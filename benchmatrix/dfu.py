#!/usr/bin/env python3
"""Nordic DFU flashing for one named device — trigger and program in a single process.

⛔⛔ THE BOOTLOADER WINDOW IS SHORTER THAN THE GAP BETWEEN TWO SHELL COMMANDS. Trigger DFU in one
call and run `nrfutil device program` in the next, and the device has already fallen back to the
application: nrfutil then emits no events at all and exits clean, and the version afterwards is the
OLD build. That is a race, not a flash failure, and it is indistinguishable from success by output
alone. So the trigger and the program happen inside one process, polling the bootloader's VID/PID
from here rather than shelling out to look.

⛔⛔ AND IT MUST TARGET ONE NAMED DEVICE. The stock `enter_dfu.py` walks the port list and takes the
first device matching the Chameleon VID/PID, which with two units on the bench is a coin toss on
enumeration order — the wrong one goes into DFU. This takes a port and refuses anything else. It
also refuses to fire when a device is ALREADY in DFU, because the port a bootloader scan returns is
then ambiguous and the flash could land on either.

⭐ RUN AS ITS OWN PROCESS, UNDER WHATEVER PYTHON HAS pyserial. Nothing here imports from the rest of
the package, so it can be handed to a virtualenv interpreter without any path arrangement:

    python3 dfu.py '{"port": "/dev/tty.usbmodemX", "zip": "...", "nrfutil": "..."}'

It prints one JSON object per line, so the caller can report each step rather than parse prose.
"""

import json
import os
import subprocess
import sys
import time

# ⚠ IMPORTED LAZILY, NOT AT MODULE LEVEL. Exiting on import would make the pure logic here — which
# USB id is which, what counts as a success record — impossible to unit-test on an interpreter
# without pyserial, and that logic is the part most worth testing.
try:
    import serial
    import serial.tools.list_ports as list_ports
    HAVE_SERIAL = True
except ImportError:
    serial = list_ports = None
    HAVE_SERIAL = False

DEFAULTS = {
    "app_usb": "6868:8686",
    "dfu_usb": "1915:521F",
    # The Chameleon's "enter DFU" command frame.
    "trigger": "11ef03f2000000000b00",
    "wait": 15.0,
    "back_wait": 20.0,
    "options": [],
}


def emit(step, ok, detail="", **extra):
    print(json.dumps({"step": step, "ok": ok, "detail": detail, **extra}), flush=True)


def same_device(a, b):
    """`/dev/cu.usbmodemX` and `/dev/tty.usbmodemX` are the same physical device.

    ⚠ macOS exposes every USB serial device TWICE and `comports()` reports only the `cu.` form,
    while every note and command on this bench names the `tty.` form. Matching the literal string
    rejects the right device.
    """
    strip = lambda d: (d or "").replace("/dev/cu.", "").replace("/dev/tty.", "")
    return strip(a) == strip(b)


def usb(spec):
    vid, _, pid = spec.partition(":")
    return int(vid, 16), int(pid, 16)


def ports_matching(ident):
    return [p.device for p in list_ports.comports() if (p.vid, p.pid) == ident]


def run(cfg):
    if not HAVE_SERIAL:
        emit("import", False, "pyserial is not installed for %s — point the target's `python` at "
                              "an interpreter that has it" % sys.executable)
        return 1
    app, dfu = usb(cfg["app_usb"]), usb(cfg["dfu_usb"])
    zip_path = os.path.abspath(cfg["zip"])

    if not os.path.exists(zip_path):
        emit("artifact", False, "no such firmware file: %s" % zip_path)
        return 1

    already = ports_matching(dfu)
    if already:
        emit("preflight", False,
             "a device is ALREADY in DFU (%s) — refusing, because a flash now could not tell the "
             "two apart. Power-cycle it first." % ", ".join(already))
        return 1

    ports = list(list_ports.comports())
    target = [p for p in ports if same_device(p.device, cfg["port"]) and (p.vid, p.pid) == app]
    if not target:
        seen = ", ".join("%s (%04x:%04x)" % (p.device, p.vid or 0, p.pid or 0) for p in ports)
        emit("preflight", False, "%s is not attached in application mode. Attached: %s"
             % (cfg["port"], seen))
        return 1
    others = [p.device for p in ports
              if (p.vid, p.pid) == app and not same_device(p.device, cfg["port"])]
    emit("preflight", True, "target %s; leaving alone: %s"
         % (cfg["port"], ", ".join(others) or "(none)"), others=others)

    s = serial.Serial(port=cfg["port"], baudrate=115200)
    try:
        s.dtr = 1
        s.timeout = 0
        s.write(bytes.fromhex(cfg["trigger"]))
    finally:
        s.close()

    # ⛔ Poll from INSIDE this process. `nrfutil device list` between the trigger and the program is
    # itself slow enough to miss the window.
    t0 = time.time()
    boot = []
    while time.time() - t0 < cfg["wait"]:
        boot = ports_matching(dfu)
        if boot:
            break
        time.sleep(0.05)
    if not boot:
        emit("trigger", False,
             "the bootloader never enumerated within %.0fs — NOTHING was flashed and the device is "
             "back in the application. This is a TRIGGER failure, not a flash failure."
             % cfg["wait"])
        return 1
    emit("trigger", True, "bootloader up at %s after %.1fs" % (", ".join(boot), time.time() - t0))

    # ⛔⛔ QUIET OUTPUT IS NOT SUCCESS. Captured non-interactively, nrfutil prints only an unrelated
    # JLink warning — which is exactly what a flash that never happened also prints. `--json` gives
    # a record per progress step ending in an explicit result, and THAT is the evidence.
    argv = [cfg["nrfutil"], "--json", "device", "program", "--firmware", zip_path,
            "--traits", "nordicDfu"]
    if cfg.get("options"):
        argv += ["--options", ",".join(cfg["options"])]
    r = subprocess.run(argv, capture_output=True, text=True)
    records = []
    for line in (r.stdout or "").splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            pass
    ok = _succeeded(records)
    if not ok:
        tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        emit("program", False,
             "nrfutil exit %d and no success record in %d JSON line(s)%s"
             % (r.returncode, len(records), (": " + tail[-1][:160]) if tail else ""),
             records=len(records))
        return 1
    emit("program", True, "nrfutil reported success over %d progress record(s)" % len(records),
         records=len(records))

    # ⛔ The device has to come BACK. Leaving it in the bootloader is worse than not flashing.
    t0 = time.time()
    while time.time() - t0 < cfg["back_wait"]:
        if any(same_device(p.device, cfg["port"]) and (p.vid, p.pid) == app
               for p in list_ports.comports()):
            emit("returned", True, "back in application mode after %.1fs" % (time.time() - t0))
            return 0
        time.sleep(0.25)
    emit("returned", False,
         "the device did not come back in application mode within %.0fs — do NOT leave it like "
         "this." % cfg["back_wait"])
    return 1


def _succeeded(records):
    """⚠ POSITIVE EVIDENCE ONLY. An empty record list is the race this file exists to prevent, and
    a zero exit status with no records looks identical to a flash that happened."""
    for rec in records:
        blob = json.dumps(rec).lower()
        if '"result"' in blob and "success" in blob:
            return True
    return False


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        sys.exit("usage: dfu.py '<json config>'")
    cfg = dict(DEFAULTS)
    cfg.update(json.loads(argv[0]))
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
