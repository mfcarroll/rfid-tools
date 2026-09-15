"""`bench setup` — find the devices, learn which Chameleon is which, write `.env`.

⛔⛔ WHY THIS EXISTS. The Proxmark and the Flipper name themselves in their USB product strings. The
Chameleons do not: two of them enumerate as `/dev/tty.usbmodem<serial>`, and nothing in that string
says which is the one labelled 1 on the bench. Getting them crossed is easy, silent, and poisons a
whole run — every arm attributed to the wrong device and the wrong firmware build.

⛔ AND THE RADIO IDENTITY CHECK CANNOT SAVE YOU FROM IT. That check arms `cu1` with a unique id and
asks a reader who is there — but "cu1" means *whatever `CU1_PORT` points at*. If the ports are
crossed, it confirms the lie. The two checks cover different failure modes:

    setup  → which physical device is on which port
    radio  → which physical device is in the stack

Neither substitutes for the other, and the second is only as good as the first.

⭐ SO IDENTITY IS ESTABLISHED ONCE, BY EYE, AND REMEMBERED BY CHIP ID. `hw chipid` returns a
permanent hardware identifier. The operator does the blink dance once; after that the mapping holds
however the ports are reshuffled, because it is keyed on the silicon and not on the enumeration
order. A device whose chip id is already known is assigned with no questions asked.
"""

from __future__ import annotations

import datetime as _dt
import glob
import os

from . import cues
from .devices import CHIPID_RE as _CHIPID_RE, DEFAULT_CU_PY, DEFAULT_PM3, Chameleon

ENV_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

#: Product-string fragments that name a device unambiguously. Everything else is a candidate
#: Chameleon and gets asked directly.
FLIPPER_HINTS = ("flip",)
PM3_HINTS = ("iceman", "proxmark", "pm3")

#: Defined in devices.py so the runtime check and setup cannot drift apart.
CHIPID_RE = _CHIPID_RE

#: How many LF reads to fire while the operator is looking. One is too brief to catch.
BLINK_READS = 4


def load_env(path: str = ENV_PATH) -> dict:
    """Read `.env` into a dict. Missing file is not an error — nothing is configured yet."""
    out: dict[str, str] = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def apply_env(path: str = ENV_PATH) -> dict:
    """Populate os.environ from `.env` WITHOUT overriding anything already set.

    ⚠ AN EXPLICIT VALUE ALWAYS WINS. A one-off `CU1_PORT=... ./bench run` must not be silently
    overwritten by a stale file, or the override does the opposite of what it looks like.
    """
    values = load_env(path)
    for k, v in values.items():
        os.environ.setdefault(k, v)
    return values


def write_env(values: dict, path: str = ENV_PATH) -> None:
    order = ("PM3", "CU1_PORT", "CU1_CHIPID", "CU2_PORT", "CU2_CHIPID", "FLIPPER_PORT")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Written by `bench setup` on %s. Not tracked by git.\n"
                 "# CU*_CHIPID is the permanent hardware id; the port may change between sessions,\n"
                 "# the chip id may not. `bench run` refuses to start if they disagree.\n"
                 % _dt.datetime.now().isoformat(timespec="seconds"))
        for k in order:
            if values.get(k):
                fh.write("%s=%s\n" % (k, values[k]))
        for k in sorted(set(values) - set(order)):
            if values[k]:
                fh.write("%s=%s\n" % (k, values[k]))


# ------------------------------------------------------------------ discovery

def serial_ports() -> list[str]:
    return sorted(set(glob.glob("/dev/tty.usbmodem*")))


def classify(ports: list[str]) -> tuple[list[str], list[str], list[str]]:
    """(flipper, proxmark, unknown) by product string. Unknown ones get asked directly."""
    flip = [p for p in ports if any(h in p.lower() for h in FLIPPER_HINTS)]
    pm3 = [p for p in ports if any(h in p.lower() for h in PM3_HINTS)]
    rest = [p for p in ports if p not in flip and p not in pm3]
    return flip, pm3, rest


def chip_id(port: str, cli: str = DEFAULT_CU_PY, timeout: int = 15) -> str | None:
    """The permanent hardware id, or None if this port is not a Chameleon."""
    cham = Chameleon(port=port, cli=cli, timeout=timeout)
    try:
        out = cham.exec("hw chipid")
    except Exception:                                   # noqa: BLE001 — a bad port is not fatal
        return None
    m = CHIPID_RE.search(out or "")
    return m.group(1).upper() if m else None


def blink(port: str, cli: str = DEFAULT_CU_PY, reads: int = BLINK_READS) -> None:
    """Make one device visibly busy, so the operator can name it by looking at the bench.

    ⭐ THE LEDs ARE THE OUT-OF-BAND CHANNEL. Every other way of asking "which one is this?" runs
    through the same USB mapping we are trying to establish, and so cannot check it. Tracing a cable
    by hand can; so can watching which device lights up. This is the second, and it does not require
    the operator to move anything.
    """
    cham = Chameleon(port=port, cli=cli, timeout=20)
    cham.exec("hw mode -r")
    for _ in range(reads):
        cham.exec("lf em 410x read")


def find_pm3(existing: str | None = None) -> str:
    """The `pm3` wrapper. It finds its own port, so only the binary path is configuration."""
    for cand in (existing, os.environ.get("PM3"), DEFAULT_PM3):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(d, "pm3")
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return DEFAULT_PM3


# ------------------------------------------------------------------ the interactive part

def identify_chameleons(ports: list[str], known: dict, cli: str = DEFAULT_CU_PY,
                        ask=None, out=print) -> dict:
    """Map each Chameleon port to the label on its case. Returns {"cu1": port, "cu2": port, ...}.

    ⚠ ONLY UNKNOWN DEVICES ARE ASKED ABOUT. A chip id already in `.env` is assigned silently, so the
    blink dance is a one-time cost and not a per-session ritual the operator learns to click through.
    """
    ask = ask or _ask_label
    by_chip = {v: k.replace("_CHIPID", "").lower()
               for k, v in known.items() if k.endswith("_CHIPID") and v}
    found: dict[str, str] = {}
    unknown: list[tuple[str, str]] = []

    for port in ports:
        cid = chip_id(port, cli)
        if cid is None:
            out("    · %s did not answer `hw chipid` — not a Chameleon, skipping" % port)
            continue
        label = by_chip.get(cid)
        if label:
            out("    ✓ %s is %s (chip %s, already known)" % (port, label.upper(), cid))
            found[label] = port
            found[label + "_chipid"] = cid
        else:
            unknown.append((port, cid))

    for port, cid in unknown:
        out("\n    watch the bench — one Chameleon is about to blink.")
        blink(port, cli)
        label = ask(port, cid)
        if label is None:
            out("    · skipped %s" % port)
            continue
        if label in found:
            out("    ⛔ %s is already mapped to %s. Two devices cannot both be %s."
                % (label.upper(), found[label], label.upper()))
            return {}
        found[label] = port
        found[label + "_chipid"] = cid
        out("    ✓ %s is %s (chip %s) — remembered" % (port, label.upper(), cid))
    return found


def _ask_label(port: str, cid: str) -> str | None:
    """Which physical device just blinked? The answer is the label on its case."""
    cues.cue_check("which Chameleon blinked?")
    r = cues.ask_choice("    which Chameleon blinked — 1, 2, or s to skip? ", "12s", "s",
                        spoken="which Chameleon blinked, one or two?")
    return None if r == "s" else "cu" + r
