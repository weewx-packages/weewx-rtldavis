package main

import (
	"errors"
	"testing"
	"time"

	rtlsdr "github.com/jpoirier/gortlsdr"
)

func TestGateKeepsRepeatedTransmissions(t *testing.T) {
	var gate packetGate
	start := time.Unix(100, 0)
	for _, test := range []struct {
		id    byte
		delay time.Duration
		want  bool
	}{
		{0, 0, true}, {0, time.Millisecond, false}, {1, time.Millisecond, true},
		{0, 1900 * time.Millisecond, false}, {0, 2562500 * time.Microsecond, true},
		{0, 3 * time.Second, false}, {0, 5125000 * time.Microsecond, true},
		{8, 6 * time.Second, false},
	} {
		if got := gate.accept(test.id, start.Add(test.delay)); got != test.want {
			t.Errorf("id=%d delay=%s accepted=%v, want %v", test.id, test.delay, got, test.want)
		}
	}
}

func TestOpenPassesResolvedDevice(t *testing.T) {
	for _, test := range []struct {
		name         string
		serial, want int
	}{
		{"1", -1, 1}, {"weather", 3, 3}, {"00000002", 2, 2},
	} {
		opened := -1
		_, err := openSelectedDevice(test.name,
			func(string) (int, error) { return test.serial, nil },
			func(index int) (*rtlsdr.Context, error) { opened = index; return nil, nil })
		if err != nil || opened != test.want {
			t.Errorf("%s opened=%d err=%v", test.name, opened, err)
		}
	}
	for _, name := range []string{"-1", "missing"} {
		_, err := openSelectedDevice(name,
			func(string) (int, error) { return -1, errors.New("missing") },
			func(int) (*rtlsdr.Context, error) { t.Fatal("invalid device opened"); return nil, nil })
		if err == nil {
			t.Errorf("accepted invalid device %q", name)
		}
	}
}

func TestRejectInvalidOptions(t *testing.T) {
	for _, test := range []struct {
		mask             int
		band             string
		start, end, step int
	}{
		{0, "EU", 0, 0, 0}, {256, "EU", 0, 0, 0}, {1, "AU", 0, 0, 0},
		{1, "EU", 86800, 86900, 100}, {1, "EU", 868000000, 869000000, 0},
		{1, "EU", 869000000, 868000000, 100},
	} {
		if validateOptions(test.mask, test.band, test.start, test.end, test.step) == nil {
			t.Errorf("accepted %+v", test)
		}
	}
	if err := validateOptions(255, "NZ", 921000000, 928000000, 20000); err != nil {
		t.Fatal(err)
	}
}
