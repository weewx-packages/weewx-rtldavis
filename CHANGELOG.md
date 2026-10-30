# Changes

## 0.22.1 (2026-10-30)

- Attribute each frame to the channel it was received on, also when one
  sample block holds several frames and the first one retunes the receiver.
- Close the dongle only after a running USB read has returned.
- Leave unconfigured transmitters out of the frequency search. They could hold
  it at an offset where the configured transmitter is not received.
- Forget the learned frequency offsets when the frequency is searched again.
- Store the EU frequency offsets in their mapped database fields again. 0.22.0
  added them under their unmapped names.
- Return a frame at the very end of a recording in `--iq` replay.

## 0.22.0 (2026-10-30)

The receiver runs inside WeeWX. The separate Go program, its build and the
`cmd`, `path` and `ld_library_path` options are gone. numpy and librtlsdr are
now required; see the README.

- Search for the dongle's frequency error at startup, then correct the tuning
  per transmitter and channel from every frame. The Go receiver measured this
  error 1024 samples after the sync word, mostly after the frame.
- Decode frames up to about 20 kHz off frequency, and frames at a lower signal
  level than before.
- Let one burst decode once: the payload most decodes agree on wins. Discard
  frames of eight zero bytes and frames with a message type no transmitter
  sends.
- Wait for a missing dongle, library or permission and log how to fix it,
  instead of stopping WeeWX.
- Log a transmitter on an unconfigured channel, with the setting to use.
- Ask for band, ISS channel and rain bucket in `weectl station reconfigure`.
- Add `device`, `gain` and `ppm`, and `--check` for the diagnostic command.
- Store the EU frequency offsets in the observation packet, not a packet of
  their own.
- Remove the string comparison of the WeeWX version. Issue #6.
- Read synchronously when librtlsdr delivers zeroed sample blocks. librtlsdr
  0.6.0 in Debian bookworm does this on ARM (Debian bug #1041701).
- Name the missing RTL-SDR Blog V4 support of Debian bookworm's librtlsdr in
  the README.

## 0.21.2

- Restructure the README around installation from the catalog.
- Document migration of existing driver installations to the catalog.
- State in the configuration reference that `sensor_map` entries are merged
  into the built-in mapping.

## 0.21.1

- Compare DSP floating-point results with a numerical tolerance on ARM64.
- Run native receiver checks on x86-64 and ARM64 in GitHub Actions.

## 0.21.0

Independent continuation with the Python driver and Go receiver in one repository.
The receiver reports version 0.16.0. Both original Git histories are retained.

- Decode signed digital temperatures without including sensor flags; recognize
  both missing-sensor values. Original issues #14 and PRs #19, #23.
- Limit wind to known message types and the selected transmitter. Preserve calm
  wind and north-boundary directions. Export the transmitter's reported gust.
  Original PR #19 and issue #25.
- Reject repeated RF decodes per sender and unsafe rain counter transitions.
  Rejected counts do not become the baseline. Original issues #15, #24 and PR #22.
- Accept low-battery frames and skip bad CRCs without stopping the packet loop.
  Original issue #20.
- Populate archive reception percentages, including silent transmitters; handle
  short intervals and receiver counter resets. Original issues #7, #26.
- Stop reader threads at binary EOF, drain both pipes and quote command paths.
  Shutdown reaps only the receiver owned by this driver. Diagnostic mode handles
  idle output and `--version` returns success. Original issues #7, #9.
- Build the companion receiver with pinned Go modules. Honor `-d`, retain valid
  repeated transmissions, validate scan units and decode IQ recordings offline.
  Original issues #7, #13, #18; receiver PRs #2, #3, #5, #6, #7.
- Add packet replay, process and synthetic IQ regression tests. Daily checks
  against WeeWX development are configured in the shared package catalog.

Existing module and installer names remain `user.rtldavis` and `rtldavis`.
Existing installations can retain their receiver executable, but rebuild it to
obtain the receiver fixes. Legacy database diagnostic aliases remain unchanged.
BMP280/BME280 readings need a separate service.

The EU no-decode/repeater report, original issue #21, still needs real IQ samples
and hardware verification. General elimination of every isolated corrupt reading
is also unverified. See docs/troubleshooting.md.

Earlier history is recorded in [changelog](changelog).
