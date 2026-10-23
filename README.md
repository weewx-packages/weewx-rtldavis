# Davis RTL-SDR

Receive Davis Vantage Pro, Pro2 and Vue observations with an RTL-SDR USB dongle.
The driver supports EU, US and NZ frequency plans, separate wind transmitters,
and leaf/soil and temperature/humidity stations. It needs the companion Go
receiver `rtldavis`, which the extension does not install.

This is an independent continuation of
[lheijst/weewx-rtldavis](https://github.com/lheijst/weewx-rtldavis) and
[lheijst/rtldavis](https://github.com/lheijst/rtldavis). The Python driver and
the Go receiver share this repository, with both Git histories. Report problems
in [this issue tracker](https://github.com/weewx-packages/weewx-rtldavis/issues).

## Requirements

- Linux, a Davis wireless station and an RTL-SDR dongle.
- For the receiver: Go 1.23 or later, a C compiler and the librtlsdr headers.

On Debian or Raspberry Pi OS:

```sh
sudo apt install git golang-go build-essential librtlsdr-dev rtl-sdr
```

No Python packages are needed beyond WeeWX.

## Installation

Install `rtldavis` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/rtldavis.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

The extension installs only the Python driver. Build the receiver from the tag
of the same release, for example `v<version>`:

```sh
git clone https://github.com/weewx-packages/weewx-rtldavis.git
cd weewx-rtldavis
git checkout v<version>
(cd receiver && go build -o ../dist/rtldavis .)
sudo install -m 755 dist/rtldavis /usr/local/bin/rtldavis
```

After an update, rebuild the receiver when the [changelog](CHANGELOG.md) says
so. Then select the driver and restart WeeWX, here for a systemd installation:

```sh
weectl station reconfigure --driver=user.rtldavis --config=/path/to/weewx.conf
sudo systemctl restart weewx
```

## Configuration

Edit `[Rtldavis]` in your station's `weewx.conf`:

```ini
[Rtldavis]
    driver = user.rtldavis
    cmd = /usr/local/bin/rtldavis
    transceiver_frequency = EU
    iss_channel = 1
    rain_bucket_type = 1
```

Set the frequency plan and the ISS channel to match your station. Bucket type
`1` means 0.2 mm per tip, `0` means 0.01 inch.

The [configuration reference](docs/configuration.md) lists every option with
its default, the observations, additional transmitters and the sensor map.
[Troubleshooting](docs/troubleshooting.md) covers USB access, reception tests
and IQ replay.

## Limitations

- Tests cover recorded problem frames, synthetic IQ, receiver processes and
  WeeWX installation. Live RF reception has not been tested on real hardware.
- The original EU no-decode report with a repeater is unresolved.
  Repeater-specific frame formats are not supported.
- The driver reads no I2C sensor. A BMP280 or BME280 needs its own WeeWX
  service.

## Development

Install WeeWX and pytest in a virtual environment, then run:

```sh
python -m pytest -q
(cd receiver && go test -race ./...)
python tools/package.py
```

The receiver tests need the native build dependencies. `tools/package.py` builds
the extension archive in `dist/`. The catalog's
[compatibility workflow](https://github.com/weewx-packages/catalog/actions)
tests catalog releases against WeeWX `master` and `development` once a week.

## License

GPL-3.0-or-later. Original authors include Matthew Wall, Luc Heijst and Douglas
Hall. See [credits](docs/credits.md) and [license](license).
