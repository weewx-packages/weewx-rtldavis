# Diagnose reception

Stop WeeWX before a standalone radio test so it releases the dongle:

```sh
sudo systemctl stop weewx
rtl_test -t
rtldavis -tf EU -tr 1
```

`-tr` is a bitmask: channels 1–8 use bits 1, 2, 4, 8, 16, 32, 64, 128.
For ISS channel 1 and wind channel 2, use `-tr 3`. The driver constructs this
mask automatically. The receiver writes its decoded frames and diagnostics to
stderr. Absence of an ISS signal produces no weather readings.

For Python diagnostics, use the same Python environment as WeeWX. With a station
at `~/weewx-data`:

```sh
PYTHONPATH=~/weewx-data/bin python3 -m user.rtldavis --help
PYTHONPATH=~/weewx-data/bin python3 -m user.rtldavis --cmd '/usr/local/bin/rtldavis -tf EU -tr 1'
```

For a package installation, replace the path with `/etc/weewx/bin`. Activate the
WeeWX virtual environment first when using a pip installation. `--version` exits
successfully; the default action displays both receiver output streams until
interrupted or until the receiver exits.

- A missing `rtl-sdr.h` requires `librtlsdr-dev` before building the receiver.
- A missing `configobj` or `weewx` usually means diagnostics use a different
  Python environment from WeeWX.
- Permission denied opening USB requires the distribution's RTL-SDR udev rules
  and permission for the WeeWX service user. Reconnect the dongle after changing
  rules. Do not grant every user write access to all USB devices.
- If a DVB kernel driver claims the dongle, follow your distribution's RTL-SDR
  instructions to release that device.
- RTL-SDR Blog V4 hardware needs a librtlsdr build supporting its R828D tuner.
  Verify which library the executable uses with `ldd /usr/local/bin/rtldavis`.
- The driver raises a recoverable WeeWX I/O error if no valid data arrives for
  150 seconds or the receiver exits. Hop diagnostics alone do not reset this timer.

Restart WeeWX after the standalone test:

```sh
sudo systemctl start weewx
journalctl -u weewx -f
```

## EU reception and repeaters

The original EU no-decode report remains unresolved:
[lheijst/weewx-rtldavis#21](https://github.com/lheijst/weewx-rtldavis/issues/21).
A strong `rtl_power` signal verifies RF energy, not successful packet decoding.
The receiver expects an 80-bit frame including its 16-bit sync word. Longer
repeater frames need protocol samples before support can be verified.

Frequency scan flags use raw Hz, for example:

```sh
rtldavis -tf EU -tr 2 -startfreq 868047250 -endfreq 868107250 -stepfreq 2000
```

Each scan step waits a complete synchronization interval. Confirm normal
reception first where possible. A scan cannot correct an unsupported frame format.

To investigate a failure, attach the command, receiver log, SDR model, librtlsdr
version and a short unsigned 8-bit IQ recording at 268800 complex samples/second.
Record the tuned frequency and any ppm correction. Keep direct ISS and repeater
captures separate. Offline replay needs no SDR:

```sh
rtldavis -tf EU -iq capture.cu8
```

Replay prints CRC-valid payloads and zero-based transmitter IDs to stdout.
It uses the live decoder's quarter-sample-rate frequency offset. A capture must
retain the live tuning relationship; a recording centered differently may need
frequency translation before replay. Synthetic IQ tests verify the decoding
path, but do not establish real repeater support or receiver sensitivity.
