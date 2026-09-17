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
from .stations import EMULATED_SOURCES, GOLD_SOURCES, READER_NOTE, REAL_SOURCES

#: Sources across the top of every table, left to right. ⚠ ORDERED, so the grid reads the same way
#: in every run and two runs can be diffed.
#:
#: ⛔⛔ AND DERIVED, BECAUSE THE HAND-MAINTAINED VERSION LOST A COLUMN. This was a fourth copy of
#: the source list and `emu.pm3` was never added to it when the Proxmark became an emitter. The
#: filter below keeps only sources that appear in SOURCE_ORDER, so ten MEASURED cells — every
#: `emu.pm3 → rd.cu1` reading in run 20260916_114253 — were dropped from the published grid without
#: a word. The tallies counted 27 for that reader and the table showed 17, and the operator read the
#: missing column as the Chameleon failing to read.
#:
#: ⚠ `plan.py` had already been given exactly this treatment for `EMULATED_ORDER`, with a comment
#: saying a new emitter "cannot be added to one and forgotten in the other". It was added to that
#: one and forgotten in THIS one.
SOURCE_ORDER = tuple(s for s in ("t55.pm3", "oem", "t55.flip", "t55.cu1", "t55.cu2",
                                 "emu.pm3", "emu.flip", "emu.cu1", "emu.cu2")
                     if s in REAL_SOURCES | EMULATED_SOURCES)
assert set(SOURCE_ORDER) == REAL_SOURCES | EMULATED_SOURCES, (
    "SOURCE_ORDER is missing %s — every cell from it would vanish from the grid"
    % ((REAL_SOURCES | EMULATED_SOURCES) - set(SOURCE_ORDER),))

READER_ORDER = tuple(r for r in ("rd.pm3", "rd.flip", "rd.cu1", "rd.cu2") if r in READER_NOTE)
assert set(READER_ORDER) == set(READER_NOTE), (
    "READER_ORDER is missing %s — that reader would get no table at all"
    % (set(READER_NOTE) - set(READER_ORDER),))


class GridError(Exception):
    """The grid cannot be rendered honestly."""


def _by_cell(cells: list[Cell]) -> dict:
    return {(c.protocol, c.source, c.reader): c for c in cells}


def merge(phase1, phase2):
    """Fold the isolation phase's verdicts into the screening phase's grid.

    ⛔ AN ISOLATED VERDICT ALWAYS WINS *OVER A PLACEHOLDER*. A screening result is not a verdict at
    all, so there is no conflict to resolve — the phase-2 cell simply replaces the placeholder that
    queued it. A cell phase 2 could not reach (its licence was revoked, its write refused) keeps the
    screening note, which still says honestly that the reading exists and has not been isolated.

    ⛔⛔ AND THAT PREMISE ONLY HOLDS FOR A PLACEHOLDER. This keyed off `crowding`, which is true of
    every reading taken in a crowded stack including the licensed and the merely unlicensed ones —
    so a real observation could be replaced by a worse one. It was: an EXACT fdxb read was
    overwritten by a non-result taken behind a failed park, and the published record went on to cite
    the reading it had just deleted. A cell that is not `provisional` is evidence, and evidence is
    not replaced — phase 2 has nothing to say about it.
    """
    isolated = _by_cell(phase2.cells)
    out = []
    for c in phase1.cells:
        repl = isolated.get((c.protocol, c.source, c.reader))
        out.append(repl if (repl is not None and c.provisional) else c)
    seen = {(c.protocol, c.source, c.reader) for c in out}
    out += [c for k, c in isolated.items() if k not in seen]
    phase1.cells = _relicense(out, phase1.licences)
    phase1.blocks = list(phase1.blocks) + list(phase2.blocks)
    phase1.refusals.update({k: v for k, v in phase2.refusals.items()})
    phase1.finished = phase2.finished
    return phase1


