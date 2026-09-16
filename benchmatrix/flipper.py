#!/usr/bin/env python3
"""Drive the Flipper Zero's `lfrfid` CLI over USB serial, and return RESULTS rather than prose.

⭐ DERIVED FROM `flipper.py` BY MATTHEW CARROLL, in the ChameleonUltra project at
`research/indala-psk-read/flipper.py` (c704a5c3 2026-09-11, then 96f46ab9, 629bef55, 21aeaf9d and
969138a3). Everything that makes this channel trustworthy was worked out there and is carried over
unchanged in substance: the anchored `^name HEX$` success line, the structural rejection of the
usage banner and the protocol listing, ETX termination because `rfid read` never returns on its own,
treating a refused plugin load as a DEAD INSTRUMENT rather than a zero, emulation as a held port,
and the heap-fragmentation cliff that makes a healthy reader die mid-session.

It lives here rather than being called there because a general tool that depends on one project's
research directory is not general — the same reason `dfu.py` was moved.

⛔⛔ WHAT THIS PORT CHANGES, AND WHY IT HAD TO. The harness used to run that script as a SUBPROCESS
and parse its stdout. The script prints a human summary per attempt —

        1: H10301 7B11D7  FC: 123 Card: 4567

— and prints the raw device lines only under `--verbose`. The harness matched for the raw line, did
not pass `--verbose`, and so extracted NOTHING from a Flipper that was decoding perfectly. `rd.flip`
returned an empty string for every protocol it was ever asked about. Passing `--verbose` was not
enough either: those lines are prefixed `      | `, and `.strip()` leaves the pipe, which fails an
anchor requiring a letter first. Two independent reasons the same real decode was invisible.

⇒ So this returns `Decode` objects. There is no text between the device and the caller to get wrong,
`--verbose` is a display choice again instead of a correctness one, and the anchored pattern is
applied once, here, to lines that came off the wire.

⚠ pyserial IS IMPORTED LAZILY, so the pure logic stays testable on an interpreter without it — the
same arrangement `dfu.py` uses.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass

BAUD = 115200
ETX = b"\x03"

#: `rfid read <normal|indala>` selects a FRONT END, not a protocol filter.
MODES = {"psk": "indala", "ask": "normal"}

#: name, single space, an even number of uppercase hex digits, end of line.
#:
#: ⛔⛔ THE NAME MAY CONTAIN SPACES, AND ASSUMING IT COULD NOT COST A PUBLISHED CLAIM. This was
#: `[A-Za-z][A-Za-z0-9]*` — one word — which cannot match Momentum's name for Securakey, "Radio
#: Key". A working emulation reported 0 of 6 and that number went into FINDINGS.md as an emulation
#: defect with an isolating control beside it (C177). The control was sound; the instrument was not.
#:
#: ⚠ MATCH THE SUCCESS PATH, NOT THE PROTOCOL NAME (M28). An earlier tool counted substring hits of
#: a protocol name and reported 10 successes from 5 attempts, because the command did not exist and
#: the help text contained the name twice. The structural rejections still hold: the "Available
#: protocols:" listing is tab-indented so it fails `^[A-Za-z]`, and no banner line ends in an even
#: run of hex digits.
SUCCESS = re.compile(r"^([A-Za-z][A-Za-z0-9 ]*?) ((?:[0-9A-F]{2}){2,})$")

#: The CLI printed usage or a listing instead of running what we asked, so every count after it
#: would be meaningless.
#:
#: ⛔⛔ `failed to load external command` IS THE ONE THAT COST A WHOLE UNIT (C373). `rfid` is not
#: built into the firmware — it is `/ext/apps/RFID/lfrfid.fap`, and the loader refuses it when the
#: .fap's API version does not match the running firmware. The refusal is ONE red line and then a
#: normal prompt: no usage, no listing, nothing the pattern above matches. So every attempt scored a
#: clean `-`, and eleven emulate arms reported `0/6` against a reader that was never listening.
#: ⇒ A DEAD INSTRUMENT MUST ABORT, NEVER SCORE ZERO. A null with no positive control is not
#: evidence (F05), and this one looked exactly like a firmware finding.
REJECTED = ("Available protocols:", "rfid <write | emulate>", "Unknown protocol",
            "failed to load external command")

#: ⛔⛔⛔ THE `rfid` PLUGIN DIES OF HEAP FRAGMENTATION (C377). It is a 66,304-byte .fap the loader
#: must place in ONE contiguous block. Measured across a session: 118,304 bytes largest-block at
#: boot, 63,880 after ~12 minutes and six emulate arms — with 107,464 bytes still FREE. So it is
#: fragmentation, not exhaustion, and the plugin starts refusing mid-session with nothing about the
#: bench having changed. That is why the reader looked healthy at one claim and dead at the next on
#: the SAME boot. A reboot restores it in ~10 seconds.
FAP_BYTES = 66304
FAP_HEADROOM = 12000


class FlipperError(Exception):
    """The instrument is not fit to measure with. Never scored — always raised."""


@dataclass(frozen=True)
class Decode:
    """One successful read: what the Flipper named it, the hex it printed, and its own detail."""

    name: str
    data: str
    detail: str = ""
    mode: str = ""

    @property
    def line(self) -> str:
        """The anchored form, which is what an expectation is compared against."""
        return "%s %s" % (self.name, self.data)


@dataclass
class Attempt:
    """One `rfid read`, whether or not it decoded. ⭐ A MISS IS A RECORD TOO — the denominator is
    what makes a hit rate meaningful, and M28 exists because one was once missing."""

    mode: str
    decode: Decode | None
    lines: tuple = ()


def _serial(port: str, timeout: float = 0.2):
    try:
        import serial                                    # noqa: PLC0415 - lazy, see the docstring
    except ImportError as e:                             # pragma: no cover - environment
        raise FlipperError(
            "pyserial is not installed, so the Flipper cannot be driven. The interpreter running "
            "this harness is %s — install it there:\n"
            "        %s -m pip install -r requirements.txt"
            % (sys.executable, sys.executable)) from e
    return serial.Serial(port, BAUD, timeout=timeout)


class FlipperCLI:
    """An open session on the Flipper's CLI. Use as a context manager; it holds the port.

    ⚠ ONE READER PER `/dev/cu.*`. Two processes on the same port eat each other's replies, so this
    opens for as long as it is needed and closes — and nothing else may hold the port meanwhile.
    """

    def __init__(self, port: str, settle: float = 6.0, quiet: bool = True):
        self.port, self.settle, self.quiet = port, settle, quiet
        self.s = _serial(port)
        self.transcript: list[str] = []
        time.sleep(0.4)
        self.s.reset_input_buffer()

    def __enter__(self) -> "FlipperCLI":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            self.s.close()
        except Exception:                                # noqa: BLE001 - closing must not raise
            pass

    def _drain(self, until: str, deadline: float) -> tuple[list[str], bool]:
        """Collect lines until `until` is seen or the deadline passes. Returns (lines, saw it)."""
        buf, lines = "", []
        while time.time() < deadline:
            chunk = self.s.read(4096).decode("utf-8", "replace")
            if not chunk:
                time.sleep(0.05)
                continue
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.replace("\r", "").rstrip()
                # The CLI echoes the command and prints a ">: " prompt; neither is output.
                if line.startswith(">") or not line.strip():
                    continue
                lines.append(line)
                self.transcript.append(line)
                if not self.quiet:
                    print("      | " + line)
                if until in line:
                    return lines, True
        return lines, False

    def run(self, command: str, terminator: str, settle: float | None = None) -> list[str]:
        """Send a command, wait for `terminator`, then ETX if it never came.

        ⛔ `rfid read` DOES NOT TIME OUT. It loops until a tag is decoded or the next character is
        ETX (0x03) — the `cli_is_pipe_broken_or_is_etx_next_char` loop. A failed read therefore
        never returns, and anything written afterwards is consumed as ordinary input while the
        worker is still running. A version that slept and moved on looks right whenever the read
        SUCCEEDS — i.e. every arm except the null, which is the arm that matters.
        """
        self.s.reset_input_buffer()
        self.s.write((command + "\r\n").encode())
        lines, done = self._drain(terminator, time.time() + (settle or self.settle))
        if not done:
            self.s.write(ETX)
            more, _ = self._drain(terminator, time.time() + 3.0)
            lines += more
        for line in lines:
            if any(r in line for r in REJECTED):
                raise FlipperError(
                    "the Flipper REJECTED `%s` — it printed usage or refused the plugin, not a "
                    "result. Every count from here would be a phantom (M28). Line: %r"
                    % (command, line))
        return lines

    # ------------------------------------------------------------------ the arms

    def read(self, mode="both", attempts: int = 6, stop_on_first: bool = True) -> list[Attempt]:
        """`rfid read`, returning one `Attempt` per try. No text for a caller to re-parse.

        ⭐ IT STOPS AT THE FIRST DECODE, AND THE DEFAULT USED TO BE TO RUN ALL TWELVE. A failed read
        does not return on its own — it costs the full settle plus the ETX drain, about nine
        seconds — so asking a front end that has nothing to find, six times, after the other one
        has already answered, cost 49 seconds per protocol on the bench. Across the Flipper's
        fourteen unknowns that is eleven minutes of the operator watching a spinner.
        ⇒ What the harness needs from a read is WHAT the reader prints, and one decode says it.

        ⛔ `stop_on_first=False` IS FOR A HIT RATE, AND A NULL SWEEP IS NOT ONE. A sweep decodes
        nothing by construction, so it runs every attempt either way — the denominator only matters
        where something DID answer and the question is how often (C81/C83).

        ⚠ `mode` MAY BE AN ORDER. The front ends are not symmetric: `rfid read indala` decodes ASK
        perfectly well (C353), but a PSK signal is not recoverable through the ASK front end. So
        trying the likely one first is free, and trying the other afterwards is what keeps it
        correct when the guess is wrong.
        """
        order = list(MODES) if mode == "both" else ([mode] if isinstance(mode, str) else list(mode))
        out: list[Attempt] = []
        for m in order:
            for _ in range(attempts):
                lines = self.run("rfid read " + MODES[m], "Reading stopped")
                got = decode(lines, m)
                out.append(Attempt(mode=m, decode=got, lines=tuple(lines)))
                if got and stop_on_first:
                    return out
        return out

    def emulate(self, protocol: str, data: str, seconds: int = 30) -> None:
        """`rfid emulate` — a HOLD. It blocks like `read`, so the port is kept open for the
        duration and released with ETX."""
        self.s.reset_input_buffer()
        self.s.write(("rfid emulate %s %s\r\n" % (protocol, data)).encode())
        lines, _ = self._drain("Emulating RFID...", time.time() + 3.0)
        for line in lines:
            if any(r in line for r in REJECTED) or "needs to be" in line:
                raise FlipperError("the Flipper REJECTED the emulation: %r" % line)
        if not any("Emulating" in line for line in lines):
            raise FlipperError("no 'Emulating RFID...' — it never started. Saw: %r" % lines)
        try:
            time.sleep(seconds)
        finally:
            self.s.write(ETX)
            time.sleep(0.3)

    def write_tag(self, protocol: str, data: str) -> list[str]:
        """`rfid write` — the `t55.flip` writer."""
        return self.run("rfid write %s %s" % (protocol, data), "Writing", settle=20.0)


#: Everything `rfid read` prints whatever happens: the echoed command, the two status lines, and
#: the terminator. ⭐ ANYTHING ELSE IS THE DEVICE SAYING SOMETHING.
_BOILERPLATE = ("rfid read", "reading rfid", "press ctrl+c", "reading stopped", "reading raw")


def unrecognised(lines) -> list[str]:
    """Lines the device printed that are neither boilerplate nor a decode we matched.

    ⛔⛔ THIS IS THE DIFFERENCE BETWEEN "THE READER FOUND NOTHING" AND "WE DID NOT UNDERSTAND THE
    READER", AND EVERY BUG IN THIS HARNESS SO FAR HAS BEEN THE SECOND REPORTED AS THE FIRST. The
    anchored `^name HEX$` pattern is an assumption about output shape; a protocol that renders
    differently produces no match, and a no-match was being published as a decoder gap. It already
    happened: `rd.flip` returned nothing for EVERY protocol while the Flipper decoded perfectly,
    and `fdxb` was written up as a Flipper FDX-B gap against a firmware that reads FDX-B fine.

    ⇒ A null is only evidence with a positive control (F05), and this is the control that is always
    available: if the device printed lines we cannot account for, the fault is OURS and must not be
    recorded as a finding. If it printed only the boilerplate, it genuinely heard nothing.
    """
    out = []
    for line in lines or ():
        t = line.strip()
        if not t or any(b in t.lower() for b in _BOILERPLATE):
            continue
        if SUCCESS.match(t):
            continue                       # a decode we DID match is accounted for
        out.append(t)
    return out


def front_ends_for(family: str) -> tuple:
    """Which front end to try first for a protocol of this modulation family.

    ⚠ NOT A FILTER, AN ORDER. Both are still tried — `rfid read normal` cannot recover a PSK signal,
    so guessing wrong must cost time and not a reading. `normal` handles ASK and FSK (HID H10301 is
    FSK and decodes through it); `indala` is the PSK front end and decodes ASK too (C353).
    """
    return ("psk", "ask") if family == "psk" else ("ask", "psk")


def decode(lines, mode: str = "") -> Decode | None:
    """The decoded credential from one read, or None. Only the anchored success line counts.

    ⚠ EVERYTHING BETWEEN THAT LINE AND "Reading stopped" IS THE PROTOCOL'S OWN DETAIL. Indala26
    prints FC and Card on separate lines, so taking only the next one silently drops the card
    number — which is the half that identifies the credential.
    """
    for i, line in enumerate(lines):
        m = SUCCESS.match(line.strip())
        if not m:
            continue
        detail = []
        for nxt in lines[i + 1:]:
            if "Reading stopped" in nxt or SUCCESS.match(nxt.strip()):
                break
            detail.append(nxt.strip())
        return Decode(name=m.group(1), data=m.group(2),
                      detail=" ".join(d for d in detail if d), mode=mode)
    return None


def heap_largest_block(port: str) -> int | None:
    """Largest contiguous heap block in bytes, or None if the CLI would not say."""
    s = _serial(port, timeout=0.3)
    try:
        time.sleep(0.4)
        s.reset_input_buffer()
        s.write(b"free\r\n")
        time.sleep(1.5)
        out = s.read(s.in_waiting or 1).decode("utf-8", "replace")
    finally:
        s.close()
    m = re.search(r"Maximum heap block:\s*(\d+)", out)
    return int(m.group(1)) if m else None


def reboot(port: str) -> None:
    """Power-cycle over the Flipper's own CLI and wait for the port to come back.

    ⚠ `power reboot` DROPS USB MID-COMMAND, so the write is expected to be the last thing that
    succeeds — an OSError afterwards is the SUCCESS path, not a failure.
    """
    try:
        s = _serial(port, timeout=0.3)
        time.sleep(0.3)
        s.write(b"power reboot\r\n")
        time.sleep(0.5)
        s.close()
    except OSError:
        pass
    for _ in range(40):
        time.sleep(0.5)
        try:
            _serial(port, timeout=0.3).close()
            time.sleep(1.5)
            return
        except OSError:
            continue
    raise FlipperError("the Flipper did not come back after `power reboot`")


# ------------------------------------------------------------------ used as a tool

def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m benchmatrix.flipper",
                                 description="Drive the Flipper's lfrfid CLI.")
    ap.add_argument("--port", required=True)
    ap.add_argument("--quiet", action="store_true", help="do not echo the device's lines")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read")
    r.add_argument("--mode", choices=["psk", "ask", "both"], default="both")
    r.add_argument("--attempts", type=int, default=6)
    e = sub.add_parser("emulate")
    e.add_argument("protocol")
    e.add_argument("data")
    e.add_argument("--seconds", type=int, default=30)
    sub.add_parser("heap")
    sub.add_parser("reboot")
    a = ap.parse_args(argv)

    if a.cmd == "heap":
        got = heap_largest_block(a.port)
        print("  largest heap block: %s (the rfid plugin needs %d)" % (got, FAP_BYTES))
        return 0 if (got or 0) >= FAP_BYTES + FAP_HEADROOM else 1
    if a.cmd == "reboot":
        reboot(a.port)
        print("  rebooted")
        return 0
    with FlipperCLI(a.port, quiet=a.quiet) as f:
        if a.cmd == "emulate":
            f.emulate(a.protocol, a.data, a.seconds)
            print("  stopped")
            return 0
        tries = f.read(a.mode, a.attempts)
        for t in tries:
            print("  %-4s %s" % (t.mode.upper(), t.decode.line if t.decode else "-"))
        hits = [t for t in tries if t.decode]
        print("  => %d/%d" % (len(hits), len(tries)))
        return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
