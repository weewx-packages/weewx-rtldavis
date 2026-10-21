# weewx-rtldavis

WeeWX driver for Davis wireless stations received through an RTL-SDR dongle.
Independent continuation of lheijst/weewx-rtldavis; preserve GPL notices and authorship.

## Structure

- `bin/user/rtldavis.py`: WeeWX driver and receiver diagnostics.
- `install.py`: WeeWX extension installer.

## Conventions

Use four spaces and existing WeeWX naming. New Python docstrings use Google style
with types in the docstring, without runtime annotations. Keep hardware claims
separate from recorded-packet and simulated-process tests.
