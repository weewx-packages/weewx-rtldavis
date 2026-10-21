# Origins and contributions

The driver continues Matthew Wall and Luc Heijst's GPL-3.0-or-later work from
[lheijst/weewx-rtldavis](https://github.com/lheijst/weewx-rtldavis), including code
from weewx-sdr and weewx-meteostick. Kobuki supplied the Envoy wind calibration
logic. The receiver continues Douglas Hall's rtldavis and Luc Heijst's
multi-transmitter, EU and NZ changes. Steve Wormley contributed device selection
and frequency correction improvements upstream.

This repository includes both original Git histories. It is independently
maintained by weewx-packages. Original maintainers have not transferred their
repositories or endorsed this continuation.

Fixes and tests draw on LloydR's wind, temperature and corrupt-burst reports and
PR #19; WeatheredScientist's signed-temperature and rain-counter PRs #23 and #22,
plus the receiver retransmission PR #7; and the receiver device-selection PRs
#3 by rwowens and #6 by cdavis289. Upstream PR authors retain credit for their
proposals. Implementations here include additional regression checks and fixes.
See the original threads for their contributors and disclosures.

`tests/fixtures/issue24.txt` contains only receiver frame lines extracted from the
public log attached to original issue #24. Tests also reproduce the CRC-valid
frame pairs published in original issue #15.

The receiver uses jpoirier/gortlsdr under its BSD license, resolved at the version
in `receiver/go.mod`. `receiver/dsp/search.go` derives from the Go standard
library; its BSD license is included in `receiver/dsp/LICENSE`. The remaining
project code is GPL-3.0-or-later unless a file states otherwise.
