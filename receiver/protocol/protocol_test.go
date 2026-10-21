package protocol

import (
	"bytes"
	"encoding/hex"
	"testing"

	"github.com/weewx-packages/weewx-rtldavis/receiver/dsp"
)

func TestParseRecordedFrameTwiceWithoutChangingInput(t *testing.T) {
	parser := NewParser(14, "EU")
	payload, _ := hex.DecodeString("E003BE730300E26A")
	onAir := append([]byte{0xCB, 0x89}, payload...)
	for i, value := range onAir {
		onAir[i] = SwapBitOrder(value)
	}
	original := append([]byte(nil), onAir...)
	for i := 0; i < 2; i++ {
		messages := parser.Parse([]dsp.Packet{{Idx: 0, Data: onAir}})
		if len(messages) != 1 || !bytes.Equal(messages[0].Data, payload) {
			t.Fatalf("parse %d: %+v", i, messages)
		}
		if !bytes.Equal(onAir, original) {
			t.Fatal("Parse modified its input")
		}
	}
}

func TestParseRejectsMalformedFrames(t *testing.T) {
	parser := NewParser(14, "EU")
	for _, packet := range []dsp.Packet{
		{Idx: 0, Data: nil}, {Idx: 0, Data: make([]byte, 3)},
		{Idx: -1, Data: make([]byte, 10)}, {Idx: 10000, Data: make([]byte, 10)},
		{Idx: 0, Data: bytes.Repeat([]byte{1}, 10)},
	} {
		if messages := parser.Parse([]dsp.Packet{packet}); len(messages) != 0 {
			t.Fatalf("accepted %+v", packet)
		}
	}
}

func TestPacketConfigHonorsSymbolLength(t *testing.T) {
	if cfg := NewPacketConfig(16); cfg.SymbolLength != 16 || cfg.SampleRate != 307200 {
		t.Fatal(cfg)
	}
}

func TestFrequencyEstimateUsesPacketSamplePhase(t *testing.T) {
	parser := NewParser(14, "EU")
	data, _ := hex.DecodeString("CB89E003BE730300E26A")
	for i, value := range data {
		data[i] = SwapBitOrder(value)
	}
	for i := 0; i < 16; i++ {
		parser.Discriminated[3+i*14] = .1
	}
	parser.Parse([]dsp.Packet{{Idx: 3, Data: data}})
	channel := parser.hopPattern[parser.hopIdx]
	if got := parser.freqerrTrChList[0][channel][0]; got != -4278 {
		t.Fatalf("frequency error %d, want -4278 Hz", got)
	}
}
