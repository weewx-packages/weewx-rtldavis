# Copyright (c) 2026 Manuel Hilgert <hilman2@gmail.com>
"""Receiver checks against simulated transmitters, without SDR hardware."""
import math
import threading
import time

import numpy
import pytest

from user import rtldavis_dsp as dsp
from user import rtldavis_receiver as receiver

FS = receiver.SAMPLE_RATE
BLOCK = 8192


def payload(transmitter, sequence):
    """Return a CRC-valid Davis payload for a temperature message."""
    body = bytes([0x80 | transmitter, 2, 128, 0x25, 0x18, sequence & 0xFF])
    return body + dsp.crc16(body).to_bytes(2, 'big')


def burst(data, deviation=4800.0):
    """Return the per-sample frequency deviation of one frame, sync word first."""
    reversed_bits = [int('{:08b}'.format(value)[::-1], 2) for value in data]
    bits = []
    for value in [0xCB, 0x89] + reversed_bits:
        bits += [(value >> bit) & 1 for bit in range(7, -1, -1)]
    return numpy.repeat(numpy.array(bits) * 2.0 - 1.0, dsp.SYMBOL_LENGTH) * deviation


class Simulation:
    """One ISS hopping through a band, received by a dongle with a frequency error.

    The ISS sends on table frequency + dongle_error + channel_error[channel].
    The receiver's tuning decides which bursts fall inside the sampled band.
    """

    def __init__(self, band, transmitter, dongle_error, channel_error, noise, seed=1):
        self.frequencies, self.pattern = receiver.BANDS[band]
        self.transmitter = transmitter
        self.period = receiver.transmitter_period(transmitter)
        self.dongle_error = dongle_error
        self.channel_error = channel_error
        self.noise = noise
        self.rng = numpy.random.default_rng(seed)
        self.first = 0.7
        self.sent = []

    def transmissions(self, start, end):
        """Yield (time, channel, payload) of bursts overlapping [start, end) seconds."""
        k = max(0, int(math.floor((start - self.first) / self.period)) - 1)
        while True:
            when = self.first + k * self.period
            if when >= end:
                return
            channel = self.pattern[k % len(self.pattern)]
            yield when, channel, payload(self.transmitter, k)
            k += 1

    def block(self, index, tuned):
        """Return BLOCK samples starting at sample index, as interleaved uint8 IQ."""
        signal = self.noise * (self.rng.standard_normal(BLOCK)
                               + 1j * self.rng.standard_normal(BLOCK))
        start, end = index / FS, (index + BLOCK) / FS
        for when, channel, data in self.transmissions(start, end + 0.01):
            if when < end and (when, data) not in self.sent:
                self.sent.append((when, data))
            carrier = (self.frequencies[channel] + self.dongle_error
                       + self.channel_error[channel])
            # The receiver expects the carrier a quarter of the sample rate below
            # the tuned frequency.
            offset = carrier - tuned - FS / 4
            if abs(offset) > 0.45 * FS:
                continue
            deviation = burst(data)
            phase = numpy.cumsum(2 * math.pi * (deviation + offset) / FS)
            first = int(round(when * FS))
            lo, hi = max(first, index), min(first + len(phase), index + BLOCK)
            if lo >= hi:
                continue
            signal[lo - index:hi - index] += 60 * numpy.exp(1j * phase[lo - first:hi - first])
        raw = numpy.empty(2 * BLOCK, dtype=numpy.uint8)
        raw[0::2] = numpy.clip(numpy.round(127.4 + signal.real), 0, 255)
        raw[1::2] = numpy.clip(numpy.round(127.4 + signal.imag), 0, 255)
        return raw.tobytes()


def run(simulation, rx, seconds):
    rx.start(0.0)
    frames = []
    index = 0
    while index < seconds * FS:
        data = simulation.block(index, rx.frequency)
        index += BLOCK
        frames += rx.feed(data, index / FS)
    return frames


def test_finds_offset_synchronizes_and_tracks_channels():
    # +45 kHz dongle error: found in the third search step. The channel errors
    # are the difference between the table's 120 kHz and a 115.2 kHz spacing.
    channel_error = [-4800 * channel for channel in range(5)]
    simulation = Simulation('EU', 0, 45000, channel_error, noise=8)
    rx = receiver.Receiver('EU', [0])
    frames = run(simulation, rx, 90)
    assert rx.locked
    received = {frame.payload for frame in frames}
    after_lock = [data for when, data in simulation.sent if when > frames[0].time]
    assert len(after_lock) > 15
    assert sum(data in received for data in after_lock) >= 0.9 * len(after_lock)
    for channel in range(5):
        learned = rx.learned[(0, channel)]
        assert learned == pytest.approx(45000 + channel_error[channel], abs=2500)
    # Tuned per channel, the carrier is centered on every channel.
    assert max(abs(frame.frequency_error) for frame in frames[-10:]) < 2000


def test_unconfigured_transmitter_is_reported_not_returned(caplog):
    simulation = Simulation('EU', 1, 0, [0] * 5, noise=8)
    rx = receiver.Receiver('EU', [0])
    caplog.set_level('INFO')
    assert run(simulation, rx, 20) == []
    assert 'iss_channel = 2' in caplog.text


def test_second_decode_of_a_burst_is_ignored():
    # Both CRC-valid frames from original issue #15 arrived 262 microseconds apart.
    rx = receiver.Receiver('EU', [0])
    rx.start(0.0)
    tuning = (rx.channel, rx.frequency)
    first = dsp.Candidate(0, bytes.fromhex('E003BE730300E26A'), 0.0)
    second = dsp.Candidate(70, bytes.fromhex('E0019E310300E26A'), 0.0)
    assert rx._accept(first, 10.0, *tuning) is not None
    assert rx._accept(second, 10.000262, *tuning) is None
    assert rx._accept(dsp.Candidate(0, bytes.fromhex('E001BE730300A6E9'), 0.0), 30.5, *tuning)


