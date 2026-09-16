"""The three device channels, plus a scripted stand-in for dry runs and tests.

Channels are UNCHANGED IN KIND from `t5577_campaign.py` — `pm3_exec`/`pm3_probe` for the Proxmark,
a subprocess for the Flipper, `cu.py` for the Chameleon. What is added is arming (the campaign only
ever read) and, on every channel, a `alive()` proof of life.

⛔⛔ THE LIVENESS RULE (RULES.md §5). Every failure marker in `PM3_FAIL` below was added AFTER a
failure got through it — offline mode, wrapper errors, a client/firmware version mismatch that cost
a whole bench session. The structural fix
is to require EVIDENCE THE DEVICE ANSWERED rather than to enumerate the ways it did not, which is
why `alive()` checks both. `Using UART port ...` is NOT such evidence: it appears identically in a
working session and in the version-mismatch failure.

⛔⛔ AND ON THE FLIPPER IT IS THE DIFFERENCE BETWEEN A RESULT AND A VOID SESSION. Eleven
arms once read `psk -  ask -` with a clean null either side, and the truth was that the `rfid`
plugin had refused to load — a silent reader and a silent emulator produce IDENTICAL numbers. Every
Flipper read here goes through `flipper.py`, which returns non-zero when the instrument is dead,
and a non-zero return aborts the block rather than being scored.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

from . import registry as reg
from .stations import T5577

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))          # .../rfid
CHAMELEON_ROOT = os.path.join(REPO, "ChameleonUltra")
RESEARCH = os.path.join(CHAMELEON_ROOT, "research", "indala-psk-read")

DEFAULT_PM3 = os.environ.get("PM3", os.path.join(REPO, "proxmark3", "pm3"))
DEFAULT_CU_PY = os.environ.get("CHAMELEON_CLI",
                               os.path.join(CHAMELEON_ROOT, "software", "script", "cu.py"))
DEFAULT_FLIPPER_PY = os.environ.get("FLIPPER_PY", os.path.join(RESEARCH, "flipper.py"))

PM3_FAIL = ("claimed by another process", "could not open", "waiting for proxmark3",
            "failed to open", "no proxmark3 found", "permission denied", "resource busy",
            "unable to open", "timed out", "offline mode", "[pm3 error running",
            "cannot communicate with the proxmark3", "capabilities structure version",
            "please flash the proxmark3 with the same version")
PM3_ALIVE = ("communicating with pm3 over", "max frame size:")

#: ⛔ A WRITE IS CONFIRMED BY EVIDENCE IT HAPPENED, not by the absence of an error. Every `lf <proto>
#: clone` in the client prints this on the success path (checked across all sixteen tier-0
#: commands), and a rejected argument prints usage text instead. Without a positive check, a refused
#: clone leaves the tag holding its PREVIOUS credential, the read that follows decodes nothing, and
#: the harness reports "this reader cannot judge this protocol" — a bench verdict for what is
#: actually a one-line registry error. That misattribution is exactly what this project exists to
#: prevent, so the write says so itself rather than being inferred from what came after it.
PM3_WROTE = ("done!", "done:")

#: ⛔⛔ `lf t55xx detect` IS A PREREQUISITE FOR EVERY DIRECT T5577 BLOCK READ, AND IT IS NOT ITSELF A
#: BLOCK READ. It works out the modulation and bit rate from what the tag is putting on the air, and
#: the block 0 it reports is INTERPRETED FROM THAT SIGNAL rather than fetched from block 0. The
#: Proxmark needs it because it cannot decode an addressed block read — block 0 included — without
#: first knowing the signalling. Anything added later that reads blocks directly must run it first,
#: and must not treat its block 0 as a direct read.
#:
#: ⭐ IT IS ALSO THE RIGHT WAY TO CONFIRM A WIPE, and better than the silence this used to check. A
#: silent protocol decoder could mean a wiped tag, a tag that is not on the pad, or a field that is
#: off. `detect` answering with the default configuration is POSITIVE evidence: a chip replied, and
#: what it is transmitting is the wiped config.
T55_DEFAULT_BLOCK0 = ("000880e0",)          # T55x7 default; a Q5/T5555 wipes to 6001f004
T55_Q5_BLOCK0 = ("6001f004",)
T55_PRESENT = ("chip type", "block0")

#: ⛔⛔ A GRID THAT CANNOT SAY WHICH FIRMWARE PRODUCED IT CANNOT BE CITED LATER. The two Chameleons
#: on this bench run different builds on purpose — that is half of why there are two — so "the
#: Chameleon decodes Keri" is not a claim about anything until it says WHICH Chameleon and which
#: build. The versions come out of the `hw version` that proof of life already runs, so recording
#: them costs nothing but must not be skipped.
#: ⚠ THE CLIENT VERSION MATTERS TOO, NOT ONLY THE FIRMWARE. A mismatched Proxmark client fails every
#: command while looking cheerful, and that pairing has cost a bench session before now.
PM3_OS_RE = re.compile(r"^\s*OS\.*\s+(.+?)\s*$", re.M)
PM3_CLIENT_RE = re.compile(r"^\s*Client\.*\s+(.+?)\s*$", re.M)
CU_VERSION_RE = re.compile(r"Chameleon\s+(\w+),\s*Version:\s*(\S+)\s*\(([^)]+)\)")

#: The Flipper's success line, from `flipper.py`: name, one space, an even number of uppercase hex
#: digits, alone on the line. ⛔ The name MAY CONTAIN SPACES ("Radio Key"), and assuming it could
#: not scored a working emulation 0 of 6 and put that number in FINDINGS.md as a defect.
FLIP_SUCCESS = re.compile(r"^([A-Za-z][A-Za-z0-9/\- ]*?)\s+([0-9A-F]{4,})$")
FLIP_DECODE_MARKER = r"^[A-Za-z][A-Za-z0-9/\- ]*?\s+[0-9A-F]{4,}$"

#: The Chameleon's permanent hardware id, as `hw chipid` prints it. Shared with
#: setup.py so the two cannot drift apart.
CHIPID_RE = re.compile(r"Device chip ID[:\s]+([0-9A-Fa-f]{4,})")
#: The whole line, so it can be stripped before the output is matched for a decode.
CHIPID_LINE_RE = re.compile(r"^.*Device chip ID[:\s]+[0-9A-Fa-f]{4,}.*$\n?", re.M)


class DeviceError(Exception):
    """The instrument is not fit to measure with. Never scored — always aborts the block."""


class WrongDevice(DeviceError):
    """A command reached a device other than the one it was addressed to.

    ⛔⛔ THE WORST FAILURE THIS BENCH HAS. It is silent by construction: the wrong Chameleon answers
    confidently, with no error and no wrong exit code, and every arm gets attributed to the wrong
    device and the wrong firmware build. `cu.py` carries its own scar from exactly this — a
    correctly flashed device was graded through its neighbour twice, and the flashing tool was
    blamed. Hence the check on EVERY action rather than once at startup.
    """


def _run(argv: list[str], timeout: int) -> str:
    try:
        # ⛔ errors="replace" IS LOAD-BEARING. `lf t55xx dump` puts raw credential bytes in the
        # stream and strict UTF-8 raises; a bare except then returns only the error string, and a
        # DECODE ERROR MUST NEVER BE REPORTABLE AS A HARDWARE VERDICT.
        r = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL)
        return (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return "\n[TIMED OUT after %ss running %s]\n" % (timeout, shlex.join(argv[:3]))
    except Exception as e:                                        # noqa: BLE001 - reported, not raised
        return "\n[pm3 ERROR running '%s': %s]\n" % (shlex.join(argv[:3]), e)


# ===================================================================== Proxmark3

@dataclass
class Pm3:
    """Reader `rd.pm3`, and the writer that makes the `t55.pm3` gold reference."""

    binary: str = DEFAULT_PM3
    timeout: int = 90
    id: str = "rd.pm3"
    #: Filled in by `alive()` from the same `hw version` it already runs.
    reported: str = ""

    def exec(self, *cmds: str, timeout: Optional[int] = None) -> str:
        return _run(shlex.split(self.binary) + ["-c", " ; ".join(cmds)], timeout or self.timeout)

    def alive(self) -> tuple[bool, str]:
        out = self.exec("hw version", timeout=25)
        low = out.lower()
        for m in PM3_FAIL:
            if m in low:
                return False, "pm3: %s" % m
        if not low.strip():
            return False, "pm3: no output — the client did not connect"
        if not any(m in low for m in PM3_ALIVE):
            return False, ("pm3: the client ran but the device never answered — no proof of life in "
                           "`hw version`. Check the CLIENT/FIRMWARE pairing first: a shimmed or "
                           "mismatched client fails EVERY command while looking cheerful.")
        self.reported = _pm3_version(out)
        return True, "pm3: alive — %s" % self.reported

    def read(self, p: reg.Protocol) -> str:
        return self.exec(p.pm3_read)

    def write_t55(self, p: reg.Protocol) -> str:
        """Write the gold reference onto a real T5577, and refuse to pretend it happened."""
        out = self.exec(p.pm3_write, timeout=max(self.timeout, 120))
        if not any(m in (out or "").lower() for m in PM3_WROTE):
            tail = " / ".join(l.strip() for l in (out or "").strip().splitlines()[-3:])
            raise DeviceError(
                "pm3: `%s` did not confirm a write. The tag still holds whatever it held before, so "
                "nothing read from it now is about %s. Client said: %s"
                % (p.pm3_write, p.key, tail[:200] or "nothing at all"))
        return out

    def wipe_t55(self) -> tuple[bool, str]:
        """Wipe the tag, then make it prove it. Returns (confirmed, what the client said).

        ⭐ TWO JOBS AT ONCE. It puts the tag into a state that cannot be mistaken for any credential
        — so a later read can only have come from the write under test — and it restores a config
        the other writers can actually work with. The Flipper in particular will refuse to write a
        T5577 left in some configurations, and a wipe from the Proxmark makes it writable again;
        without one, "the Flipper cannot write this protocol" and "the Flipper cannot write this
        TAG" look identical.

        ⚠ THE WIPE'S OWN REPLY IS NOT THE CONFIRMATION — it lists the blocks it sent, not what the
        tag now holds. `detect` is, and the two run in one client invocation because each one costs
        a connect (RULES.md §10).
        """
        out = self.exec("lf t55xx wipe", "lf t55xx detect", timeout=max(self.timeout, 120))
        low = (out or "").lower()
        if not any(m in low for m in T55_PRESENT):
            return False, "no tag answered `lf t55xx detect` after the wipe"
        if any(b in low for b in T55_DEFAULT_BLOCK0 + T55_Q5_BLOCK0):
            return True, "detect reports the default configuration block"
        m = re.search(r"block0\.*\s*([0-9a-f]{8})", low)
        return False, ("the tag answers but its configuration is %s, not the wiped default"
                       % (m.group(1).upper() if m else "unreadable"))

    def disarm(self) -> None:
        """A no-op, and deliberately present.

        ⚠ EVERY CHANNEL ANSWERS `disarm()` whether or not it can emit, because the null sweep calls
        it on everything in the stack and must not have to know which devices those are. The
        Proxmark client exits after each `-c` invocation, so this harness cannot leave it
        simulating; if that ever changes, this is where stopping it belongs.
        """

    def decode_marker(self, p: reg.Protocol) -> str:
        return p.pm3_decode_marker


# ===================================================================== Chameleon Ultra

@dataclass
class Chameleon:
    """A Chameleon, used as an emitter (`emu.cu1`/`emu.cu2`) and as reader `rd.cu`.

    ⛔⛔ FOUR SEPARATE THINGS, AND NOTHING IN THE NOTES SAID SO. A slot emits only when all of them
    are done: the TYPE is set, the CREDENTIAL is written, the LF interface is ENABLED, and the
    device is in emulator MODE. Miss the enable and `hw slot list` says `LF: (disabled)EM410X` —
    type present, interface off, nothing on the air. That cost four rounds of chasing the wrong
    thing, and the tell is `(disabled)` in the listing.

    ⛔ `econfig` WRITES THE CREDENTIAL AND NOT THE TYPE, and the firmware says so with a line
    beginning `WARNING:`. The first version of emugrade.sh filtered for error|usage|invalid, which
    does not match WARNING — the answer was printed on the very first run and thrown away by a grep.
    `_refused()` below matches WARNING for that reason.
    """

    port: str
    name: str = "cu1"
    cli: str = DEFAULT_CU_PY
    slot: int = 8
    timeout: int = 60
    id: str = "rd.cu"
    reported: str = ""
    #: The permanent hardware id `bench setup` recorded for this label. Checked at proof of life,
    #: because a port can be reassigned between sessions and the silicon cannot.
    expect_chipid: str = ""

    @property
    def python(self) -> str:
        """The venv BESIDE cu.py — it holds the chameleon_com imports our interpreter need not have."""
        cand = os.path.join(os.path.dirname(os.path.abspath(self.cli)), ".venv", "bin", "python")
        return cand if os.path.exists(cand) else "python3"

    def exec(self, *cmds: str, timeout: Optional[int] = None, verify: bool = True) -> str:
        """Run commands on this device, proving on the way that it IS this device.

        ⭐⭐ THE IDENTITY CHECK RIDES ALONG WITH THE WORK, AND THAT IS WHY IT CAN BE ON EVERY ACTION.
        `cu.py` runs a list of commands in ONE session with one connect, so prepending `hw chipid`
        costs an extra command on an already-open link, not another process. Checking once at
        startup would leave the rest of the run unguarded against a replug; checking here means a
        swapped cable is caught at the exact action it would have corrupted, and named.

        ⚠ THE CHIP ID LINE IS STRIPPED FROM WHAT IS RETURNED. It must never reach the decode
        matcher: a hex identifier sitting in front of a reader's output is exactly the kind of thing
        a byte-exact search can trip over.
        """
        check = bool(self.expect_chipid) and verify
        argv = [self.python, self.cli, "-p", self.port]
        argv += (["hw chipid"] if check else []) + list(cmds)
        out = _run(argv, timeout or self.timeout)
        if not check:
            return out
        m = CHIPID_RE.search(out or "")
        if m is None:
            raise WrongDevice(
                "%s: %s did not answer `hw chipid`, so there is no proof this is the device the "
                "command was addressed to. Nothing measured through it would mean anything."
                % (self.name, self.port))
        if m.group(1).upper() != self.expect_chipid.upper():
            raise WrongDevice(
                "⛔ %s IS NOT THE DEVICE ON %s. %s is chip %s; this port holds chip %s. A cable has "
                "been moved since the port was resolved. Re-run `bench setup` (or just re-run the "
                "command — ports are re-resolved by chip id at startup)."
                % (self.name, self.port, self.name, self.expect_chipid, m.group(1).upper()))
        return CHIPID_LINE_RE.sub("", out)

    @staticmethod
    def _refused(out: str) -> str:
        m = re.search(r"(?im)^.*\b(error|warning|invalid|unrecognized|usage|traceback)\b.*$", out or "")
        return m.group(0).strip()[:110] if m else ""

    def alive(self) -> tuple[bool, str]:
        try:
            out = self.exec("hw version")
        except WrongDevice as e:
            return False, str(e)
        if self._refused(out) or not out.strip():
            return False, "%s: no usable answer to `hw version` — %s" % (self.name,
                                                                         self._refused(out) or "silence")
        # ⚠ NOTHING EXTRA IS CHECKED HERE. `exec` above already proved this is the right
        # device, and it proves it again on every subsequent action — a single startup check would
        # leave the rest of the run unguarded against a cable being moved mid-session.
        self.reported = _cu_version(out)
        return True, "%s: alive — %s%s" % (
            self.name, self.reported,
            " (chip %s, re-proved on every action)" % self.expect_chipid if self.expect_chipid
            else " — ⚠ no chip id recorded, so nothing checks that commands reach this device "
                 "rather than the other one. Run `bench setup`.")

    def chipid(self) -> Optional[str]:
        """The permanent hardware id, or None if this port will not say.

        ⛔ `verify=False` IS THE BOOTSTRAP AND IS NOT OPTIONAL. You cannot check identity with the
        command that discovers it: verifying would prepend a second `hw chipid` and then strip the
        answer out of the reply, so the probe would always return None and every port would look
        like it was not a Chameleon.
        """
        m = CHIPID_RE.search(self.exec("hw chipid", verify=False) or "")
        return m.group(1).upper() if m else None

    def arm(self, p: reg.Protocol) -> None:
        """Type, credential, LF enable, slot change, emulator mode — all four, in that order."""
        for step, out in (
            ("slot type", self.exec("hw slot type -s %d -t %s" % (self.slot, p.cu_type))),
            ("lf enable", self.exec("hw slot enable -s %d --lf" % self.slot)),
            ("econfig", self.exec(p.emulate_cmd(self.slot))),
        ):
            why = self._refused(out)
            if why:
                raise DeviceError("%s: %s REFUSED for %s — %s" % (self.name, step, p.key, why))
        self.exec("hw slot change -s %d" % self.slot, "hw mode -e")
        time.sleep(1.0)

    def disarm(self) -> None:
        """Reader mode: the device emits nothing. This is what a null sweep is taken against.

        ⛔ AND IT MUST BE UNDONE BEFORE THE NEXT ARM. The first emugrade.sh left the device in
        reader mode after the null check and never switched back, so every arm was measured against
        a device emulating nothing and scored 0 — with a clean null either side that looked like
        confirmation. `arm()` ends with `hw mode -e` for that reason.
        """
        self.exec("hw mode -r")
        time.sleep(0.5)

    def read(self, p: reg.Protocol) -> str:
        raise DeviceError(
            "rd.cu is not wired to a per-protocol decoder in this build. The Chameleon's reader "
            "arms are the thing under test in the owning project; until a read command per protocol "
            "is registered here, plan.py must not emit (*, rd.cu) cells."
        )

    def decode_marker(self, p: reg.Protocol) -> str:
        return p.pm3_decode_marker


# ===================================================================== Flipper Zero

@dataclass
class Flipper:
    """Reader `rd.flip`, emitter `emu.flip`, and the `t55.flip` writer.

    Driven through `flipper.py` rather than a fresh serial implementation, because that script
    already encodes the three lessons this channel costs you: ETX-terminated reads (`rfid read`
    never times out on its own), a non-zero exit when the plugin will not load, and a reboot before
    an arm that would not fit in the largest contiguous heap block.
    """

    script: str = DEFAULT_FLIPPER_PY
    port: str = ""
    attempts: int = 6
    timeout: int = 180
    id: str = "rd.flip"
    #: ⚠ HONESTLY UNKNOWN. `flipper.py` exposes read / emulate / reboot / heap and no version query,
    #: and this harness does not reach past it to the serial port — two readers on one `/dev/cu.*`
    #: is how a session's replies get eaten. Recorded as unknown rather than guessed; a one-line
    #: `version` subcommand in `flipper.py` would fill it in.
    reported: str = "firmware not reported by this channel"

    def _py(self) -> str:
        cand = os.path.join(os.path.dirname(DEFAULT_CU_PY), ".venv", "bin", "python")
        return cand if os.path.exists(cand) else "python3"

    def _exec(self, *args: str) -> tuple[int, str]:
        argv = [self._py(), self.script] + (["--port", self.port] if self.port else []) + list(args)
        try:
            r = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                               timeout=self.timeout, stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            return 3, "[flipper.py TIMED OUT after %ss]" % self.timeout
        except Exception as e:                                    # noqa: BLE001
            return 3, "[flipper.py could not launch: %s]" % e

    def alive(self) -> tuple[bool, str]:
        """⭐ A CLEAN `heap` IS THE ONLY POSITIVE CONTROL THIS RIG HAS. There is no other, because a
        silent reader and a silent emulator produce the same numbers."""
        rc, out = self._exec("heap")
        if rc != 0:
            rc2, _ = self._exec("reboot")
            if rc2 != 0:
                return False, "flipper: heap too fragmented for the rfid plugin and the reboot failed"
            rc, out = self._exec("heap")
        return (rc == 0), ("flipper: alive" if rc == 0
                           else "flipper: the rfid plugin will not load — /ext/apps/RFID/lfrfid.fap "
                                "must match the running firmware's API")

    def read(self, p: reg.Protocol) -> str:
        """Return the NORMALISED decode lines, not the raw log.

        ⭐ NORMALISING HERE IS WHAT KEEPS THE NAME-MATCH RULE (RULES.md §6). `observe()` does a substring match, and
        a substring match against the raw log would hit the usage banner and the "Available
        protocols:" listing — the exact trap that once turned 5 attempts into 10 reported successes.
        What comes back from here is only lines that matched the anchored `^name HEX$` pattern, so
        there is nothing else in the text for a match to land on.
        """
        rc, out = self._exec("read", "--mode", "both", "--attempts", str(self.attempts))
        if rc != 0 or "the Flipper REJECTED" in out:
            raise DeviceError(
                "flipper: the reader is not running — nothing measured against it would mean "
                "anything. A silent reader and a silent emulator produce IDENTICAL numbers.")
        hits = [m.group(0) for line in out.splitlines()
                for m in [FLIP_SUCCESS.match(line.strip())] if m]
        return "\n".join(hits)

    def arm(self, p: reg.Protocol) -> None:
        """`emu.flip` — the Flipper emulating, an independent second opinion on our own emulator."""
        if p.flip_expect is None:
            raise DeviceError("flipper: no known data encoding for %s — `rfid emulate` needs the "
                              "Flipper's own hex. Run `bench learn` first." % p.key)
        rc, out = self._exec("emulate", p.flip_key, p.flip_expect, "--seconds", "30")
        if rc != 0:
            raise DeviceError("flipper: refused to emulate %s — %s" % (p.key, out.strip()[-160:]))

    def write_t55(self, p: reg.Protocol) -> str:
        """`t55.flip` — `rfid write <key_type> <key_data>`.

        ⛔ FOUR OF THE SIXTEEN ARE KNOWN NOT TO WRITE (see the gap register): keri, nexwatch, idteck and
        gproxii go onto a T5577 from the pm3 and not from the Flipper. That is a REGISTERED GAP, so
        it is refused here by name rather than discovered again as a puzzling row.
        """
        if not p.flip_write:
            raise DeviceError("flipper: cannot write %s to a T5577 — registered gap, the gap register"
                              % p.key)
        if p.flip_expect is None:
            raise DeviceError("flipper: no known data encoding for %s. Run `bench learn` first."
                              % p.key)
        rc, out = self._exec("write", p.flip_key, p.flip_expect)
        if rc != 0:
            raise DeviceError("flipper: write refused for %s — %s" % (p.key, out.strip()[-160:]))
        return out

    def disarm(self) -> None:
        pass          # `rfid emulate` stops when flipper.py closes the port

    def decode_marker(self, p: reg.Protocol) -> str:
        return FLIP_DECODE_MARKER


# ===================================================================== scripted stand-in

@dataclass
class Air:
    """Shared bench state for the scripted devices: who is armed, and who is on the pad.

    ⚠ THIS IS NOT AN RF MODEL AND MUST NOT GROW INTO ONE. It knows exactly two facts — an emitter
    that is armed emits what it was armed with, and a reader hears only emitters on its own pad —
    which is the minimum needed to exercise the identity check, the null sweeps and the licence flow
    off the bench. Anything it cannot express (range, modulation, a decoder gap) belongs in a
    `Scripted.answers` entry written by the test that cares, so that every departure from "it just
    works" is stated explicitly rather than modelled vaguely.

    ⭐ `in_stack` IS WHY THE IDENTITY CHECK IS TESTABLE. The check arms every Chameleon on purpose,
    so a decode names a device rather than merely proving something is there; without a notion of
    which ones are physically stacked, a fake bench hears them all and the check can only ever
    report a stray. `None` means "everything armed is audible", which is the contamination case.
    """

    armed: dict = field(default_factory=dict)         # device id -> (protocol key, expected text)
    in_stack: set | None = None                       # device ids sharing the reader's stack


@dataclass
class Scripted:
    """A device that replays canned text. `--dry-run` and every test run on this.

    Lookup order for a read: an explicit `answers[(protocol, armed_source)]` entry first, so a test
    can script silence or a wrong decode; then the shared `Air`; then nothing.
    """

    id: str
    role: str                                    # pm3 | flipper | cu1 | cu2
    answers: dict = field(default_factory=dict)  # (protocol_key, armed_source) -> text
    air: Air = field(default_factory=Air)
    armed: Optional[str] = None
    alive_ok: bool = True
    reported: str = "scripted, no firmware"
    log: list = field(default_factory=list)

    def alive(self) -> tuple[bool, str]:
        return self.alive_ok, "%s: %s" % (self.id, "alive" if self.alive_ok else "DEAD")

    def exec(self, *cmds: str, timeout=None) -> str:
        self.log.append(("exec",) + cmds)
        return self.answers.get(("exec", cmds[0]), "")

    def audible(self) -> list:
        """(device, protocol, expected) for every armed emitter this reader can hear."""
        return [(d, k, v) for d, (k, v) in sorted(self.air.armed.items())
                if d != self.id and (self.air.in_stack is None or d in self.air.in_stack)]

    def read(self, p: reg.Protocol) -> str:
        """⛔ ONLY AN EMITTER ACTUALLY HOLDING THIS PROTOCOL CAN ANSWER FOR IT. The scripted answers
        are keyed by (protocol, device) and it is tempting to look them up directly — but then a
        reader is told what a device WOULD say if it were emitting that protocol, regardless of what
        it is emitting now. A test for "the write did nothing, so the tag still holds the parking
        credential" then passes with flying colours, because the fake answers for the protocol that
        was never written. The scripted bench must be able to be wrong in the same ways the real one
        is, or the tests are about nothing.
        """
        heard = self.audible()
        holding = [(d, k, v) for d, k, v in heard if k == p.key]
        self.log.append(("read", p.key, holding[0][0] if holding else None))
        if not holding:
            return ""
        for dev, _, _ in holding:
            if (p.key, dev) in self.answers:
                return self.answers[(p.key, dev)]
        return "\n".join("[+] %s scripted read: %s" % (p.key, exp) for _, _, exp in holding if exp)

    def write_t55(self, p: reg.Protocol) -> str:
        self.log.append(("write", p.key))
        self.air.armed[T5577] = (p.key, p.expect)      # the tag now holds this credential
        return "ok"

    #: Set False to model a wipe that returns cheerfully and changes nothing.
    wipe_works: bool = True

    def wipe_t55(self) -> tuple[bool, str]:
        """⚠ ACTUALLY CLEARS THE FAKE TAG. A wipe that only logged itself would let a test for "the
        write did nothing, so the tag is still empty" pass against a tag that was never emptied."""
        self.log.append(("wipe",))
        if not self.wipe_works:
            return False, "the tag answers but its configuration is 00148040, not the wiped default"
        self.air.armed.pop(T5577, None)
        return True, "detect reports the default configuration block"

    def arm(self, p: reg.Protocol) -> None:
        self.log.append(("arm", p.key))
        self.armed = p.key
        self.air.armed[self.id] = (p.key, p.expect)

    def disarm(self) -> None:
        self.log.append(("disarm",))
        self.armed = None
        self.air.armed.pop(self.id, None)

    def decode_marker(self, p: reg.Protocol) -> str:
        return FLIP_DECODE_MARKER if self.role == "flipper" else p.pm3_decode_marker