def _relicense(cells: list[Cell], licences: dict) -> list[Cell]:
    """Grant the licences phase 2 just earned, and re-grade what was waiting on them.

    ⛔⛔ AN ISOLATED GOLD ROW IS A LICENCE, AND MERGING IT WITHOUT GRANTING ONE WASTES THE WHOLE
    PHASE. When the cell phase 2 goes back for is a CALIBRATION row, settling it is not one cell's
    business: every reading of that (protocol, reader) was graded UNGRADED for want of exactly the
    licence phase 2 has now produced.

    ⚠ IT HAPPENED, AND IT LOOKED LIKE A DEVICE FAULT. Run 20260916_125646 screened
    `em410x t55.pm3 -> rd.cu1` SILENT in a crowded stack, isolated it, and read it byte-exact — and
    still published `em410x` as "⛔ no licence — the calibration row was screened SILENT in a
    crowded stack and awaits isolation", with `em410x emu.pm3 -> rd.cu1` UNGRADED beside a note
    saying it had read EXACT. The bench had done the work; the grid said it was outstanding.

    ⭐ RE-GRADED FROM THE STORED OBSERVATION, never by editing an outcome. A cell whose reading was
    WRONG or SILENT stays WRONG or SILENT once licensed — the licence decides whether a reading may
    be scored, not what it scores.
    """
    from .outcomes import Calibration, CalibrationRefused, grade
    from .stations import GOLD_SOURCES
    fresh = {}
    for c in cells:
        pair = (c.protocol, c.reader)
        if (c.source in GOLD_SOURCES and c.outcome is Outcome.EXACT and c.observation is not None
                and pair not in licences):
            try:
                fresh[pair] = licences[pair] = Calibration.from_row(c.observation, GOLD_SOURCES)
            except CalibrationRefused:
                pass
    if not fresh:
        return cells
    out = []
    for c in cells:
        lic = fresh.get((c.protocol, c.reader))
        if lic is None or c.outcome is not Outcome.UNGRADED or c.observation is None:
            out.append(c)
            continue
        import dataclasses
        graded = grade(c.observation, lic, crowding=c.crowding)
        out.append(dataclasses.replace(graded, isolated=c.isolated, station=c.station,
                                       carried_from=c.carried_from))
    return out


def _audit(cells: list[Cell], sources: dict, readers: list[str],
           protocols: list[reg.Protocol]) -> None:
    """Every measured cell must have a square to appear in. ⛔ MEASURED AND NOT SHOWN IS THE WORST
    OF THE THREE STATES: refused says so with a reason, missing is visible as a blank, but a
    reading that was taken, graded, counted in the tallies and then rendered NOWHERE makes the grid
    disagree with itself — and the reader of it blames the device. `rd.cu1` scored 26 EXACT and
    displayed 17 (run 20260916_114253), and the ten `emu.pm3` readings holding the difference were
    the very ones that proved the Proxmark's emitter fixes had worked.

    ⚠ THE AXIS LISTS ARE NOT THE TEST — the cells are. An assertion on `SOURCE_ORDER` proves it
    agrees with `stations.py`; this proves the grid agrees with what actually happened, which is
    what the earlier assertion would still have missed had the source been absent from both.
    """
    keys = {p.key for p in protocols}
    lost = sorted({(c.protocol, c.source, c.reader) for c in cells
                   if c.reader not in readers or c.protocol not in keys
                   or c.source not in sources.get(c.reader, ())})
    if lost:
        raise GridError(
            "%d measured cell(s) would not appear anywhere in the grid: %s. The tallies count "
            "them and no table shows them, so the published grid contradicts its own totals. "
            "Check SOURCE_ORDER / READER_ORDER against stations.py."
            % (len(lost), "; ".join("%s %s → %s" % k for k in lost[:6])))


