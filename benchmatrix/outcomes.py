"""The four outcomes, and the calibration licence that is required to produce three of them.

⭐⭐ THIS MODULE IS THE WHOLE POINT OF THE PROJECT. C473 published a seven-protocol positive
conclusion built on uncalibrated silence, and the operator refuted it from their own bench in
minutes. The defect was not the conclusion, it was that *nothing in the process refused to
produce a verdict when the controls were missing* — `pm3grade.sh` will happily print a full grid
with no calibration row anywhere in it.

⛔ SO THE LICENCE IS A TYPE, NOT A FLAG. `grade()` cannot be called without a `Calibration`, and a
`Calibration` cannot be constructed except by `Calibration.from_row()`, which refuses anything but
an `EXACT` real-tag observation. There is deliberately no `--no-calibration`, no `force=`, and no
`Calibration()` bare constructor: an option to skip the control is the same defect with a nicer
name on it.

⚠ WRONG IS NOT SILENCE (DESIGN.md §1). A reader that decodes *something other than what was armed*
has told us a great deal; a reader that says nothing has told us nothing. Merging them is how a
decoder bug and a dead instrument end up in the same cell. Distinguishing them requires a
per-(protocol, reader) decode marker, which is why `registry.py` treats a missing marker as a
registry error rather than defaulting to SILENT.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Optional


class Outcome(enum.Enum):
    """Exactly four. No free text, and no fifth value added later without changing DESIGN.md §1.

    A cell that M52 forbids is not a fifth outcome — it is never planned at all (see plan.py), so
    it has no cell to hold an outcome in.
    """

    EXACT = "EXACT"        # decoded, byte-identical to what was armed/written
    WRONG = "WRONG"        # decoded, but not what was armed — a real result, never merged with silence
    SILENT = "SILENT"      # no decode at all
    UNGRADED = "UNGRADED"  # the calibration row for this (P, READER) is missing or failed

    def __str__(self) -> str:
        return self.value


#: Rendering for the grid. UNGRADED deliberately does not get a tick or a cross — it is not a
#: weaker verdict, it is the absence of one.
GLYPH = {
    Outcome.EXACT: "✅",
    Outcome.WRONG: "❌",
    Outcome.SILENT: "·",
    Outcome.UNGRADED: "▒",
}


@dataclass(frozen=True)
class Observation:
    """What a reader actually printed, with no verdict attached.

    ⚠ `matched` and `decoded` are BOTH measured from the text, by two different patterns, and
    neither is inferred from the other. `matched` is the byte-exact expectation token (the
    pm3grade.sh discipline, kept). `decoded` is the protocol's own "I demodulated something" line
    taken from the reader's source — see registry.py `decode_marker`.
    """

    protocol: str
    source: str
    reader: str
    text: str
    matched: bool
    decoded: bool
    session: str = ""
    pad: str = ""

    @property
    def outcome_if_licensed(self) -> Outcome:
        """The outcome this observation would carry *if* a licence exists. Never call directly —
        `grade()` is the only supported route, because this property cannot see the licence."""
        if self.matched:
            return Outcome.EXACT
        return Outcome.WRONG if self.decoded else Outcome.SILENT


class CalibrationRefused(Exception):
    """Raised when something tries to build a licence out of a row that did not pass."""


@dataclass(frozen=True)
class Calibration:
    """A licence to grade one (protocol, reader) pair, in one session, on one pad.

    ⛔ DESIGN.md §2.2: the licensing row must have been executed *in the same session, on the same
    pad, with the same antenna position* as the emulated rows it licenses. Those three are carried
    here and checked in `licenses()` — a licence from yesterday's session, or from the other pad,
    licenses nothing. That is not pedantry: the whole failure mode is a control that was true
    somewhere else.
    """

    protocol: str
    reader: str
    session: str
    pad: str
    source: str          # the real-tag source that earned the licence (t55.pm3, or oem)
    evidence: str        # the reader text, kept so the grid can show what the control saw

    # ⛔ NO PUBLIC CONSTRUCTOR PATH THAT SKIPS THE CHECK. `from_row` is the only way in.
    _vouched: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self._vouched:
            raise CalibrationRefused(
                "Calibration() was constructed directly. Use Calibration.from_row(observation) — "
                "a licence must be earned by an EXACT real-tag row, not asserted."
            )

    @classmethod
    def from_row(cls, obs: Observation, real_sources: frozenset[str]) -> "Calibration":
        """Build a licence from a calibration row, or refuse with the reason.

        ⚠ THE REFUSAL MESSAGE IS THE FINDING. DESIGN.md §2.3: when the calibration row does not
        pass, "reader R cannot judge P on this bench" is itself a result, and *the only finding
        that block of the run is allowed to produce*. But a row that came back WRONG says something
        different — the write did not put what we expected on the tag — so the two are separated
        here rather than both reported as a deaf reader.
        """
        if obs.source not in real_sources:
            raise CalibrationRefused(
                "(%s, %s): source %s is not a real-tag source %s — an emulation cannot license "
                "itself. DESIGN.md §2.1 requires t55.pm3 (or oem where a T5577 cannot hold P)."
                % (obs.protocol, obs.reader, obs.source, sorted(real_sources))
            )
        if obs.outcome_if_licensed is Outcome.WRONG:
            raise CalibrationRefused(
                "(%s, %s): the calibration row DECODED, but not what was written. This is a "
                "REGISTRY/WRITE fault, not a deaf reader — `pm3.write` and `expect` disagree. Fix "
                "the registry entry before reading anything into the emulated rows."
                % (obs.protocol, obs.reader)
            )
        if obs.outcome_if_licensed is Outcome.SILENT:
            raise CalibrationRefused(
                "(%s, %s): reader %s cannot judge %s on this bench — it read NOTHING from a real "
                "tag written by the Proxmark, on this pad, in this session. Every emulated row for "
                "this pair is UNGRADED, and this sentence is the only finding this block produces."
                % (obs.protocol, obs.reader, obs.reader, obs.protocol)
            )
        return cls(protocol=obs.protocol, reader=obs.reader, session=obs.session, pad=obs.pad,
                   source=obs.source, evidence=obs.text, _vouched=True)

    def licenses(self, obs: Observation) -> bool:
        """Does this licence cover that observation? All four of protocol, reader, session, pad."""
        return (self.protocol == obs.protocol and self.reader == obs.reader
                and self.session == obs.session and self.pad == obs.pad)


@dataclass(frozen=True)
class Cell:
    """One graded (source, reader) cell for one protocol, plus why it reads the way it does."""

    protocol: str
    source: str
    reader: str
    outcome: Outcome
    observation: Optional[Observation]
    note: str = ""

    @property
    def glyph(self) -> str:
        return GLYPH[self.outcome]


def grade(obs: Observation, licence: Optional[Calibration], note: str = "") -> Cell:
    """The ONLY route to a Cell. No licence ⇒ UNGRADED, regardless of what the reader said.

    ⛔⛔ A CELL THAT WOULD READ `EXACT` STILL READS `UNGRADED` WITHOUT A LICENCE. It is tempting to
    let a byte-exact hit through — surely a correct decode proves the reader was listening? It does
    for that one cell and for nothing else, and the moment the exception exists the grid is back to
    mixing licensed and unlicensed rows with no way to tell them apart. A run that produced
    byte-exact reads with no control is a run that forgot its control; say so.
    """
    if licence is None or not licence.licenses(obs):
        why = note or ("no calibration row for (%s, %s) in this session/pad"
                       % (obs.protocol, obs.reader))
        return Cell(obs.protocol, obs.source, obs.reader, Outcome.UNGRADED, obs, why)
    return Cell(obs.protocol, obs.source, obs.reader, obs.outcome_if_licensed, obs, note)


def ungraded(protocol: str, source: str, reader: str, note: str) -> Cell:
    """A cell that was planned but never observed — the calibration failed, so it was not run."""
    return Cell(protocol, source, reader, Outcome.UNGRADED, None, note)


# ------------------------------------------------------------------ text matching

def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text or "")


def observe(protocol: str, source: str, reader: str, text: str, expect: str,
            decode_marker: str, session: str = "", pad: str = "") -> Observation:
    """Turn raw reader output into an Observation.

    ⚠ ANSI IS STRIPPED FIRST. pm3 wraps decoded values in colour codes (`_GREEN_(...)`), so a
    naive substring search for `123` against `\\x1b[32m123\\x1b[0m` still works but one for
    `FC: 123  CN: 4567` does not — the codes land in the middle. pm3grade.sh gets away with it only
    because `grep -F` is run against a terminal-less client. Do not rely on that here.

    ⚠ `matched` is case-insensitive because half the registry's expectations are hex the pm3 prints
    in the other case (`EXPECT[viking]="1A337195"` against a client that prints lowercase). That is
    inherited from pm3grade.sh's `grep -qiF` and is deliberate: hex case is not a finding.
    """
    clean = _strip_ansi(text)
    matched = expect.lower() in clean.lower()
    decoded = bool(re.search(decode_marker, clean, re.IGNORECASE | re.MULTILINE))
    # ⛔ A BYTE-EXACT HIT IMPLIES A DECODE HAPPENED. If the marker missed while the expectation hit,
    # the marker is wrong, not the read — never let that combination produce `decoded=False`, which
    # would be an impossible Observation (matched but nothing demodulated).
    return Observation(protocol=protocol, source=source, reader=reader, text=clean,
                       matched=matched, decoded=decoded or matched, session=session, pad=pad)
