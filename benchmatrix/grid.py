"""The published grid, the exclusion list, and the cross-firmware gap register (the gap register).

⛔⛔ THE GRID NEVER AGGREGATES ACROSS PROTOCOLS TO LICENSE A CLAIM ABOUT ONE (RULES.md §1,
corollary). "Reader A missed X, reader B missed Y, so each is just a decoder gap" is a fallacy that
has already cost one retracted conclusion. Every statement this module makes is scoped to one
(protocol, reader) pair. The
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
from .stations import READER_NOTE

SOURCE_ORDER = ("t55.pm3", "oem", "t55.flip", "t55.cu1", "t55.cu2",
                "emu.flip", "emu.cu1", "emu.cu2")
READER_ORDER = ("rd.pm3", "rd.flip", "rd.cu1", "rd.cu2")


def _by_cell(cells: list[Cell]) -> dict:
    return {(c.protocol, c.source, c.reader): c for c in cells}


def merge(phase1, phase2):
    """Fold the isolation phase's verdicts into the screening phase's grid.

    ⛔ AN ISOLATED VERDICT ALWAYS WINS. A screening result is not a verdict at all, so there is no
    conflict to resolve — the phase-2 cell simply replaces the placeholder that queued it. A cell
    phase 2 could not reach (its licence was revoked, its write refused) keeps the screening note,
    which still says honestly that the reading exists and has not been isolated.
    """
    isolated = _by_cell(phase2.cells)
    out = []
    for c in phase1.cells:
        repl = isolated.get((c.protocol, c.source, c.reader))
        out.append(repl if (repl is not None and c.crowding) else c)
    seen = {(c.protocol, c.source, c.reader) for c in out}
    out += [c for k, c in isolated.items() if k not in seen]
    phase1.cells = out
    phase1.blocks = list(phase1.blocks) + list(phase2.blocks)
    phase1.refusals.update({k: v for k, v in phase2.refusals.items()})
    phase1.finished = phase2.finished
    return phase1


def render(result, protocols: list[reg.Protocol]) -> str:
    """The terminal/markdown grid: one table per reader, protocols down, sources across."""
    cells = _by_cell(result.cells)
    refused = {(e.protocol, e.source, e.reader) for e in result.plan.exclusions}
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
    lines.append("legend  " + "   ".join("%s %s" % (GLYPH[o], o.value) for o in Outcome)
                 + "   ◌ screened in a crowded stack — not a verdict (RULES.md §7)"
                 + "   – refused at plan time, with a reason below")
    lines.append("")
    lines.append("stations: " + " → ".join(b.block.station.name for b in result.blocks))
    lines.append("")
    lines.extend(_provenance(result))

    for rdr in readers:
        lines.append("## reader `%s` — %s" % (rdr, READER_NOTE[rdr]))
        lines.append("")
        lines.append("| %-*s | %s |" % (w, "protocol", " | ".join("%-8s" % s for s in sources)))
        lines.append("|" + "|".join(["-" * (w + 2)] + ["-" * 10] * len(sources)) + "|")
        for p in protocols:
            row = []
            for s in sources:
                c = cells.get((p.key, s, rdr))
                if c is None:
                    # ⚠ A BLANK CELL READS AS MISSING DATA. A refused cell is a decision with a
                    # reason, and the grid should not make it look like an omission.
                    row.append("%-8s" % ("– refsd" if (p.key, s, rdr) in refused else ""))
                else:
                    mark = "%s %s" % (c.glyph, _short(c.outcome))
                    # ◌ marks a reading that is still only a screening result.
                    if c.crowding and c.outcome is Outcome.UNGRADED and c.observation is not None:
                        mark = "◌ scrn"
                    row.append("%-8s" % mark)
            lines.append("| %-*s | %s |" % (w, p.key, " | ".join(row)))
        lines.append("")
        lines.extend(_calibration_notes(result, rdr))
        lines.append("")
    lines.extend(_tallies(result, readers))
    lines.extend(_exclusions(result.plan.exclusions))
    lines.extend(_voids(result))
    lines.extend(gap_register(result, protocols))
    lines.extend(_bad_markers(result))
    lines.extend(_open_questions(result))
    return "\n".join(lines)


def _bad_markers(result) -> list[str]:
    """⛔ A fault in the HARNESS, found on a run that otherwise passed. Published with the results
    because a grid whose instrument has a known defect should say so next to the numbers."""
    bad = getattr(result, "bad_markers", {})
    if not bad:
        return []
    out = ["## ⚠ registry faults found during this run", "",
           "These cells are correct. The **decode marker** for each pair did not fire on a "
           "byte-exact read, which means it is wrong — and a marker that never matches is invisible "
           "while reads are correct, because a byte-exact hit stands in for it. The day it matters "
           "is the day that reader decodes the WRONG value and this harness reports `SILENT` "
           "instead of `WRONG`. Fix the marker before trusting a silence from these pairs.", "",
           "| protocol | reader | what the device actually printed |", "|---|---|---|"]
    for (proto, reader), line in sorted(bad.items()):
        out.append("| `%s` | `%s` | `%s` |" % (proto, reader, line.replace("|", "\\|")[:90]))
    out.append("")
    return out


def _provenance(result) -> list[str]:
    """⛔ WHAT WAS RUNNING WHEN THIS WAS MEASURED. A cell is a claim about a firmware, not about a
    device in general — the two Chameleons on this bench run different builds on purpose, and
    "the Chameleon decodes Keri" means nothing until it says which one and which build. A grid that
    cannot answer that cannot be cited later, which is the only thing a grid is for."""
    if not result.firmware:
        return []
    out = ["### what was running", "", "| device | firmware |", "|---|---|"]
    # ⚠ ONE NAMING SCHEME. The devices were keyed by whatever attribute they happened to have, so
    # the published table mixed device names (`cu1`) with reader ids (`rd.pm3`) — in a record whose
    # whole job is to say unambiguously what was running.
    for dev, ver in sorted(_device_names(result.firmware).items()):
        flag = "" if ver and "not reported" not in ver else " ⚠"
        out.append("| `%s`%s | %s |" % (dev, flag, ver or "unknown"))
    out.append("| `rfid-tools` | %s |" % (result.harness or "unknown"))
    out.append("")
    return out


#: Reader ids the channels report themselves as, mapped to the device they are.
_DEVICE_OF = {"rd.pm3": "pm3", "rd.flip": "flipper", "rd.cu": "cu"}


def _device_names(firmware: dict) -> dict:
    return {_DEVICE_OF.get(k, k): v for k, v in firmware.items()}


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
           "license a claim about one of them is a fallacy (RULES.md §1). Read the per-(protocol, reader) "
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
        out.append("- **%s** — %s" % (b.block.station.name, b.void_why))
    out.append("")
    return out


def gap_register(result, protocols: list[reg.Protocol]) -> list[str]:
    """Cross-firmware gaps, as first-class rows rather than asides.

    ⭐ THIS IS THE DELIVERABLE THAT MAKES THE PROJECT WORTH RUNNING AGAINST OTHER FIRMWARES. An
    upstream maintainer can run the matrix themselves, and a gap row with the capture that proves it
    is the strongest form a bug report takes.

    ⛔ ONLY LICENSED CELLS APPEAR HERE. A gap is a claim about a firmware; an UNGRADED cell is a
    claim about nothing. The gaps already known are listed with their provenance
    so that a row this run produced is never confused with one taken on trust.
    """
    known = [
        ("Flipper", "cannot **write** keri, nexwatch, idteck, gproxii to a T5577 that the pm3 "
                    "writes fine", "operator bench, 2026-09"),
        ("Flipper", "can emulate Indala224 but cannot write it", "operator bench"),
        ("Proxmark", "does not decode the Flipper's Indala224 emulation", "operator bench"),
        ("Proxmark", "no dedicated InstaFob command", "`cmdlf.c` `CommandTable[]`"),
        ("ChameleonUltra", "**4** of the Flipper's 26 protocols absent — EM4100/16, EM4100/32, "
                           "HidGeneric, HidExGeneric. A further 4 (fdxa, paradox, pyramid, "
                           "instafob) are read and cloned but not emulated, which is a row shape "
                           "and not a gap", "`SCOPE.md` §B/§C"),
        ("ChameleonUltra", "FSK2a mark is a fixed 32 µs on **both** tones "
                           "(`LF_FSK2A_MARK_CYCLES = 4`); a real tag is symmetric 32/32 and 40/40",
         "ChameleonUltra bench"),
    ]
    out = ["## gap register", "",
           "⚠ The rows above the run's own are carried from `SCOPE.md` and are only as current as "
           "it is. Two were retracted on 2026-09-15 after being checked against source: the "
           "Proxmark DOES support Electra (`lf em 410x clone --electra`, and its reader prints the "
           "Electra value), and the ChameleonUltra is missing 4 of the Flipper's protocols rather "
           "than 10.", "",
           "| firmware | gap | evidence |", "|---|---|---|"]
    for fw, gap, ev in known:
        out.append("| %s | %s | %s |" % (fw, gap, ev))

    for fw, gap, ev in _observed_gaps(result):
        out.append("| %s | %s | run %s |" % (fw, gap, result.session))
    out.append("")
    return out


def _observed_gaps(result) -> list[tuple[str, str, str]]:
    """Gaps this run is entitled to assert. Licensed cells only, and one (protocol, reader) each."""
    owner = {"rd.pm3": "Proxmark", "rd.flip": "Flipper",
             "rd.cu1": "ChameleonUltra", "rd.cu2": "ChameleonUltra"}
    emitter_owner = {"emu.cu1": "ChameleonUltra", "emu.cu2": "ChameleonUltra",
                     "emu.flip": "Flipper", "t55.flip": "Flipper",
                     "t55.cu1": "ChameleonUltra", "t55.cu2": "ChameleonUltra"}
    gaps: list[tuple[str, str, str]] = []
    for c in result.cells:
        if c.outcome is Outcome.UNGRADED or c.observation is None:
            continue
        # ⛔ ONLY AN ISOLATED READING MAY BECOME A GAP. A success in a crowded stack is a success,
        # but a gap is a claim that something does NOT work, and the crowded-stack rule says a
        # crowded stack cannot support that claim.
        if c.crowding and c.outcome is not Outcome.EXACT:
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
    # ⚠ NOT `split(".")`. Every reader id has a dot in it, so grouping on the first sentence cut
    # "(viking, rd.pm3): the calibration row DECODED..." down to "(viking, rd".
    by_note: dict[str, list[Cell]] = {}
    for c in ungraded:
        by_note.setdefault(" ".join(c.note.split())[:160], []).append(c)
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
        "firmware": dict(result.firmware),
        "harness": result.harness,
        "started": result.started,
        "finished": result.finished,
        "aborted": result.aborted or None,
        "bench": {"pad": result.plan.bench.pad, "max_stack": result.plan.bench.max_stack,
                  "tags": result.plan.bench.tag_count,
                  "devices": sorted(result.plan.bench.has)},
        "cells": [{"protocol": c.protocol, "source": c.source, "reader": c.reader,
                   "outcome": c.outcome.value, "note": c.note,
                   "crowding": sorted(c.crowding), "isolated": c.isolated,
                   "decoded": (list(c.observation.summary) if c.observation else None),
                   "evidence": (c.observation.text[-1200:] if c.observation else None)}
                  for c in result.cells],
        "licences": [{"protocol": p, "reader": r, "source": lic.source, "pad": lic.pad,
                      "evidence": lic.evidence[:400]}
                     for (p, r), lic in sorted(result.licences.items())],
        "refusals": [{"protocol": p, "reader": r, "why": why}
                     for (p, r), why in sorted(result.refusals.items())],
        "bad_markers": [{"protocol": p, "reader": r, "observed": line}
                        for (p, r), line in sorted(getattr(result, "bad_markers", {}).items())],
        "void_blocks": [{"station": b.block.station.name, "why": b.void_why}
                        for b in result.void_blocks],
        "exclusions": [{"protocol": e.protocol, "source": e.source, "reader": e.reader,
                        "rule": e.rule, "why": e.why} for e in result.plan.exclusions],
        "stations": [b.block.station.name for b in result.blocks],
    }, indent=2)
