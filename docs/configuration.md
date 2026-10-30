# Configuration reference

Options belong in `[Rtldavis]` in `weewx.conf`.

| Option | Default | Meaning |
| --- | --- | --- |
| `driver` | | Must be `user.rtldavis`. |
| `transceiver_frequency` | `EU` | `EU`, `US` or `NZ`. |
| `iss_channel` | `1` | ISS transmitter channel, 1 through 8. |
| `anemometer_channel` | `0` | Separate wind transmitter, 1 through 8; 0 uses ISS wind. |
| `leaf_soil_channel` | `0` | Leaf/soil transmitter, 1 through 8; 0 disables it. |
| `temp_hum_1_channel`, `temp_hum_2_channel` | `0` | Extra temperature/humidity transmitters; 0 disables them. |
| `rain_bucket_type` | `1` | 1 for 0.2 mm, 0 for 0.01 inch per tip. |
| `device` | `0` | Dongle index, counted from 0, or the dongle's serial number. |
| `gain` | `auto` | Tuner gain in dB, or `auto`. The nearest gain the tuner supports is used. |
| `ppm` | `0` | Expected frequency error of the dongle in ppm. The frequency search starts there. |
| `debug_parse`, `debug_rain` | `0` | Parser detail level 0–3 and rain debug messages. WeeWX debug logging must also be enabled. |
| `debug_rtld` | `0` | 1 or more logs every hop and frame of the receiver. WeeWX debug logging must also be enabled. |
| `save_pct_good_per_transmitter` | `False` | Archive reception percentages for up to four active transmitters. |
| `log_humidity_raw` | `False` | Log changes in the unconverted humidity value. |
| `sensor_map` | built-in mapping | Nested mapping from WeeWX field names to decoded observations. Entries are merged into the built-in mapping. |

`weectl station reconfigure --driver=user.rtldavis` asks for
`transceiver_frequency`, `iss_channel` and `rain_bucket_type`. It proposes
bucket type 0 for the US band and 1 otherwise.

## Frequency correction

Until the first frame arrives, the receiver searches five tuning offsets around
`ppm`: 0, -60, +60, +120 and -120 kHz. Each step lasts one synchronization
period: 18 seconds in the EU band and 136 seconds in the US and NZ bands with
an ISS on channel 1, up to 21 and 159 seconds on channel 8. Once a frame arrives, the receiver corrects the tuning for each
transmitter and channel from the frequency error of every frame. The log
reports the offset found, in kHz and ppm.

Set `ppm` only to shorten the search for a dongle known to be far off, or to
avoid the EU limitation in the README. The receiver never changes the dongle's
own frequency correction.

## Observations

Standard output includes temperature, humidity, wind speed/direction, transmitter
reported gust, rain, rain rate, radiation, UV and transmitter battery status.
Rain comes only from `iss_channel`, wind only from the selected wind transmitter.
`windGust` is the ISS's stored peak, whose reporting window is defined by the
transmitter. Its direction is unavailable. WeeWX still aggregates LOOP wind
samples for archive records.

Extra stations provide `temp_1`, `temp_2`, `humid_1`, `humid_2`, `soil_temp_1` through
`soil_temp_4`, `soil_moisture_1` through `soil_moisture_4`, `leaf_temp_1`,
`leaf_temp_2`, `leaf_wetness_1` and `leaf_wetness_2`. Configure output fields in
`[[sensor_map]]`. The default mapping is in `RtldavisDriver.DEFAULT_SENSOR_MAP`.
An I2C BMP280 or BME280 requires its own WeeWX service; this driver reads no I2C sensor.

## Legacy database fields

For existing databases, diagnostic mappings retain the original field aliases:

| Decoded observation | Database field | Unit |
| --- | --- | --- |
| `pct_good_0` … `pct_good_2` | `extraTemp1` … `extraTemp3` | percent |
| `pct_good_3` | `leafTemp2` | percent |
| `freqError0` … `freqError4` | `consBatteryVoltage`, `hail`, `hailRate`, `heatingTemp`, `heatingVoltage` | hertz |

These fields have diagnostic units when the driver loads. Do not also use them
for their usual temperature, battery or precipitation meanings. Give additional
observations different output names and add matching database columns and WeeWX
unit groups. Overall reception uses the standard `rxCheckPercent` field.

Reception statistics start after the first archive establishes a baseline.
They count the first four configured transmitters, ordered by channel. A silent
transmitter contributes zero reception.

`freqError0` … `freqError4` hold the learned offset in Hz of one transmitter on
each of the five EU channels, from the channel's table frequency. With several
transmitters, the stored transmitter changes every two days. US and NZ offsets
are not stored. The values ride on the observation packet of the same frame.

## Rejected readings

The receiver checks the frame CRC. One burst can decode at several sample
offsets; the payload most of these decodes agree on is used, and a second
frame from the same transmitter within two seconds is ignored. Frames of eight
zero bytes, which pass the CRC, are discarded. The driver discards frames whose
message type no transmitter sends: 0, 1, 0xB, 0xD and 0xF from an ISS,
anemometer or temperature/humidity station.

Rain counter changes below zero are treated as wraparound only below -100.
Changes above 60 tips are rejected. Rejected counters do not replace the last
valid baseline; repeating the rejected value establishes a new baseline with
zero rain. A reset or long reception gap can lose rain because the seven-bit
counter cannot distinguish every wrap from corruption.

Digital temperature sentinels `0xFFC` and `0xFF8`, invalid thermistor resistances,
and zero rain-tip intervals produce missing observations.
CRC and timing checks cannot reject every plausible, isolated corrupt frame.
Use WeeWX's `[StdQC]` for local observation ranges.
