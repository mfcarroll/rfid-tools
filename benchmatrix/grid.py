"""The published grid, the exclusion list, and the cross-firmware gap register (DESIGN.md §4).

⛔⛔ THE GRID NEVER AGGREGATES ACROSS PROTOCOLS TO LICENSE A CLAIM ABOUT ONE (DESIGN.md §2,
corollary). "Reader A missed X, reader B missed Y, so each is just a decoder gap" is the fallacy
that cost C474. Every statement this module makes is scoped to one (protocol, reader) pair. The
per-reader tallies that do get printed are labelled as TALLIES and carry the sentence that says so,
because a number in a summary row is read as evidence unless it is explicitly not.

⛔ AN UNGRADED CELL IS NOT A GAP. The gap register records "this firmware is wrong about this
protocol" with the capture that proves it, and the only cells entitled to appear there are ones a
passing calibration licensed. An UNGRADED row goes in the OPEN QUESTIONS list instead — it is work
still to do, not a finding.
"""

from __future__ import annotations

import json
from collections import OrderedDict

from . import registry as reg
from .outcomes import GLYPH, Cell, Outcome
from .plan import Exclusion
from .topology import READERS

SOURCE_ORDER = ("t55.pm3", "oem", "t55.flip", "emu.flip", "emu.cu1", "emu.cu2")
READER_ORDER = ("rd.pm3", "rd.flip", "rd.cu")


def _by_cell(cells: list[Cell]) -> dict:
    return {(c.protocol, c.source, c.reader): c for c in cells}


def render(result, protocols: list[reg.Protocol]) -> str:
    """The terminal/markdown grid: one table per reader, protocols down, sources across."""
    cells = _by_cell(result.cells)
    sources = [s for s in SOURCE_ORDER
               if any(c.source == s for c in result.cells)]
    readers = [r for r in READER_ORDER if any(c.reader == r for c in result.cells)]
    lines: list[str] = []
    w = max((len(p.key) for p in protocols), default=8)

    lines.append("# Bench matrix — run %s" % result.session)
    lines.append("")
    if result.provenance != "bench":
        lines.append("> ⛔ **%s — THIS IS NOT A RESULT.** Every read below was answered from a "
                     "dictionary, not a radio. The grid says the control logic works and says "
                     "nothing whatever about any protocol. Do not cite a cell from it."
                     % result.provenance.upper())
        lines.append("")
    lines.append("started %s  ·  finished %s  ·  provenance `%s`"
                 % (result.started, result.finished or "—", result.provenance))
    if result.aborted:
        lines.append("")
        lines.append("⛔ **RUN ABORTED** — %s" % result.aborted)
        lines.append("")
        lines.append("No grid is published from an aborted run. The rows below were measured before "
                     "the abort and are kept only so the point of failure is visible.")
    lines.append("")
    lines.append("legend  " + "   ".join("%s %s" % (GLYPH[o], o.value) for o in Outcome))
    lines.append("")

    for rdr in readers:
        lines.append("## reader `%s` — %s" % (rdr, READERS[rdr][1]))
        lines.append("")
        hdr = "| %-*s | %s |" % (w, "protocol", " | ".join("%-8s" % s for s in sources))
        lines.append(hdr)
        lines.append("|" + "|".join(["-" * (w + 2)] + ["-" * 10] * len(sources)) + "|")
        for p in protocols:
            row = []
            for s in sources:
                c = cells.get((p.key, s, rdr))
                row.append("%-8s" % ("" if c is None else "%s %s" % (c.glyph, _short(c.outcome))))
            lines.append("| %-*s | %s |" % (w, p.key, " | ".join(row)))
        lines.append("")
        lines.extend(_calibration_notes(result, rdr))
        lines.append("")
    lines.extend(_tallies(result, readers))
    lines.extend(_exclusions(result.plan.exclusions))
    lines.extend(_voids(result))
    lines.extend(gap_register(result, protocols))
    lines.extend(_open_questions(result))
    return "\n".join(lines)


def _short(o: Outcome) -> str:
    return {"EXACT": "exact", "WRONG": "wrong", "SILENT": "silent", "UNGRADED": "ungrd"}[o.value]


