# Davis wireless weather stations for WeeWX

Receive Davis Vantage Pro, Pro2 and Vue observations with an RTL-SDR USB dongle.
The driver supports EU, US and NZ frequency plans, separate wind transmitters,
and leaf/soil and temperature/humidity stations.

This is an independent continuation of
[lheijst/weewx-rtldavis](https://github.com/lheijst/weewx-rtldavis) and
[lheijst/rtldavis](https://github.com/lheijst/rtldavis).
Both histories and original GPL notices are preserved. The Python driver and Go
receiver now share this repository. Report problems in
[this issue tracker](https://github.com/weewx-packages/weewx-rtldavis/issues).

## Install

Requires WeeWX 5, Python 3.7 or later, Linux and a compatible RTL-SDR dongle.
The Go receiver needs Go 1.23 or later, a C compiler and the librtlsdr headers.
On Debian or Raspberry Pi OS:

```sh
sudo apt install git golang-go build-essential librtlsdr-dev rtl-sdr
git clone https://github.com/weewx-packages/weewx-rtldavis.git
cd weewx-rtldavis
git checkout v0.21.1
(cd receiver && go build -o ../dist/rtldavis .)
sudo install -m 755 dist/rtldavis /usr/local/bin/rtldavis
```

Install the driver using the `weectl` from your WeeWX installation:

```sh
weectl extension install https://github.com/weewx-packages/weewx-rtldavis/releases/download/v0.21.1/weewx-rtldavis-0.21.1.zip
weectl station reconfigure --driver=user.rtldavis
```

If you already use the [package catalog](https://github.com/weewx-packages/catalog),
`weectl extension install rtldavis` selects the catalog release.
Building the Go receiver remains a separate step; extension installation updates
the Python driver. Rebuild the receiver when its release notes require it.

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
`1` means 0.2 mm per tip; `0` means 0.01 inch. Restart WeeWX after changing drivers.
For a systemd installation, use `sudo systemctl restart weewx`.

See [configuration](docs/configuration.md) for additional transmitters and sensor
mapping, and [troubleshooting](docs/troubleshooting.md) for USB and reception tests.

## Updates and limits

Existing `[Rtldavis]`, `user.rtldavis` and installer name `rtldavis` remain valid.
See [changes](CHANGELOG.md) for fixes and migration details.

If the driver was installed from an archive and you now want updates from a
registered catalog source named `packages`, explicitly switch its source:

```sh
weectl extension switch-source rtldavis --repo packages --package rtldavis
```

This installs the selected catalog release and binds future updates to that
source. It requires a WeeWX build with repository support.

Tests cover recorded problem frames, synthetic IQ, receiver processes and WeeWX
installation. Live RF reception, including the unresolved EU/repeater report,
still needs hardware testing. Repeater-specific frame formats are unsupported.

## Development

Install WeeWX and pytest in a virtual environment, then run `python -m pytest -q`.
Run `go test -race ./...` from `receiver/` with the native build dependencies
installed. [The compatibility workflow](https://github.com/weewx-packages/catalog/actions)
checks catalog releases against WeeWX's current `master` and `development` daily.

GPL-3.0-or-later. Original authors include Matthew Wall, Luc Heijst and Douglas
Hall. See [credits](docs/credits.md) and [license](license).
