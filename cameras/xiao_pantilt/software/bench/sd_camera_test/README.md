# XIAO ESP32S3 Sense camera → microSD test

Bench proof that the Sense expansion board's camera and microSD slot both
work from the Arduino ESP32 core. No motor, switch, scheduler, or network.
The DRV8833 bench pins (GPIO1/2 AIN, GPIO3 SLP) are held LOW from the first
line of `setup()` so the head cannot move while this sketch is loaded.

## Wiring

Nothing beyond the Sense expansion board clicked onto the XIAO and a microSD
card in its slot. Pins are the official Seeed map:

| function | GPIO |
| --- | --- |
| camera XCLK / SCCB SDA / SCL | 10 / 40 / 39 |
| camera D0…D7 | 15, 17, 18, 16, 14, 12, 11, 48 |
| camera VSYNC / HREF / PCLK | 38 / 47 / 13 |
| microSD SPI CS / SCK / MISO / MOSI | 21 / 7 / 8 / 9 |

GPIO21 is both the SD chip select and the user LED, so the LED flickers on
card access and must not be driven by anything else while the card is used.

## Build, flash, talk

The XIAO_ESP32S3 board definition defaults PSRAM to **disabled**; pass
`PSRAM=opi` or `psramFound()` is false and UXGA frames will not fit.

```sh
cd cameras/xiao_pantilt/software
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:PSRAM=opi sd_camera_test
arduino-cli upload  --fqbn esp32:esp32:XIAO_ESP32S3:PSRAM=opi -p /dev/ttyACM1 sd_camera_test
```

Find the port with `arduino-cli board list`; the XIAO enumerates as an
Espressif USB JTAG/serial unit. Opening the serial port resets the board
(and each boot takes one capture), so expect the sequence number to climb
by one per monitor session.

Serial 115200, single characters:

- `c` capture one JPEG and save it as `/xiao_sd_test/NNNNN.jpg`
- `l` list the directory
- `i` PSRAM / heap / card / sequence info
- `g` dump the last saved file as base64 between `BEGIN … END` lines
- `a` toggle auto capture every 10 s
- `h` help

Filenames use a sequence counter in NVS (`Preferences` namespace `sdcam`),
reserved before the write; the file is written as `.tmp`, flushed, then
renamed, so a crash mid-write never leaves a half file under a final name.

## Result (2026-09-12)

Proven on the real head with a 64 GB SDHC card:

- Sensor reports PID `0x3660` (OV3660), not the OV2640 in the spec.
- UXGA 1600×1200 JPEG at quality 10 is 60–70 kB and writes in about 175 ms.
- `samples/00003.jpg` is the third boot capture, pulled back with `g`.

The dump was decoded on the host with a small pyserial script: read the
`BEGIN path size` line, strip whitespace from the base64 body, `base64.b64decode`,
and check the length matches.
