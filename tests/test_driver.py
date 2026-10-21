"""Regression cases from the original issue tracker, without SDR hardware."""
import io
import queue
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
import weewx
from weewx.crc16 import crc16
from user import rtldavis as rtl


@pytest.fixture
def driver(monkeypatch):
    monkeypatch.setattr(rtl.ProcManager, 'startup', lambda *args, **kwargs: None)
    return rtl.RtldavisDriver(None, {'Rtldavis': {}})


def frame(message=8, channel=1, raw=0x251, flags=8, speed=2, direction=128):
    body = bytes([(message << 4) | (channel - 1), speed, direction,
                  raw >> 4, ((raw & 15) << 4) | flags, 0])
    return body + crc16(body).to_bytes(2, 'big')


def decode(driver, raw, stamp='12:00:00.000000'):
    return list(rtl.PacketFactory.create(
        driver, [f'{stamp} {raw.hex().upper()} 100 0 0 0 0 msg.ID=0']))


@pytest.mark.parametrize('raw,fahrenheit', [(0xFCE, -5), (0xE68, -40.8),
                                            (0xFFF, -0.1), (0x251, 59.3), (0, 0)])
def test_signed_temperature(driver, raw, fahrenheit):
    data = driver.parse_readings(frame(raw=raw))
    assert data['temperature'] == pytest.approx((fahrenheit - 32) * 5 / 9)


@pytest.mark.parametrize('raw', [0xFFC, 0xFF8])
def test_missing_temperature(driver, raw):
    assert 'temperature' not in driver.parse_readings(frame(raw=raw))


def test_low_battery_frames(driver):
    # Actual frames from issue #20, with battery bit 3 set.
    driver.channels['iss'] = 2
    data = decode(driver, bytes.fromhex('8900D7331B002690'))
    assert len(data) == 1
    assert data[0]['bat_iss'] == 1
    assert 'temperature' in data[0]


def test_crc_failure_does_not_hide_following_frame(driver):
    bad = bytearray(frame()); bad[3] ^= 1
    lines = [f'12:00:00.000000 {bad.hex().upper()} 1 0 0 0',
             f'12:00:03.000000 {frame().hex().upper()} 2 0 0 0']
    results = list(rtl.PacketFactory.create(driver, lines))
    assert len(results) == 1
    assert results[0]['curr_cnt0'] == 2


@pytest.mark.parametrize('message', [0, 1, 3, 0xB, 0xC, 0xD])
def test_unknown_messages_do_not_supply_wind(driver, message):
    assert 'wind_speed' not in driver.parse_readings(frame(message=message, speed=242))


@pytest.mark.parametrize('direction,expected', [(0, 5), (255, 355), (128, 180.675889)])
def test_wind_at_north_boundaries(driver, direction, expected):
    data = driver.parse_readings(frame(direction=direction))
    assert data['wind_speed'] == pytest.approx(2 * rtl.MPH_TO_MPS)
    assert data['wind_dir'] == pytest.approx(expected)


def test_calm_wind_clears_last_speed(driver):
    data = driver.parse_readings(frame(speed=0, direction=0))
    assert data['wind_speed'] == 0
    assert data['wind_dir'] is None


def test_wind_only_from_selected_transmitter(driver):
    driver.channels['anemometer'] = driver.channels['wind_channel'] = 2
    assert 'wind_speed' not in driver.parse_readings(frame(channel=1, speed=30))
    assert 'wind_speed' in driver.parse_readings(frame(channel=2))


def test_gust_reaches_weewx(driver):
    raw = bytearray(frame(message=9)); raw[3] = 11; raw[5] = 0x10
    packet = driver._data_to_packet(driver.parse_readings(raw))
    assert packet['windGust'] == pytest.approx(11 * rtl.MPH_TO_MPS)
    assert 'windGustDir' not in packet


def test_rain_corruption_does_not_move_baseline(driver):
    for count, expected in [(115, 0), (49, None), (115, 0), (116, .2)]:
        assert driver._data_to_packet({'rain_count': count})['rain'] == expected


@pytest.mark.parametrize('previous,current,tips', [(127, 0, 1), (126, 2, 4), (5, 4, None), (1, 100, None)])
def test_rain_wrap_and_outliers(driver, previous, current, tips):
    driver.last_rain_count = previous
    value = driver._data_to_packet({'rain_count': current})['rain']
    assert value == (None if tips is None else pytest.approx(tips * .2))