def _pm3_version(out: str) -> str:
    os_m, cl_m = PM3_OS_RE.search(out or ""), PM3_CLIENT_RE.search(out or "")
    if not (os_m or cl_m):
        return "firmware version not reported"
    bits = []
    if os_m:
        bits.append("os %s" % os_m.group(1))
    if cl_m:
        bits.append("client %s" % cl_m.group(1))
    return ", ".join(bits)


def _cu_version(out: str) -> str:
    m = CU_VERSION_RE.search(out or "")
    return ("Chameleon %s %s (%s)" % (m.group(1), m.group(2), m.group(3)) if m
            else "firmware version not reported")


def scripted_bench(answers: dict | None = None, *, flipper: bool = True, cu2: bool = True):
    """A complete scripted bench sharing one `Air`, plus the operator who performs the moves.

    ⭐ THIS IS WHAT MAKES `--dry-run` A REHEARSAL RATHER THAN A STUB. With separate `Air`s and no
    operator every reader is deaf, every pad is empty, and the run aborts at the first identity
    check — which tests nothing except that the abort works. Sharing the air and moving the devices
    when the cue says to means a dry run walks the real move script, takes the real null sweeps, and
    exercises the real licence flow, with the radio replaced by a dictionary.

    Returns (devices_kwargs, air). The caller assembles `runner.Devices` because this module must
    not import the runner.
    """
    air = Air()
    kw = {
        "pm3": Scripted(id="pm3", role="pm3", answers=answers or {}, air=air),
        "flipper": Scripted(id="flipper", role="flipper", answers=answers or {}, air=air)
                   if flipper else None,
        "cu1": Scripted(id="cu1", role="cu1", air=air),
        "cu2": Scripted(id="cu2", role="cu2", air=air) if cu2 else None,
    }
    return kw, air


def obedient_operator(air: Air):
    """An operator who builds every stack exactly as cued. The baseline a dry run assumes."""
    def do(station):
        air.in_stack = set(station.stack)
    return do