def render(result, protocols: list[reg.Protocol]) -> str:
    """The terminal/markdown grid: one table per reader, protocols down, sources across."""
    cells = _by_cell(result.cells)
    refused = {(e.protocol, e.source, e.reader) for e in result.plan.exclusions}
    readers = [r for r in READER_ORDER if any(c.reader == r for c in result.cells)]
    # ⛔ COLUMNS ARE PER READER, BECAUSE A SOURCE THIS READER NEVER SAW IS NOT A GAP IN ITS ROW.
    # One global list put `emu.cu1` in the `rd.cu1` table, refused all the way down — a Chameleon
    # cannot emulate and read at the same time, so that column was not an omission or a decision
    # about this run, it was an IMPOSSIBILITY given a whole column of its own. The operator: "that's
    # not a possible configuration... that should just be dropped from the table, as it's confusing."
    #
    # ⚠ A `– refsd` IS ONLY INFORMATIVE BESIDE A MEASUREMENT. In a live column it says this protocol
    # was refused and the others were not; in a column of nothing else it says only that the column
    # should not have been drawn. Every refusal keeps its full entry under "refused at plan time",
    # with the rule that made it — which is where a reason belongs, not spread down a dead column.
    sources = {r: [s for s in SOURCE_ORDER
                   if any(c.source == s and c.reader == r for c in result.cells)]
               for r in readers}
    _audit(result.cells, sources, readers, protocols)
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
    carried = [c for c in result.cells if c.carried_from]
    if carried:
        lines.append("")
        lines.append("⟲ **%d of these cells were carried forward from run `%s`** — stations it "
                     "completed with both null sweeps agreeing, on the same firmware, pad and "
                     "harness commit. Each was re-graded here from its stored evidence, not copied. "
                     "Cells measured in THIS session take precedence where both exist."
                     % (len(carried), result.carried_from or carried[0].carried_from))
    lines.append("")
    lines.extend(_provenance(result))

    for rdr in readers:
        lines.append("## reader `%s` — %s" % (rdr, READER_NOTE[rdr]))
        lines.append("")
        cols = sources[rdr]
        lines.append("| %-*s | %s |" % (w, "protocol", " | ".join("%-8s" % s for s in cols)))
        lines.append("|" + "|".join(["-" * (w + 2)] + ["-" * 10] * len(cols)) + "|")
        for p in protocols:
            row = []
            for s in cols:
                c = cells.get((p.key, s, rdr))
                if c is None:
                    # ⚠ A BLANK CELL READS AS MISSING DATA. A refused cell is a decision with a
                    # reason, and the grid should not make it look like an omission.
                    row.append("%-8s" % ("– refsd" if (p.key, s, rdr) in refused else ""))
                else:
                    mark = "%s %s" % (c.glyph, _short(c.outcome))
                    # ◌ marks a reading that is still only a screening result. ⛔ NOT every UNGRADED
                    # reading from a crowded stack: an unlicensed one is a finished measurement
                    # waiting on a gold row, and painting it ◌ tells the operator to go and
                    # rearrange a bench that would not change it.
                    if c.provisional:
                        mark = "◌ scrn"
                    row.append("%-8s" % mark)
            lines.append("| %-*s | %s |" % (w, p.key, " | ".join(row)))
        lines.append("")
        lines.extend(_calibration_notes(result, rdr))
        lines.append("")
    lines.extend(_tallies(result, readers))
    lines.extend(_exclusions(result.plan.exclusions))
    lines.extend(_voids(result))
    lines.extend(_unstable(result))
    lines.extend(gap_register(result, protocols))
    lines.extend(_bad_markers(result))
    lines.extend(_unparsed(result))
    lines.extend(_open_questions(result))
    return "\n".join(lines)