def test_unconfigured_transmitter_does_not_lock_the_frequency():
    rx = receiver.Receiver('EU', [0])
    rx.start(0.0)
    rx._accept(dsp.Candidate(0, payload(1, 0), 30000.0), 1.0, rx.channel, rx.frequency)
    assert not rx.locked
    assert rx.learned == {}


def test_lost_lock_forgets_learned_offsets():
    rx = receiver.Receiver('EU', [0])
    rx.start(0.0)
    rx._accept(dsp.Candidate(0, payload(0, 0), 5000.0), 1.0, rx.channel, rx.frequency)
    rx._synchronize(2.0)
    for period in range(receiver.LOST_LOCK_PERIODS):
        rx._timeout(rx._deadline)
    assert not rx.locked
    assert rx.learned == {}


class PreparedDemodulator:
    """Returns prepared candidates, one list per block."""

    def __init__(self, batches):
        self.batches = batches
        self.sample_count = 0
        self.settled = 0

    def feed(self, raw, shifts):
        self.sample_count += len(raw) // 2
        self.settled = self.sample_count
        return self.batches.pop(0) if self.batches else []


def test_frames_of_one_block_keep_the_channel_they_were_sampled_on():
    rx = receiver.Receiver('EU', [0, 1, 2])
    rx.start(0.0)
    channel = rx.channel
    burst = lambda transmitter, index: dsp.Candidate(index, payload(transmitter, 1), 0.0)
    rx._demodulator = PreparedDemodulator([
        [burst(0, 100), burst(1, 3000)],
        # Transmitter 2 completes the synchronization and retunes the
        # receiver before transmitter 0's second frame is handled.
        [burst(2, 8300), burst(0, 12000)]])
    frames = rx.feed(bytes(2 * BLOCK), BLOCK / FS)
    frames += rx.feed(bytes(2 * BLOCK), 5.0)
    assert rx.channel != channel
    assert [frame.channel for frame in frames] == [channel] * 4


def test_replay_returns_a_frame_at_the_end_of_a_recording(tmp_path):
    data = payload(0, 3)
    deviation = numpy.concatenate((numpy.zeros(1000), burst(data), numpy.zeros(100)))
    phase = numpy.cumsum(2 * math.pi * (deviation - FS / 4) / FS)
    raw = numpy.empty(2 * len(phase), dtype=numpy.uint8)
    raw[0::2] = numpy.round(127.4 + 60 * numpy.cos(phase))
    raw[1::2] = numpy.round(127.4 + 60 * numpy.sin(phase))
    recording = tmp_path / 'capture.cu8'
    recording.write_bytes(raw.tobytes())
    assert [candidate.payload for candidate in receiver.replay(str(recording))] == [data]


def test_demodulator_rejects_corrupt_frame():
    good = payload(0, 7)
    bad = bytearray(good)
    bad[3] ^= 1
    for data, expected in ((good, [good]), (bytes(bad), [])):
        deviation = numpy.concatenate((numpy.zeros(3000), burst(data), numpy.zeros(3000)))
        phase = numpy.cumsum(2 * math.pi * (deviation - FS / 4) / FS)
        raw = numpy.empty(2 * len(phase), dtype=numpy.uint8)
        raw[0::2] = numpy.round(127.4 + 60 * numpy.cos(phase))
        raw[1::2] = numpy.round(127.4 + 60 * numpy.sin(phase))
        demodulator = dsp.Demodulator()
        found = demodulator.feed(raw.tobytes()) + demodulator.flush()
        assert [candidate.payload for candidate in found] == expected
    # Symbols all on one side of the threshold decode to zero bytes, whose CRC is 0.
    assert dsp._decode(numpy.ones(dsp.FRAME_SYMBOLS), [0.0]) is None


class EmptyAsyncDongle:
    """Stands in for librtlsdr 0.6.0 on ARM: queued transfers arrive zeroed."""

    def __init__(self, radio):
        self.radio = radio
        self.modes = []

    def configure(self, gain):
        pass

    def tune(self, frequency):
        pass

    def cancel(self):
        self.cancelled = True

    def close(self):
        self.closed = True

    def stream(self, receive, synchronous=False):
        self.modes.append(synchronous)
        self.cancelled = False
        block = b'\0' * 16384 if not synchronous else bytes([127, 128]) * 8192
        for _ in range(10):
            if self.cancelled:
                break
            receive(block, 0.0)
        if synchronous:
            self.radio._stopping.set()
        return 0


def test_radio_reads_synchronously_after_empty_blocks():
    radio = receiver.Radio(receiver.Receiver('EU', [0]))
    dongle = EmptyAsyncDongle(radio)
    radio._run_dongle(dongle)
    assert dongle.modes == [False, True]
    assert dongle.closed


class StuckReadDongle(EmptyAsyncDongle):
    """A synchronous read that cancel() cannot end, like librtlsdr's."""

    def __init__(self, radio):
        EmptyAsyncDongle.__init__(self, radio)
        self.release = threading.Event()
        self.closed = False

    def stream(self, receive, synchronous=False):
        self.radio._stopping.set()
        self.release.wait(5)
        assert not self.closed
        return 0


def test_dongle_is_not_closed_during_a_read():
    radio = receiver.Radio(receiver.Receiver('EU', [0]))
    radio.USB_JOIN = 0.1
    dongle = StuckReadDongle(radio)
    radio._run_dongle(dongle)
    assert not dongle.closed
    dongle.release.set()
    for _ in range(50):
        if dongle.closed:
            break
        time.sleep(0.02)
    assert dongle.closed
