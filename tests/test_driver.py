"""Regression cases from the original issue tracker, without SDR hardware."""
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import weewx
from weewx.crc16 import crc16
from user import rtldavis as rtl
from user import rtldavis_receiver


@pytest.fixture
def driver(monkeypatch):
    monkeypatch.setattr(rtldavis_receiver.Radio, 'start', lambda self: None)
    return rtl.RtldavisDriver(None, {'Rtldavis': {}})


def frame_bytes(message=8, channel=1, raw=0x251, flags=8, speed=2, direction=128):
    body = bytes([(message << 4) | (channel - 1), speed, direction,
                  raw >> 4, ((raw & 15) << 4) | flags, 0])
    return body + crc16(body).to_bytes(2, 'big')


@pytest.mark.parametrize('raw,fahrenheit', [(0xFCE, -5), (0xE68, -40.8),
                                            (0xFFF, -0.1), (0x251, 59.3), (0, 0)])
def test_signed_temperature(driver, raw, fahrenheit):
    data = driver.parse_readings(frame_bytes(raw=raw))
    assert data['temperature'] == pytest.approx((fahrenheit - 32) * 5 / 9)


@pytest.mark.parametrize('raw', [0xFFC, 0xFF8])
def test_missing_temperature(driver, raw):
    assert 'temperature' not in driver.parse_readings(frame_bytes(raw=raw))


def test_low_battery_frames(driver):
    # Actual frames from issue #20, with battery bit 3 set.
    driver.channels['iss'] = 2
    data = driver.parse_readings(bytes.fromhex('8900D7331B002690'))
    assert data['bat_iss'] == 1
    assert 'temperature' in data


@pytest.mark.parametrize('message', [0, 1, 3, 0xB, 0xC, 0xD])
def test_unknown_messages_do_not_supply_wind(driver, message):
    assert 'wind_speed' not in driver.parse_readings(frame_bytes(message=message, speed=242))


@pytest.mark.parametrize('direction,expected', [(0, 5), (255, 355), (128, 180.675889)])
def test_wind_at_north_boundaries(driver, direction, expected):
    data = driver.parse_readings(frame_bytes(direction=direction))
    assert data['wind_speed'] == pytest.approx(2 * rtl.MPH_TO_MPS)
    assert data['wind_dir'] == pytest.approx(expected)


def test_calm_wind_clears_last_speed(driver):
    data = driver.parse_readings(frame_bytes(speed=0, direction=0))
    assert data['wind_speed'] == 0
    assert data['wind_dir'] is None


def test_wind_only_from_selected_transmitter(driver):
    driver.channels['anemometer'] = driver.channels['wind_channel'] = 2
    assert 'wind_speed' not in driver.parse_readings(frame_bytes(channel=1, speed=30))
    assert 'wind_speed' in driver.parse_readings(frame_bytes(channel=2))


def test_gust_reaches_weewx(driver):
    raw = bytearray(frame_bytes(message=9)); raw[3] = 11; raw[5] = 0x10
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
    assert driver.parse_readings(frame_bytes(message=5, raw=0, flags=0))['rain_rate'] is None


def test_foreign_station_does_not_crash(driver):
    assert driver.parse_readings(frame_bytes(channel=8)) == {}


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


def test_cli_version_success():
    environment = dict(os.environ, PYTHONPATH=str(Path(rtl.__file__).parents[1]))
    result = subprocess.run([sys.executable, '-m', 'user.rtldavis', '--version'],
                            capture_output=True, text=True, env=environment)
    assert result.returncode == 0
    assert 'rtldavis' in result.stdout.lower()


def test_thermistor_invalid_resistance_is_missing():
    for raw in (0, -1, 1023.75):
        assert rtl.calculate_thermistor_temp(raw) is None


def test_captured_multi_transmitter_log_has_no_phantom_rain(driver):
    driver.channels['iss'] = driver.channels['wind_channel'] = 2
    driver.channels['leaf_soil'] = 3
    lines = (Path(__file__).parent / 'fixtures/issue24.txt').read_text().splitlines()
    payloads = [bytes.fromhex(line.split()[1]) for line in lines if line.strip()]
    packets = [driver._data_to_packet(driver.parse_readings(payload)) for payload in payloads]
    assert len(packets) > 60
    assert sum(packet.get('rain') or 0 for packet in packets) == 0


def test_frame_counts_reach_archive_statistics(driver):
    frame = rtldavis_receiver.Frame(0, frame_bytes(), 0.0, (7,), 2, -1234.4)
    packet = driver._frame_to_packet(frame)
    assert driver.stats['curr_cnt'] == [7, 0, 0, 0]
    assert packet['outTemp'] == pytest.approx((59.3 - 32) * 5 / 9)
    assert 'hailRate' not in packet
    driver.transm_to_store = 0
    # freqError2 reaches the database through its legacy field.
    assert driver._frame_to_packet(frame)['hailRate'] == -1234


@pytest.mark.parametrize('message', [0, 1, 0xB, 0xD, 0xF])
def test_frame_with_impossible_message_type_is_discarded(driver, message):
    assert driver.parse_readings(frame_bytes(message=message)) == {}