def _unstable(result) -> list[str]:
    """Cells that disagree with an earlier run on the same firmware.

    ⭐⭐ THE STRONGEST THING THIS BENCH CAN SAY, and it could not say it until now. Every other
    control here defends ONE run — calibration, null sweeps, the crowded-stack rule — and none of
    them can tell you that the null you are about to publish as a firmware gap read byte-exact
    half an hour ago. A cell that contradicts itself is not a gap and is not a pass; it is an
    instability, and naming it is worth more than either verdict would have been.
    """
    rows = getattr(result, "disagreements", ())
    if not rows:
        return []
    out = ["## ⚠ cells that disagree with an earlier run", "",
           "Same firmware on every device, same registry, different answer. **No finding is built "
           "on these** — a single reading is not evidence when the same bench has already "
           "contradicted it, and two readings are not settled by counting them. What settles one is "
           "a cause: a timing, a settle period, a bench arrangement that differs between the runs.",
           "",
           "| protocol | source | reader | now | earlier |", "|---|---|---|---|---|"]
    for proto, source, reader, now, other in rows:
        was = "; ".join("`%s` %s" % (r.session, r.outcome) for r in other[:3])
        out.append("| `%s` | `%s` | `%s` | **%s** | %s |" % (proto, source, reader, now, was))
    out.append("")
    return out


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


def _unparsed(result) -> list[str]:
    """⛔ SUSPECTED HARNESS FAULTS, PUBLISHED NEXT TO THE RESULTS. A reading that scored SILENT while
    the device plainly printed something is far more likely to be a wrong decode marker or a wrong
    expectation than a deaf reader — and 18 expectations in this registry have never been observed
    being printed by the device they describe. Every harness bug in this project so far has been an
    assumption about output shape surfacing as a claim about hardware."""
    odd = getattr(result, "unparsed", {})
    if not odd:
        return []
    out = ["## ⛔ silences that may be OURS", "",
           "Each of these scored `SILENT` — the decode marker did not fire and the expectation did "
           "not match — and yet the reader printed lines this harness cannot account for. **Do not "
           "read these as decoder gaps.** A null is only evidence with a positive control, and "
           "output we cannot parse is a control pointing at the registry entry, not at the device.",
           "", "| protocol | reader | what it printed that we did not recognise |", "|---|---|---|"]
    for (proto, reader), said in sorted(odd.items()):
        out.append("| `%s` | `%s` | `%s` |"
                   % (proto, reader, " / ".join(said)[:120].replace("|", "\|")))
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
_DEVICE_OF = {"rd.pm3": "pm3", "rd.flip": "flipper", "rd.cu1": "cu1", "rd.cu2": "cu2"}


def _firmware_of(result, reader: str) -> str:
    """What the reader named in a cell was running — linked to the cell, not left to be joined."""
    dev = _DEVICE_OF.get(reader, reader)
    fw = _device_names(getattr(result, "firmware", {}) or {})
    return fw.get(dev) or fw.get(reader) or "unknown"


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
    # ⛔⛔ GROUPED BY THE REASON, NOT BY THE RULE NAME. `group[0].why` printed the FIRST member's
    # sentence for the whole rule and dropped the rest — and the reasons here NAME THINGS, so
    # members of one rule routinely differ. Run 20260916_114253 published "no Proxmark simulation
    # command is registered for keri" over a group that was half `em410x_electra`, and one
    # "(emu.pm3, rd.pm3) puts the Proxmark on its own antenna" over a group that was mostly
    # Chameleon cells. The operator reading it learns why one member was refused and is told
    # nothing about the others, while looking at a sentence that appears to cover them.
    #
    # ⚠ THIRD TIME IN THIS FILE: one string used both as a grouping key and as the text. The note
    # truncation in `_open_questions` carries the same warning, written after the same bug.
    by_reason: dict[tuple, list[Exclusion]] = {}
    for e in exclusions:
        by_reason.setdefault((e.rule, e.why), []).append(e)
    for (rule, why) in sorted(by_reason):
        group = by_reason[(rule, why)]
        out.append("**%s** — %d cell%s" % (rule, len(group), "" if len(group) == 1 else "s"))
        out.append("")
        out.append("> %s" % why)
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
        # ⭐⭐ THE ONE ROW HERE THAT IS ABOUT THE INSTRUMENT WE GRADE WITH, which is why it
        # is worth more than the others: `lf <proto> reader` is the path every emulate cell is
        # judged on, and it can miss a signal that the SAME samples yield once round-tripped.
        ("Proxmark", "`lf read` → `lf gproxii demod` finds **nothing** on a signal that the "
                     "**same 40,000 samples** decode after `data save` + `data load` — one "
                     "session, one buffer, byte-exact `fac2a38c2b081af0210b12c2` either way. Live "
                     "`lf gproxii reader` 0 of 8; save/load 3 of 3. ⚠ `indala` fails BOTH "
                     "ways, so it is specific and not a universal rescue",
         "ChameleonUltra C487, 2026-09-16"),
        # ⛔ RETRACTED ROW, KEPT AS A ROW. The register used to carry this as a Proxmark
        # capability and the correction below used to assert it. The hardware says otherwise.
        ("Proxmark", "**cannot distinguish Electra from plain em410x**: `lf em 410x clone "
                     "--electra` writes it and prints `Electra 0x7e1eaaaaaaaaaaaa`, but `lf em "
                     "410x reader` then prints `EM 410x ID 2244668800` and nothing else, and "
                     "`reader -h` has no Electra flag at all. On this bench only the Flipper "
                     "tells them apart", "operator bench, measured 2026-09-16"),
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
           "it is. The ChameleonUltra is missing 4 of the Flipper's protocols rather than 10 "
           "(retracted 2026-09-15 against source). ⛔ **And the Electra retraction was itself "
           "wrong and is now retracted**: this note used to say *the Proxmark DOES support "
           "Electra and its reader prints the Electra value*, which was read from source and "
           "never run. Measured 2026-09-16 the reader prints only `EM 410x ID` and has no Electra "
           "flag — it is a gap row again, above. ⭐ Both directions of that mistake were made by "
           "reading rather than running.", "",
           "| firmware | gap | evidence |", "|---|---|---|"]
    for fw, gap, ev in known:
        out.append("| %s | %s | %s |" % (fw, gap, ev))

    for fw, gap, ev in _observed_gaps(result):
        out.append("| %s | %s | run %s |" % (fw, gap, result.session))
    out.append("")
    return out


