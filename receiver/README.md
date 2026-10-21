# rtldavis receiver

Go component of [weewx-rtldavis](../README.md). See the root README for installation
and [troubleshooting](../docs/troubleshooting.md) for RF tests and IQ replay.

```sh
go build -o ../dist/rtldavis .
go test -race ./...
```

Requires Go 1.23 or later, a C compiler and librtlsdr development headers.
The original receiver history from lheijst/rtldavis is preserved in Git.
