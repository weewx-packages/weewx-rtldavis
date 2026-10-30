# Diagnose reception

## Read the log

The receiver logs what it needs and what it does:

```sh
journalctl -u weewx -f
```

| Message | Meaning |
| --- | --- |
| `numpy is missing. Install it with: …` | Run the command shown. The receiver retries every 15 seconds; no restart is needed. |
| `librtlsdr is missing. Install it with: …` | As above. |
| `No RTL-SDR dongle found.` | Plug in the dongle. The receiver opens it as soon as it appears. |
| `No permission to open the RTL-SDR dongle. Add user … to the plugdev group …` | Run the `usermod` command shown, then restart WeeWX. Group changes apply only to newly started programs. |
| `No permission … Install librtlsdr0, which provides the udev rule …` | The udev rule is missing. Install librtlsdr0, then reconnect the dongle. |
| `The RTL-SDR dongle is in use.` | Another program holds the dongle, or the DVB-T kernel driver does. The message shows how to release it. |
| `Searching for transmitter(s) on channel … (step n of 5)` | Normal at startup. Each step tries another tuning offset. |
| `Found a Davis transmitter … kHz (… ppm) from the table frequency.` | The dongle's frequency error. The receiver corrects it from now on. |
| `Receiving transmitter on channel …` | The transmitter is in sync; observations follow. |
| `Heard a Davis transmitter on channel …, but only channel … is configured.` | Another channel is on the air. If it is yours, set that channel in `[Rtldavis]`. |
| `Few frames arrive at …; the first one probably came from a neighbouring channel.` | The first frame was a transmitter on another channel. The search continues. |
| `Lost transmitter on channel …, synchronizing again` | 51 frames in a row were missed. The receiver waits for the transmitter again. |
| `No Davis transmitter heard for … s, searching the frequency again` | Nothing at all was received for two synchronization periods. |

If the search runs through all five steps repeatedly, check the frequency band,
the channel, the antenna and the distance. Place the ISS a few metres from the
antenna for a first test.

## Check the setup

Stop WeeWX first; only one program can use the dongle. Run the checks with the
Python that runs WeeWX. For a package installation:

```sh
sudo systemctl stop weewx
sudo -u weewx env PYTHONPATH=/etc/weewx/bin:/usr/share/weewx python3 -m user.rtldavis --check
```

For a pip installation, activate the WeeWX virtual environment and run
`PYTHONPATH=~/weewx-data/bin python3 -m user.rtldavis --check`. `--check`
reports numpy, librtlsdr and whether the dongle opens, with the same
instructions as the log.

## Receive without WeeWX

The same command without `--check` runs the receiver and prints every frame
with its channel, the learned frequency offset and the frames received so far:

```sh
sudo -u weewx env PYTHONPATH=/etc/weewx/bin:/usr/share/weewx python3 -m user.rtldavis --band EU --channels 1
```

`--channels` takes a comma-separated list such as `1,2`. `--device`, `--gain`
and `--ppm` match the options in the configuration reference. `--debug` shows
every hop. Stop it with Ctrl+C and start WeeWX again:

```sh
sudo systemctl start weewx
```

## EU reception and repeaters

The original EU no-decode report remains unresolved:
[lheijst/weewx-rtldavis#21](https://github.com/lheijst/weewx-rtldavis/issues/21).
A strong `rtl_power` signal verifies RF energy, not successful packet decoding.
The receiver expects an 80-bit frame including its 16-bit sync word. Longer
repeater frames need protocol samples before support can be verified.

To investigate a failure, attach the log, the SDR model and a short unsigned
8-bit IQ recording at 268800 samples/second, tuned to a channel frequency as
the receiver tunes it: the table frequency in `user/rtldavis_receiver.py` plus
the offset the log reports. For the first EU channel without offset:
`rtl_sdr -f 868077250 -s 268800 capture.cu8`. Keep direct ISS and repeater
captures separate. Offline replay needs no SDR:

```sh
PYTHONPATH=/etc/weewx/bin:/usr/share/weewx python3 -m user.rtldavis --iq capture.cu8
```

Replay prints each CRC-valid payload and its channel. It searches about
±30 kHz around the expected carrier and does not hop.
