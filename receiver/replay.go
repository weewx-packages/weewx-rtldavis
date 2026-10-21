package main

import (
	"fmt"
	"io"

	"github.com/weewx-packages/weewx-rtldavis/receiver/protocol"
)

// replay decodes unsigned 8-bit interleaved IQ at the receiver's sample rate.
// It prints CRC-valid payloads without USB access or frequency hopping. The
// recording must already contain a Davis channel at the same tuning offset
// used by the live receiver. Partial final blocks are ignored, never reused.
func replay(input io.Reader, output io.Writer, band string) error {
	parser := protocol.NewParser(14, band)
	block := make([]byte, parser.Cfg.BlockSize2)
	for {
		if _, err := io.ReadFull(input, block); err != nil {
			if err == io.EOF || err == io.ErrUnexpectedEOF {
				return nil
			}
			return err
		}
		for _, message := range parser.Parse(parser.Demodulate(block)) {
			if _, err := fmt.Fprintf(output, "%02X ID=%d\n", message.Data, message.ID); err != nil {
				return err
			}
		}
	}
}