#: device suffix -> whose firmware a finding about it belongs to.
_OWNER_OF = {"pm3": "Proxmark", "flip": "Flipper", "cu1": "ChameleonUltra", "cu2": "ChameleonUltra"}


def _observed_gaps(result) -> list[tuple[str, str, str]]:
    """Gaps this run is entitled to assert. Licensed cells only, and one (protocol, reader) each.

    ⛔⛔ AND NOT ONE THE SAME BENCH HAS ALREADY CONTRADICTED. `result.unstable` holds every cell that
    an earlier run on THIS firmware graded differently, and no claim may be built on one. A single
    SILENT is not sufficient evidence of a decoder gap: `em410x emu.pm3 -> rd.cu1` decoded
    byte-exact at 11:19 and answered `LF tag not found` at 11:52, and this register was the thing
    about to write that up as a Proxmark firmware gap.

    ⚠ NOT A VOTE. Two readings that disagree are not settled by counting them — the cell is withheld
    and reported as unstable, which is its own finding and a more useful one.
    """
    owner = {"rd.pm3": "Proxmark", "rd.flip": "Flipper",
             "rd.cu1": "ChameleonUltra", "rd.cu2": "ChameleonUltra"}
    # ⛔⛔ DERIVED, BECAUSE THE HAND-KEPT VERSION COULD NOT SEE THE PROXMARK'S EMITTER AT ALL. This
    # was a FOURTH copy of the source list — after SOURCE_ORDER in this same file — and `emu.pm3`
    # was never added to it. A cell with no owner falls through every branch below, so a failure of
    # the gold emitter was not suppressed deliberately, it was unrepresentable: `emu.pm3` is the one
    # source in the registry that could never be the subject of a finding.
    #
    # ⚠ THE GOLD SOURCES ARE ABSENT ON PURPOSE and that is a different thing. A silence from a real
    # tag the calibration passed on is a fact about the READER, handled by its own branch above.
    emitter_owner = {s: _OWNER_OF[s.split(".", 1)[1]]
                     for s in (REAL_SOURCES | EMULATED_SOURCES) - GOLD_SOURCES}
    shaky = getattr(result, "unstable", frozenset())
    gaps: list[tuple[str, str, str]] = []
    for c in result.cells:
        if (c.protocol, c.source, c.reader) in shaky:
            continue
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
    # ⛔ THE TRUNCATION IS A GROUPING KEY, NOT THE TEXT. Using one string for both published
    # "the write was issued and nothing decoded anything at all. No reader present has been shown
    # to decode fdxb at all this session, so this cannot be told apart from" — cut exactly where
    # the sentence was about to say what to do next. The whole reason a cell is outstanding IS this
    # section's content; there is nothing here worth saving 200 characters on.
    by_note: dict[str, tuple[str, list[Cell]]] = {}
    for c in ungraded:
        full = " ".join(c.note.split())
        by_note.setdefault(full[:160], (full, []))[1].append(c)
    for _, (note, group) in sorted(by_note.items(), key=lambda kv: -len(kv[1][1])):
        out.append("- **%d cell%s** — %s" % (len(group), "" if len(group) == 1 else "s", note))
        ids = sorted({"%s/%s" % (c.protocol, c.reader) for c in group})
        out.append("  · " + "; ".join(ids[:10])
                   + (" (and %d more)" % (len(ids) - 10) if len(ids) > 10 else ""))
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
                   "station": c.station or None, "carried_from": c.carried_from or None,
                   # ⭐ SAYS WHICH ROWS ARE PLACEHOLDERS. Without it a reader of the JSON cannot
                   # tell a screening result awaiting isolation from a finished measurement that
                   # has no gold row yet, which are opposite kinds of outstanding work.
                   "provisional": c.provisional,
                   "decoded": (list(c.observation.summary) if c.observation else None),
                   "evidence": (c.observation.text[-1200:] if c.observation else None)}
                  for c in result.cells],
        "licences": [{"protocol": p, "reader": r, "source": lic.source, "pad": lic.pad,
                      "evidence": lic.evidence[:400]}
                     for (p, r), lic in sorted(result.licences.items())],
        "refusals": [{"protocol": p, "reader": r, "why": why}
                     for (p, r), why in sorted(result.refusals.items())],
        # ⭐ THE HANDLE A LATER RUN NEEDS. Within a run we can confirm a write or be unable to;
        # what we cannot do is settle a silence no reader present could interpret. A later run — a
        # better decoder, a different writer — may settle it, but only if this record says plainly
        # WHICH silence is outstanding and on WHAT FIRMWARE. Buried in a prose note it is not
        # usable; a reader reflashed since licenses nothing (RULES.md §11).
        "unattributed": [{"protocol": p, "reader": r,
                          "source": result.cells[i].source if i < len(result.cells) else None,
                          "reader_firmware": _firmware_of(result, r),
                          "settled_by": "a decode of %s on %s, same firmware, from any source"
                                        % (p, r)}
                         for i, p, r, _ in getattr(result, "unattributed", [])
                         if (p, r) not in getattr(result, "decoded_by", set())],
        "bad_markers": [{"protocol": p, "reader": r, "observed": line}
                        for (p, r), line in sorted(getattr(result, "bad_markers", {}).items())],
        "unparsed": [{"protocol": p, "reader": r, "printed": list(said)}
                     for (p, r), said in sorted(getattr(result, "unparsed", {}).items())],
        "void_blocks": [{"station": b.block.station.name, "why": b.void_why}
                        for b in result.void_blocks],
        "exclusions": [{"protocol": e.protocol, "source": e.source, "reader": e.reader,
                        "rule": e.rule, "why": e.why} for e in result.plan.exclusions],
        "stations": [b.block.station.name for b in result.blocks],
        # ⭐ THE UNIT A RESUME CAN TRUST. A station carries its own before/after null sweep, so one
        # that completed with both sweeps agreeing is a self-contained measurement (RULES.md §3) —
        # and that, not the run, is what a later session may carry forward.
        "completed_stations": [b.block.station.name for b in result.blocks
                               if not b.void and b.before is not None and b.after is not None],
    }, indent=2)
