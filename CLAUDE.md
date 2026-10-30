# weewx-rtldavis

WeeWX driver for Davis wireless stations received through an RTL-SDR dongle.
Independent continuation of lheijst/weewx-rtldavis; preserve GPL notices and authorship.

## Checks

- `python -m pytest -q`: packet regressions and simulated transmitters, about 3 seconds.
  Needs WeeWX, numpy and pytest.
- `python tools/package.py`: build the versioned extension archive.
- Hardware reception and repeater formats need separate verification.

## Structure

- `bin/user/rtldavis.py`: WeeWX driver, configuration prompts and the diagnostic command.
- `bin/user/rtldavis_receiver.py`: hop schedule, frequency search, librtlsdr binding.
- `bin/user/rtldavis_dsp.py`: numpy demodulator. Imported only when numpy is present.
- `install.py`: WeeWX extension installer.
- `docs/`: Configuration, troubleshooting and provenance.
- `tests/`: Recorded-packet regressions and simulated transmitters.

## Conventions

Use four spaces and existing WeeWX naming. New Python docstrings use Google style
with types in the docstring, without runtime annotations. Keep hardware claims
separate from recorded-packet and simulated-process tests.

README follows the weewx-packages schema and names no versions or archive URLs; installation links to the catalog page.