def _calibration_notes(result, reader: str) -> list[str]:
    out = ["**calibration** — the rows that license this column:"]
    any_row = False
    for (p, r), lic in sorted(result.licences.items()):
        if r != reader:
            continue
        any_row = True
        out.append("- `%s` ✓ licensed by a byte-exact `%s` row on pad `%s`" % (p, lic.source, lic.pad))
    for (p, r), why in sorted(result.refusals.items()):
        if r != reader:
            continue
        any_row = True
        out.append("- `%s` ⛔ **no licence** — %s" % (p, why))
    if not any_row:
        out.append("- (none — nothing in this column can be graded)")
    return out


def _tallies(result, readers: list[str]) -> list[str]:
    """⚠ TALLIES, NOT EVIDENCE. Printed because a run needs a shape at a glance; labelled because a
    number in a summary row is read as a finding unless something says it is not."""
    out = ["## tallies", "",
           "⚠ These count cells. They are **not** evidence about any single protocol: a reader's "
           "total says nothing about whether it can judge protocol P, and combining protocols to "
           "license a claim about one of them is the C474 fallacy. Read the per-(protocol, reader) "
           "rows above for that.", ""]
    for rdr in readers:
        mine = [c for c in result.cells if c.reader == rdr]
        counts = OrderedDict((o, sum(1 for c in mine if c.outcome is o)) for o in Outcome)
        out.append("- `%s`: %s" % (rdr, "  ".join("%s %d" % (o.value, n) for o, n in counts.items())))
    out.append("")
    return out


def _exclusions(exclusions: list[Exclusion]) -> list[str]:
    if not exclusions:
        return []
    out = ["## refused at plan time", "",
           "Not tested, and not a failure. Each of these was removed from the plan before any bench "
           "time was spent on it, with the rule that removed it.", ""]
    by_rule: dict[str, list[Exclusion]] = {}
    for e in exclusions:
        by_rule.setdefault(e.rule, []).append(e)
    for rule in sorted(by_rule):
        group = by_rule[rule]
        out.append("**%s** — %d cell%s" % (rule, len(group), "" if len(group) == 1 else "s"))
        out.append("")
        out.append("> %s" % group[0].why)
        out.append("")
        pairs = sorted({"%s (%s → %s)" % (e.protocol, e.source, e.reader) for e in group})
        out.append("  " + "; ".join(pairs[:12]) + (" …" if len(pairs) > 12 else ""))
        out.append("")
    return out


def _voids(result) -> list[str]:
    voids = result.void_blocks
    if not voids:
        return []
    out = ["## void blocks", ""]
    for b in voids:
        out.append("- **%s** — %s" % (b.block.topology.name, b.void_why))
    out.append("")
    return out


def gap_register(result, protocols: list[reg.Protocol]) -> list[str]:
    """Cross-firmware gaps, as first-class rows rather than asides (DESIGN.md §4).

    ⭐ THIS IS THE DELIVERABLE THAT MAKES THE PROJECT WORTH RUNNING AGAINST OTHER FIRMWARES. An
    upstream maintainer can run the matrix themselves, and a gap row with the capture that proves it
    is the strongest form a bug report takes.

    ⛔ ONLY LICENSED CELLS APPEAR HERE. A gap is a claim about a firmware; an UNGRADED cell is a
    claim about nothing. The known gaps carried from DESIGN.md §4 are listed with their provenance
    so that a row this run produced is never confused with one taken on trust.
    """
    known = [
        ("Flipper", "cannot **write** keri, nexwatch, idteck, gproxii to a T5577 that the pm3 "
                    "writes fine", "operator bench, 2026-09"),
        ("Flipper", "can emulate Indala224 but cannot write it", "operator bench"),
        ("Proxmark", "does not decode the Flipper's Indala224 emulation", "operator bench"),
        ("Proxmark", "no dedicated Electra or InstaFob command", "`cmdlf.c` `CommandTable[]`"),
        ("ChameleonUltra", "10 of the Flipper's 26 protocols unimplemented", "`SCOPE.md` §B"),
        ("ChameleonUltra", "FSK2a mark is a fixed 32 µs on **both** tones "
                           "(`LF_FSK2A_MARK_CYCLES = 4`); a real tag is symmetric 32/32 and 40/40",
         "C472"),
    ]
    out = ["## gap register", "",
           "| firmware | gap | evidence |", "|---|---|---|"]
    for fw, gap, ev in known:
        out.append("| %s | %s | %s |" % (fw, gap, ev))

    for fw, gap, ev in _observed_gaps(result):
        out.append("| %s | %s | run %s |" % (fw, gap, result.session))
    out.append("")
    return out


