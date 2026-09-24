# openmv_n6 — working notes

The README is the reference; this file is what a session on this board
needs first.

- **Ask sarg first** (`sarg ask "OpenMV N6 <symptom>"`): the fw 5.x API
  differences and the CSI hang list are recorded there.
- **Bench:** USB serial `/dev/serial/by-id/usb-MicroPython_Pyboard_Virtual_Comm_Port_in_FS_Mode_31001c00025043364d343000-if00`
  (bare `/dev/ttyACM*` numbering moves — never hardcode it), mass storage
  `/media/wroscoe/PYBFLASH`. `fuser -v` the port before blaming the board;
  `udisksctl unmount` the drive before anything that resets it. The board
  re-enumerates on every reset **and on every deep-sleep wake**
  (`game_lowpower`'s `board_rest()` -> `machine.deepsleep()`; USB drops
  ~1.1 s after and comes back ~2 s after the wake) — a serial reader must
  reopen with retries every time, not just after a reset.
- **`game_lowpower` (unflashed, PLAN.md):** `software/host/monitor.py`
  finds the port by serial number and reconnects across wakes as well as
  resets — use it instead of a one-shot terminal for any bench session.
  `software/host/bench_sleep.py` drives PLAN §8's bench gates
  (standby/RTC/backup-regs, button, lightsleep, SD, wake_cost, longwake)
  over mpremote; it resets the live board on every call, so never run it
  without being asked, and always unmount `/media/wroscoe/PYBFLASH` first
  (it does this itself, but the rule holds for anything else that resets
  the board too — the host's FAT mount racing the board's own flash writes
  is the classic way to corrupt it). The `ota_main.py` (loader) change for
  this profile needs a USB copy to take effect — the loader is never OTA'd.
- **Ship code:** bump `APP_VERSION` in `software/app/board.py`, run
  `tools/dustycli/dusty.py cameras/n6cam --stage`, `POST /refresh`; `/status`
  shows the new version within ~10 s and `fw_pending` clears after the first
  upload. A crash at import rolls back and blacklists — a wrong build costs
  one boot, not a USB session.
- **Change tuning:** field path — hold USER for a contact, open the device
  page's settings form, change a value there; it lands directly in
  `n6cam.json` on the sensorhub and applies at the next pull. Workstation
  path — edit `~/.dusty/config.toml` `[camera.openmv_n6]`, run
  `tools/dustycli/dusty.py cameras/n6cam --no-bundle`, `POST /refresh`; this only
  *seeds* keys not already on the server (`--reset-config` to force the
  workstation's values back). Keys must exist in `camera.toml [tuning]`
  (firmware first, then config).
- **Watch the stream with a socket client, not curl:** `curl -N` on this
  host drained the socket so slowly the board hit write timeouts
  (`viewer dropped OSError(110)`) and the stream looked broken at 1 fps; a
  plain Python socket reader gets ~33 fps / 600 kB/s.
- The interrupted app (`mpremote exec`, REPL) must be followed by
  `mpremote reset` so the loader starts the app again.
- `batt_v` uses an inferred divider (1.5). First thing with a meter: read
  the pack, compare, fix `BATT_DIVIDER` in `board.py`.
- **PWR button off/on = a contact.** `wakecycle.py`'s `_one_wake` now runs a
  contact on *every* cold boot (power-on, PWR off/on, a watchdog reset) —
  not just the first one after provisioning — so cycling power in the field
  is the deliberate way to force a contact; a `'soft'` reset (mpremote, an
  OTA install's own reboot) does not.
- **Two networks in secrets.** `contact.py` scans before joining: if
  `secrets.LAN_SSID` (home LAN, `~/.dusty/secrets.toml [wifi]`) is in
  range, it joins that and points `uplink.py` at
  `LAN_HOST/LAN_PORT/LAN_TLS` (`~/.dusty/config.toml [server]`, no TLS);
  otherwise it joins the phone hotspot/public path as before. `secrets.py`
  now carries both sets of keys (dustygen).
- **`bench_contact_n` tuning key** (default `0`, `camera.toml [tuning]`):
  set it > 0 on a bench within reach of the home LAN and every Nth wake
  scans for it and runs a contact if seen — OTA/config without holding the
  button. Remember to set it back to `0` before the board goes off-grid.
