"""Bench-learned expectations — what a reader actually prints for a known-good credential.

⭐ WHY LEARNING IS ALLOWED AT ALL. Ten of the sixteen tier-0 protocols have no known Flipper hex
(registry.py, class 3), and deriving it from each protocol's encoder is guessing at an answer the
bench can be asked for directly: write the credential to a T5577 with the Proxmark, put the tag on
the Flipper, and record what it says. That is a measurement, not an assumption.

⛔⛔ THE SELF-LICENSING RULE (RULES.md §8), WHICH IS THE WHOLE REASON THIS IS A SEPARATE FILE. If the expectation
is learned from the same read that is supposed to license the reader, the calibration row CANNOT
FAIL — it is being compared against itself. That is not a weaker control, it is a control that has
been quietly inverted into a tautology, and it would be invisible in the grid: every licence green,
every licence worthless. It is the calibration rule defeated with one more step of indirection.

⇒ A LEARNED EXPECTATION CANNOT LICENSE ANYTHING IN THE SESSION THAT LEARNED IT. The session id is
stamped into the record and `check_independence()` refuses the pair. Learn in one sitting, grade in
the next; the cost is one extra session and the benefit is that the control means something.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from . import registry as reg

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "learned.json")


@dataclass(frozen=True)
class Learned:
    protocol: str
    reader: str
    value: str          # the decoded hex the reader printed
    session: str        # ⛔ the session that learned it — see check_independence
    source: str         # what was on the pad (must be a real tag)
    when: str
    evidence: str


class LearningRefused(Exception):
    pass


def load(path: str = DEFAULT_PATH) -> dict[tuple[str, str], Learned]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return {(r["protocol"], r["reader"]): Learned(**r) for r in raw.get("learned", [])}


def save(records: dict[tuple[str, str], Learned], path: str = DEFAULT_PATH) -> None:
    payload = {"note": ("Bench-learned reader expectations. A record CANNOT license a calibration "
                        "row in the session that learned it — see learned.py."),
               "learned": [asdict(r) for r in sorted(records.values(),
                                                     key=lambda r: (r.protocol, r.reader))]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def check_independence(rec: Learned, session: str) -> None:
    """⛔ THE GUARD. Refuse to use an expectation learned in the session now doing the grading."""
    if rec.session == session:
        raise LearningRefused(
            "(%s, %s): the expectation %r was learned in THIS session (%s). Using it would compare "
            "the calibration row against itself, which makes the control unfailable and therefore "
            "meaningless. Run the matrix in a new session."
            % (rec.protocol, rec.reader, rec.value, session))


def apply(protocols: list[reg.Protocol], records: dict[tuple[str, str], Learned],
          session: str) -> tuple[list[reg.Protocol], list[str]]:
    """Fold learned Flipper expectations into the registry entries for this run.

    Returns the protocols and the notes describing what was folded in or refused — both go into the
    published grid, because an expectation's provenance is part of the result.
    """
    out, notes = [], []
    for p in protocols:
        rec = records.get((p.key, "rd.flip"))
        if rec is None or p.flip_expect is not None:
            out.append(p)
            continue
        try:
            check_independence(rec, session)
        except LearningRefused as e:
            notes.append("⛔ %s" % e)
            out.append(p)
            continue
        notes.append("learned: %s rd.flip expects %r (session %s, from %s)"
                     % (p.key, rec.value, rec.session, rec.source))
        out.append(reg.Protocol(**{**p.__dict__, "flip_expect": rec.value}))
    return out, notes


def observed_value(text: str, flip_key: str) -> str | None:
    """Pull the hex out of an anchored `<name> <HEX>` line whose name is the one we asked for."""
    from .devices import FLIP_SUCCESS
    for line in (text or "").splitlines():
        m = FLIP_SUCCESS.match(line.strip())
        if m and m.group(1).strip().lower() == flip_key.lower():
            return m.group(2)
    return None
