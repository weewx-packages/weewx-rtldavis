package main

import (
	"fmt"
	"strconv"
	"time"

	rtlsdr "github.com/jpoirier/gortlsdr"
)

// packetGate accepts one transmission per sender every two seconds. Changed
// payloads can also be secondary decodes of one RF burst with a valid CRC.
// Legitimate repeated payloads one full ISS interval later must still advance
// hopping and reception counters. Rejected frames never extend the window.
type packetGate struct{ last [maxTr]time.Time }

func (g *packetGate) accept(id byte, now time.Time) bool {
	if id >= maxTr {
		return false
	}
	if !g.last[id].IsZero() && now.Sub(g.last[id]) < 2*time.Second {
		return false
	}
	g.last[id] = now
	return true
}

// openSelectedDevice resolves a serial number before trying a numeric index.
// The callbacks allow verification of the actual index passed to librtlsdr.
func openSelectedDevice(name string, lookup func(string) (int, error),
	open func(int) (*rtlsdr.Context, error)) (*rtlsdr.Context, error) {
	index, err := lookup(name)
	if err != nil || index < 0 {
		index, err = strconv.Atoi(name)
		if err != nil || index < 0 {
			return nil, fmt.Errorf("invalid RTL-SDR device %q", name)
		}
	}
	return open(index)
}

// validateOptions rejects empty channel masks and incorrectly scaled scans
// before any USB device is opened. Scan frequencies are raw Hz.
func validateOptions(mask int, band string, start, end, step int) error {
	if mask < 1 || mask > 255 {
		return fmt.Errorf("-tr must be between 1 and 255")
	}
	if band != "EU" && band != "US" && band != "NZ" {
		return fmt.Errorf("-tf must be EU, US or NZ")
	}
	if start != 0 || end != 0 || step != 0 {
		if start < 24000000 || end > 1766000000 || end < start || step <= 0 {
			return fmt.Errorf("scan requires 24000000 <= startfreq <= endfreq <= 1766000000 and positive stepfreq, in Hz")
		}
	}
	return nil
}
