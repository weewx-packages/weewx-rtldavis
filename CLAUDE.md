# weewx-rtldavis

WeeWX driver for Davis wireless stations received through an RTL-SDR dongle.
Independent continuation of lheijst/weewx-rtldavis; preserve GPL notices and authorship.

## Checks

- `python -m pytest -q`: packet and process regressions, about 3 seconds.
- `cd receiver && go test -race ./...`: receiver and synthetic IQ checks.
- `python tools/package.py`: build the versioned extension archive.
- Hardware reception and repeater formats need separate verification.

## Structure

- `bin/user/rtldavis.py`: WeeWX driver and receiver diagnostics.
- `install.py`: WeeWX extension installer.
- `receiver/`: Go decoder, DSP and native USB receiver.
- `docs/`: Configuration, troubleshooting and provenance.
- `tests/`: Recorded-packet and simulated-process regressions.

## Conventions

Use four spaces and existing WeeWX naming. New Python docstrings use Google style
with types in the docstring, without runtime annotations. Keep hardware claims
separate from recorded-packet and simulated-process tests.
