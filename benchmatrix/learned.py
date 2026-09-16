"""Bench-learned expectations — what a reader actually prints for a known-good credential.

⭐ WHY LEARNING IS ALLOWED AT ALL. Fourteen of the eighteen tier-0 protocols have no known Flipper
hex (registry.py, class 3), and deriving it from each protocol's encoder is guessing at an answer
the bench can be asked for directly: write the credential to a T5577 with the Proxmark, read the tag
back, and record what the reader says. That is a measurement, not an assumption.

⭐⭐ AND IT IS NOT A FLIPPER-ONLY PROBLEM, WHICH IS WHAT THIS FILE USED TO ASSUME. `rd.flip` was
hardcoded here and in `cmd_learn`, so the one tool for turning "nobody has observed this" into a
recorded measurement covered one of four readers. The other three were served by editing the
registry by hand — which is exactly how `fdxb` came to carry a decode marker the client never prints
and an expectation taken from the wrong artefact, each hiding the other for as long as both existed.
A hand-edited constant has no session, no evidence and no provenance; a learned one has all three,
and `check_independence` can refuse it.

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
import re
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


#: reader -> the registry field its expectation lives in.
#: ⚠ BOTH CHAMELEONS SHARE `cu_expect`, AND THAT IS THE REGISTRY'S MODEL, NOT AN OVERSIGHT: an
#: expectation is a claim about how a FIRMWARE renders a credential, not about a device (RULES.md
#: §11). So a value learned on `rd.cu1` does license the `rd.cu2` column — sound while both run the
#: same build, which is a fact the grid publishes on every run, and wrong in the same way the shared
#: field was already wrong if they ever diverge. The note says which reader it was learned on so
#: that is visible rather than assumed.
FIELD_FOR = {"rd.flip": "flip_expect", "rd.cu1": "cu_expect", "rd.cu2": "cu_expect",
             "rd.pm3": "expect"}


def apply(protocols: list[reg.Protocol], records: dict[tuple[str, str], Learned],
          session: str) -> tuple[list[reg.Protocol], list[str]]:
    """Fold learned expectations into the registry entries for this run, for every reader.

    ⛔ THIS WAS `rd.flip` ONLY, hardcoded, so three of the four readers had no path from "measured
    on the bench" into the registry except a human editing a constant. That is how `fdxb` acquired a
    decode marker the client never prints and an expectation taken from the wrong artefact.

    ⚠ A REGISTERED VALUE ALWAYS WINS. Learning fills a hole; it never overrides something the
    registry already asserts, because then a stale record could quietly displace a corrected entry
    and the grid would not say so. Use `--relearn` and edit the registry to change a known value.

    Returns the protocols and the notes describing what was folded in or refused — both go into the
    published grid, because an expectation's provenance is part of the result.
    """
    out, notes = [], []
    for p in protocols:
        fields, applied = {}, []
        for reader, field in sorted(FIELD_FOR.items()):
            rec = records.get((p.key, reader))
            if rec is None or p.expect_for(reader) is not None or field in fields:
                continue
            try:
                check_independence(rec, session)
            except LearningRefused as e:
                notes.append("⛔ %s" % e)
                continue
            fields[field] = rec.value
            applied.append("%s expects %r (session %s, from %s)"
                           % (reader, rec.value, rec.session, rec.source))
        for a in applied:
            notes.append("learned: %s %s" % (p.key, a))
        out.append(reg.Protocol(**{**p.__dict__, **fields}) if fields else p)
    return out, notes


def observed_value(text: str, flip_key: str) -> str | None:
    """Pull the hex out of an anchored `<name> <HEX>` line whose name is the one we asked for.

    ⚠ FLIPPER-SPECIFIC BY DESIGN — its success line has a shape worth anchoring to, and anchoring is
    what RULES.md §6 requires of it. The other readers have no such line; see `candidates`.
    """
    from .devices import FLIP_SUCCESS
    for line in (text or "").splitlines():
        m = FLIP_SUCCESS.match(line.strip())
        if m and m.group(1).strip().lower() == flip_key.lower():
            return m.group(2)
    return None


#: `[+] Animal ID......... 999-000000001337` and `[+] Raw (128 bits): 00339a08...` — a label, a run
#: of dots or a colon, then the value. Both the Proxmark and the Chameleon print in this shape.
_LABELLED = re.compile(r"^(?:\[[+=!]\]\s*)?.{2,40}?(?:\.{2,}|:)\s*(\S.*?)\s*$")
#: `[+] EM 410x ID 2244668800` — no separator at all, the value is simply last.
_TRAILING = re.compile(r"^(?:\[[+=!]\]\s*)?.*?(\S+)\s*$")
_PREFIX = re.compile(r"^\[[+=!]\]\s*")


#: Lines that carry no value: a flag rendered as a word, an empty field, a heading.
_EMPTY = ("none", "n/a", "no", "yes", "true", "false", "unknown", "0", "")

#: What a credential is mostly made of, once a client has finished formatting it.
_VALUE_CHARS = set("0123456789abcdefABCDEF -")


def _valueish(tok: str) -> float:
    return sum(c in _VALUE_CHARS for c in tok) / len(tok) if tok else 0.0


def value_lines(text: str) -> list[str]:
    """The lines a reader printed that might carry the credential.

    ⛔ NOT `outcomes._summarise`, WHICH LOOKS WRONG FOR THIS AND IS. That keeps lines matching the
    expectation or the decode marker — it is for showing evidence once you already know what you
    were looking for. Here the expectation is the unknown, so anchoring on it drops precisely the
    line being learned: asked to learn `fdxb` on `rd.pm3`, it returned the banner and the raw frame
    and threw away `Animal ID......... 999-000000001337`, which is the answer.
    """
    from .outcomes import _NOISE, _strip_ansi
    out = []
    for line in _strip_ansi(text or "").splitlines():
        t = line.strip()
        if not t or any(n in t.lower() for n in _NOISE):
            continue
        if t.lower().lstrip("[+=!] ").startswith(("pm3 -->", "usb]")):
            continue
        out.append(t)
    return out


def candidates(summary, text: str) -> list[str]:
    """Tokens from what the device printed that could serve as the expectation, best first.

    ⛔⛔ THIS PROPOSES; IT DOES NOT DECIDE. Every automatic extractor that has been trusted to pick
    on its own has eventually picked the wrong thing and made it permanent — `fdxb`'s expectation
    was the T5577 block image, which is a real value printed by a real device and simply not the one
    the Proxmark compares against. So the operator confirms, and what gets recorded is a choice with
    a transcript attached rather than a regex's opinion.

    ⚠ THE WHOLE LINE IS OFFERED, AND IT IS OFTEN THE RIGHT ANSWER. Matching is a case-insensitive
    substring test, so `Animal ID......... 999-000000001337` is a STRICTER expectation than the bare
    id — it pins the field the value came out of, and cannot be satisfied by the same digits turning
    up in a raw frame or a usage banner. That is RULES.md §6 applied to a reader that has no
    anchored success line of its own.
    """
    values: list[str] = []
    lines: list[str] = []

    def add(into: list, tok: str) -> None:
        tok = (tok or "").strip()
        # ⚠ MUST BE FINDABLE IN THE OUTPUT, or the expectation can never match. A proposal that
        # fails its own test is a bug offered to the operator as a choice.
        if len(tok) >= 3 and tok.lower() in (text or "").lower() and tok.lower() not in _EMPTY \
                and tok not in into and tok not in values and tok not in lines:
            into.append(tok)

    for line in (summary or value_lines(text)):
        bare = _PREFIX.sub("", line).strip()
        m = _LABELLED.match(line)
        if m:
            add(values, m.group(1))
        elif _TRAILING.match(line):
            add(values, _TRAILING.match(line).group(1))
        add(lines, bare)
    # ⭐ THE BARE VALUES FIRST, THEN THE WHOLE LINES. Either can be right — a labelled line is the
    # stricter expectation — so both are offered, in the order they are usually wanted.
    # ⚠ A CREDENTIAL HAS A DIGIT IN IT, AND IS MOSTLY MADE OF ONE. Without the first test the top
    # proposal for fdxb was "Animal" — the last word of the banner, a real substring of the output
    # and meaningless. Without the second it was "11784/5)", a fragment of the standard's number.
    #
    # ⭐ AND THEN THE LONGEST, BECAUSE A SHORT EXPECTATION IS A WEAK ONE. Matching is a substring
    # test, so `4567` — a Chameleon's rendering of a HID card number — is satisfied by those four
    # digits appearing anywhere in the output, including inside a raw frame or a timestamp. It was
    # the top proposal for hidprox until this line existed, over `2006ec0c86` from the same read.
    #
    # ⇒ These only ORDER the list; the operator still chooses, and can type something else. The
    # asymmetry is why the ordering leans strict: an expectation that is too tight fails loudly and
    # visibly, and one that is too loose passes wrongly and says nothing.
    values.sort(key=lambda t: (not any(c.isdigit() for c in t), -_valueish(t), -len(t)))
    return (values + lines)[:10]