def test_rain_counter_reset_resynchronizes_without_phantom_rain(driver):
    values = [driver._data_to_packet({'rain_count': n})['rain'] for n in [50, 0, 0, 1]]
    assert values == [0, None, 0, pytest.approx(.2)]


def test_rain_rate_zero_does_not_crash(driver):
    assert driver.parse_readings(frame(message=5, raw=0, flags=0))['rain_rate'] is None


def test_foreign_station_does_not_crash(driver):
    assert driver.parse_readings(frame(channel=8)) == {}


def test_stats_in_archive_include_silent_transmitter(driver, monkeypatch):
    driver.tr_count = 2
    driver.stats['activeTrIds'][:2] = [0, 1]
    driver.stats['last_ts'] = 100
    driver.stats['curr_cnt'][:2] = [10, 0]
    monkeypatch.setattr(rtl.time, 'time', lambda: 126)
    event = SimpleNamespace(record={})
    driver.new_archive_record(event)
    assert event.record['rxCheckPercent'] == pytest.approx(1000 / 19)


def test_stats_short_interval_and_reset(driver, monkeypatch):
    driver.stats['activeTrIds'][0] = 0
    driver.stats['last_ts'] = 100
    driver.stats['curr_cnt'][0] = 1
    monkeypatch.setattr(rtl.time, 'time', lambda: 101)
    driver.new_archive_record(SimpleNamespace(record={}))
    driver.stats['last_cnt'][0] = 100
    monkeypatch.setattr(rtl.time, 'time', lambda: 120)
    event = SimpleNamespace(record={})
    driver.new_archive_record(event)
    assert 'rxCheckPercent' not in event.record


def test_duplicate_channel_mask(driver):
    assert rtl.RtldavisDriver.ch_to_xmit(driver, 1, 1, 0, 0, 0) == (1, 1)


@pytest.mark.parametrize('channel', [-1, 0, 9])
def test_invalid_iss_channel_rejected(driver, channel):
    with pytest.raises(ValueError):
        rtl.RtldavisDriver.ch_to_xmit(driver, channel, 0, 0, 0, 0)


def test_async_reader_exits_at_binary_eof():
    output = queue.Queue()
    reader = rtl.AsyncReader(io.BytesIO(b'one\n'), output, 'test')
    reader.start(); reader.join(timeout=.2)
    reader.stop_running()
    assert not reader.is_alive()
    assert list(output.queue) == [b'one\n']


def test_receiver_process_quotes_drain_and_shutdown(tmp_path):
    script = tmp_path / 'fake receiver.py'
    script.write_text("import sys\nprint('out')\nprint('err', file=sys.stderr)\n")
    manager = rtl.ProcManager()
    try:
        manager.startup(f'{shlex.quote(sys.executable)} {shlex.quote(str(script))}')
        manager._process.wait(timeout=3)
        assert [line.strip() for batch in manager.get_stderr() for line in batch] == ['err']
        assert [line.strip() for line in manager.get_stdout()] == ['out']
    finally:
        manager.shutdown(); manager.shutdown()


def test_shutdown_only_own_receiver():
    other = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])
    manager = rtl.ProcManager()
    try:
        manager.startup(f'{shlex.quote(sys.executable)} -c "import time; time.sleep(20)"')
        child = manager._process
        manager.shutdown()
        assert child.poll() is not None
        assert other.poll() is None
    finally:
        manager.shutdown()
        other.terminate(); other.wait(timeout=3)


def test_cli_version_success():
    result = subprocess.run([sys.executable, rtl.__file__, '--version'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'rtldavis' in result.stdout.lower()


def test_recorded_corrupt_burst_is_rejected_per_sender(driver):
    # Both CRC-valid frames from #15 are separated by only 262 microseconds.
    first = decode(driver, bytes.fromhex('E003BE730300E26A'), '03:57:08.612942')
    second = decode(driver, bytes.fromhex('E0019E310300E26A'), '03:57:08.613204')
    assert first
    assert not second
    assert decode(driver, bytes.fromhex('E001BE730300A6E9'), '03:57:29.113525')


def test_burst_filter_uses_receiver_time_and_midnight(driver):
    assert decode(driver, frame(), '23:59:59.000000')
    assert not decode(driver, frame(), '23:59:59.001000')
    assert decode(driver, frame(), '00:00:01.562500')
    driver.channels['temp_hum_1'] = 2
    assert decode(driver, frame(channel=2), '00:00:01.563000')
