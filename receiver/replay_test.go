package main

import (
	"bytes"
	"encoding/hex"
	"math"
	"strings"
	"testing"

	"github.com/weewx-packages/weewx-rtldavis/receiver/protocol"
)

// syntheticIQ emits continuous-phase FSK with the same quarter-rate tuning
// offset as the live demodulator. It verifies the full IQ-to-CRC path while
// keeping RF sensitivity and real repeater formats outside this fixture.
func syntheticIQ(payload []byte) []byte {
	data := []byte{0xCB, 0x89}
	for _, value := range payload {
		data = append(data, protocol.SwapBitOrder(value))
	}
	bits := make([]byte, 2048)
	for _, value := range data {
		for bit := 7; bit >= 0; bit-- {
			for sample := 0; sample < 14; sample++ {
				bits = append(bits, (value>>bit)&1)
			}
		}
	}
	bits = append(bits, make([]byte, 4096)...)
	result := make([]byte, len(bits)*2)
	phase := 0.0
	for i, bit := range bits {
		frequency := -4800.0
		if bit == 1 {
			frequency = 4800
		}
		phase += -math.Pi/2 + 2*math.Pi*frequency/268800
		result[2*i] = byte(127.4 + 60*math.Cos(phase))
		result[2*i+1] = byte(127.4 + 60*math.Sin(phase))
	}
	return result
}

func TestReplayDemodulatesIQAndChecksCRC(t *testing.T) {
	payload, _ := hex.DecodeString("E003BE730300E26A")
	var output bytes.Buffer
	if err := replay(bytes.NewReader(syntheticIQ(payload)), &output, "EU"); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(output.String(), "E003BE730300E26A ID=0") {
		t.Fatalf("recorded payload missing: %q", output.String())
	}
	payload[3] ^= 1
	output.Reset()
	if err := replay(bytes.NewReader(syntheticIQ(payload)), &output, "EU"); err != nil {
		t.Fatal(err)
	}
	if output.Len() != 0 {
		t.Fatalf("accepted bad CRC: %s", output.String())
	}
}