def _observed_gaps(result) -> list[tuple[str, str, str]]:
    """Gaps this run is entitled to assert. Licensed cells only, and one (protocol, reader) each."""
    owner = {"rd.pm3": "Proxmark", "rd.flip": "Flipper", "rd.cu": "ChameleonUltra"}
    emitter_owner = {"emu.cu1": "ChameleonUltra", "emu.cu2": "ChameleonUltra",
                     "emu.flip": "Flipper", "t55.flip": "Flipper"}
    gaps: list[tuple[str, str, str]] = []
    for c in result.cells:
        if c.outcome is Outcome.UNGRADED or c.observation is None:
            continue
        if c.outcome is Outcome.SILENT and c.source in ("t55.pm3", "oem"):
            gaps.append((owner[c.reader],
                         "does not decode `%s` from a real tag the calibration passed on" % c.protocol,
                         ""))
        elif c.outcome is Outcome.SILENT and c.source in emitter_owner:
            gaps.append((emitter_owner[c.source],
                         "`%s` emulation from `%s` is not decoded by `%s`, which decodes the same "
                         "protocol from a real tag in this session"
                         % (c.protocol, c.source, c.reader), ""))
        elif c.outcome is Outcome.WRONG:
            gaps.append((emitter_owner.get(c.source, owner[c.reader]),
                         "`%s` from `%s` decodes as something other than what was armed, read by "
                         "`%s`" % (c.protocol, c.source, c.reader), ""))
    # ⚠ dedupe, keeping order: the same gap seen on two sources is one gap with two witnesses.
    seen, uniq = set(), []
    for g in gaps:
        if g[:2] not in seen:
            seen.add(g[:2])
            uniq.append(g)
    return uniq


def _open_questions(result) -> list[str]:
    ungraded = [c for c in result.cells if c.outcome is Outcome.UNGRADED]
    if not ungraded:
        return []
    out = ["## open questions", "",
           "Cells the run could not grade. These are **not** findings — they are the work that is "
           "still outstanding, and the reason each one is outstanding.", ""]
    by_note: dict[str, list[Cell]] = {}
    for c in ungraded:
        by_note.setdefault(c.note.split(".")[0][:140], []).append(c)
    for note, group in sorted(by_note.items(), key=lambda kv: -len(kv[1])):
        out.append("- **%d cell%s** — %s" % (len(group), "" if len(group) == 1 else "s", note))
        out.append("  · " + "; ".join(sorted({"%s/%s" % (c.protocol, c.reader) for c in group})[:10]))
    out.append("")
    return out


def to_json(result, protocols: list[reg.Protocol]) -> str:
    """Machine-readable, so the Chameleon project can cite a cell by run id without re-arguing it."""
    return json.dumps({
        "session": result.session,
        "provenance": result.provenance,
        "started": result.started,
        "finished": result.finished,
        "aborted": result.aborted or None,
        "bench": {"cu_reader": result.plan.bench.cu_reader, "pad": result.plan.bench.pad},
        "cells": [{"protocol": c.protocol, "source": c.source, "reader": c.reader,
                   "outcome": c.outcome.value, "note": c.note,
                   "evidence": (c.observation.text[:400] if c.observation else None)}
                  for c in result.cells],
        "licences": [{"protocol": p, "reader": r, "source": lic.source, "pad": lic.pad,
                      "evidence": lic.evidence[:400]}
                     for (p, r), lic in sorted(result.licences.items())],
        "refusals": [{"protocol": p, "reader": r, "why": why}
                     for (p, r), why in sorted(result.refusals.items())],
        "void_blocks": [{"topology": b.block.topology.name, "why": b.void_why}
                        for b in result.void_blocks],
        "exclusions": [{"protocol": e.protocol, "source": e.source, "reader": e.reader,
                        "rule": e.rule, "why": e.why} for e in result.plan.exclusions],
    }, indent=2)
