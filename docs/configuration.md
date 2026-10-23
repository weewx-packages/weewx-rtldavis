# Configuration reference

Options belong in `[Rtldavis]` in `weewx.conf`.

| Option | Default | Meaning |
| --- | --- | --- |
| `driver` | | Must be `user.rtldavis`. |
| `cmd` | `rtldavis` | Receiver executable and optional arguments. Shell quoting is supported; shell operators are not executed. |
| `path` | unset | Directories prepended to the receiver's `PATH`. |
| `ld_library_path` | unset | Receiver shared-library path. |
| `transceiver_frequency` | `EU` | `EU`, `US` or `NZ`. |
| `iss_channel` | `1` | ISS transmitter channel, 1 through 8. |
| `anemometer_channel` | `0` | Separate wind transmitter, 1 through 8; 0 uses ISS wind. |
| `leaf_soil_channel` | `0` | Leaf/soil transmitter, 1 through 8; 0 disables it. |
| `temp_hum_1_channel`, `temp_hum_2_channel` | `0` | Extra temperature/humidity transmitters; 0 disables them. |
| `rain_bucket_type` | `1` | 1 for 0.2 mm, 0 for 0.01 inch per tip. |
| `debug_parse`, `debug_rain`, `debug_rtld` | `0` | Parser detail level 0–3, rain debug messages, receiver detail level 0–3. WeeWX debug logging must also be enabled. |
| `save_pct_good_per_transmitter` | `False` | Archive reception percentages for up to four active transmitters. |
| `log_humidity_raw` | `False` | Log changes in the unconverted humidity value. |
| `sensor_map` | built-in mapping | Nested mapping from WeeWX field names to decoded observations. Entries are merged into the built-in mapping. |

The configuration editor supplies an absolute executable path and enables receiver
detail level 2. The table lists fallback values when an option is absent.
The driver appends `-tf` and `-tr`; configure these through the channel options.
For receiver flags, run `rtldavis -h`. `-d` selects a USB index or serial number;
`-ppm` adjusts the dongle's frequency calibration, and `-fc` adds a fixed Hz offset.

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
The receiver reports counters for its first four active channels, ordered by
transmitter ID. A silent channel contributes zero reception. An interval whose
counter reset is omitted. EU frequency errors rotate between transmitters in
two-day blocks; US/NZ frequency errors are not stored.

## Rejected readings

The driver checks frame CRC and rejects transmissions from the same sender
less than two seconds after its previous accepted frame, using receiver time.
It accepts repeated payloads at normal transmission intervals.

Rain counter changes below zero are treated as wraparound only below -100.
Changes above 60 tips are rejected. Rejected counters do not replace the last
valid baseline; repeating the rejected value establishes a new baseline with
zero rain. A reset or long reception gap can lose rain because the seven-bit
counter cannot distinguish every wrap from corruption.

Digital temperature sentinels `0xFFC` and `0xFF8`, invalid thermistor resistances,
and zero rain-tip intervals produce missing observations.
CRC and timing checks cannot reject every plausible, isolated corrupt frame.
Use WeeWX's `[StdQC]` for local observation ranges.
