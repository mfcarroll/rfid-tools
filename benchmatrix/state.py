"""What this bench currently believes, amalgamated across every run that measured it.

⭐⭐ A RUN IS A SESSION AND THE STATE IS A QUESTION ABOUT DEVICES. Every published grid answers
"what happened that afternoon"; nobody actually wants to know that. What they want is "can the
Chameleon on my desk read gproxii today", and that answer is spread across a dozen runs of
different shapes — one that skipped the Flipper, one that only did em410x, one that aborted at
station three. Until now there was no way to put them together, and the only way to see the whole
matrix was to measure the whole matrix again.

⛔⛔ AND THE OBVIOUS AMALGAMATION IS THE WRONG ONE. `resume` requires the ENTIRE bench firmware to
match before it will carry a station forward, which is correct for what it does — a carried station
is republished as part of a NEW run, so everything about that run must line up. Applying the same
rule here would refuse to combine a `--no-cu2` run with a full one, on the grounds that a device
neither reading was about happened to be absent from one of them.

⇒ A CELL IS A CLAIM ABOUT ONLY THE DEVICES IN IT (RULES.md §11, read exactly). `em410x t55.pm3 ->
rd.cu1` is a claim about the Proxmark that wrote the tag and the Chameleon that read it. Reflash
either and the reading is about a different instrument; reflash the Flipper, or leave it in a
drawer, and the reading is untouched. That is what lets runs of different shapes combine, and it is
strictly MORE careful than the whole-bench rule, not less: a reading is retired the moment anything
it actually depended on changed.

⛔ THE LATEST READING IS NOT AUTOMATICALLY THE ANSWER. Where readings on the same relevant firmware
disagree, the cell is DISPUTED and no verdict is published — the same rule the gap register
follows. Taking the newest would quietly turn "we have contradictory evidence" into "it works now",
which is the exact failure the operator named: locking a past bad run into the current picture,
only in the other direction.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field

from .stations import READERS, SOURCES


@dataclass(frozen=True)
class Reading:
    session: str
    outcome: str
    when: str
    #: Firmware of the devices THIS cell depended on — not of the bench it was taken on.
    firmware: tuple


@dataclass
class Known:
    """Everything the bench has ever said about one cell, newest first."""

    protocol: str
    source: str
    reader: str
    readings: list = field(default_factory=list)

    @property
    def current(self):
        """Readings taken on the firmware that is on the bench now, newest first."""
        return self.readings

    @property
    def disputed(self) -> bool:
        return len({r.outcome for r in self.readings}) > 1

    @property
    def verdict(self) -> str:
        """⛔ DISPUTED IS ITS OWN ANSWER. Not the newest, not the majority — see the module note."""
        if not self.readings:
            return ""
        return "DISPUTED" if self.disputed else self.readings[0].outcome

    @property
    def latest(self):
        return self.readings[0] if self.readings else None


def devices_in(source: str, reader: str) -> frozenset:
    """Which devices a cell's answer actually depends on.

    ⚠ THE WRITER, NOT THE TAG. A T5577 has no firmware and carries none of its writer into what it
    transmits — but the write itself is the thing under test in a `t55.X` row, so X counts. For an
    emulation the emitting device is the source outright.
    """
    dev, writer = SOURCES.get(source, (None, None))
    out = {writer or dev, READERS.get(reader)}
    return frozenset(d for d in out if d)


def firmware_for(devices: frozenset, table: dict) -> tuple:
    """The firmware entries for those devices, as a comparable tuple.

    ⛔ THE TABLE IS KEYED INCONSISTENTLY and pretending otherwise silently matches nothing. A run
    records the Proxmark as `rd.pm3` (its `id`, there being no `name`) and the Chameleons as `cu1`
    / `cu2` (their `name`), because `firmware_key` takes whichever exists.

    ⛔⛔ AND AN UNKNOWN RETURNS None, BECAUSE TWO UNKNOWNS MUST NOT COMPARE EQUAL. The first
    version filled a missing entry with `"?"` and compared tuples, so a run that never recorded the
    Flipper's firmware matched a bench with NO FLIPPER ATTACHED — `("flipper", "?")` on both sides
    — and `t55.flip → rd.pm3` appeared in the current state off a device that was not in the room.
    Caught on the first real output, by a column that should not have been there.

    ⇒ "We do not know what was running" is not "it was the same", and the whole value of this
    module is that it refuses readings about instruments that are no longer here.
    """
    out = []
    for d in sorted(devices):
        if d in ("t5577", "oemtag", "T5577", "OEM card"):
            continue                       # a passive tag runs no firmware
        hit = table.get(d) or table.get("rd.%s" % d) or table.get(d.replace("rd.", ""))
        if not hit:
            return None
        out.append((d, hit))
    return tuple(out)


def refusals(runs_dir: str) -> dict:
    """Every (protocol, source, reader) some run refused at plan time, and the rule that did it.

    ⛔⛔ A REFUSAL IS NOT A GAP IN THE WORK. The first version of this module lumped them into
    "never measured on these devices" under a sentence explicitly promising it had not — listing
    `viking t55.cu1 -> rd.cu1` (covered by two other cells) and every `em410x_electra` row (no
    Chameleon read command exists) as though somebody had merely not got round to them. Whoever
    read that would go and spend an afternoon on cells the planner refuses for good reasons.

    ⚠ AND A REFUSAL IS A PROPERTY OF THE RULES, NOT OF A FIRMWARE, which is why this is not
    firmware-filtered like the readings are. `self-judging` and `covered` will refuse the same cell
    on any bench; a refusal that DOES depend on firmware names it and stops applying when the
    registry changes.
    """
    out: dict = {}
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.json"))):
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for e in doc.get("exclusions", []):
            out.setdefault((e["protocol"], e["source"], e["reader"]), e["rule"])
    return out


def gather(runs_dir: str, now: dict) -> dict:
    """Every cell any run has measured, restricted to readings still about TODAY's devices.

    `now` is the current firmware table, as a run records it. A reading whose devices are no longer
    running what they were is dropped — not contradicted, dropped: it is a claim about an
    instrument that no longer exists.
    """
    found: dict = {}
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.json"))):
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        if doc.get("aborted") or not doc.get("session"):
            continue
        was, when = doc.get("firmware") or {}, doc.get("started", "")
        for c in doc.get("cells", []):
            if c.get("outcome") == "UNGRADED":
                continue                   # the run could not judge it; it is not an answer
            devs = devices_in(c["source"], c["reader"])
            then, today = firmware_for(devs, was), firmware_for(devs, now)
            if then is None or today is None or then != today:
                continue                   # about a different instrument, or unknowable
            key = (c["protocol"], c["source"], c["reader"])
            found.setdefault(key, Known(*key)).readings.append(
                Reading(doc["session"], c["outcome"], when, then))
    for k in found.values():
        k.readings.sort(key=lambda r: r.when, reverse=True)
    return found


#: How a verdict prints. ⚠ DISPUTED IS NOT AN OUTCOME — it is the absence of one, and it gets a
#: glyph of its own so it cannot be mistaken for a fifth grade.
#: ⛔ "NOT DONE" AND "REFUSED" GET DIFFERENT MARKS. They are opposite kinds of empty: one is work
#: somebody could go and do, the other is a cell the planner removes on purpose and always will.
#: Printing both as `–` sent the first version's reader towards an afternoon measuring `covered`
#: cells and every `em410x_electra` row, under a sentence promising it had not.
GLYPH = {"EXACT": "✅", "WRONG": "❌", "SILENT": "·", "DISPUTED": "⁇", "": "▫"}
REFUSED_GLYPH = "–"


def render(found: dict, now: dict, protocols, sources, readers, refused=None) -> str:
    """The whole matrix as it currently stands, with every cell's provenance behind it."""
    lines = ["# Bench state", "",
             "⭐ **What this bench believes right now**, amalgamated from every published run whose "
             "readings are still about the devices currently attached. This is not a run: no cell "
             "here was measured together with any other, and each carries its own session below.",
             "",
             "⛔ **A cell is a claim about the devices IN it** (RULES.md §11) — the writer or "
             "emitter, and the reader. Reflash one of those and its readings retire; reflash "
             "anything else and they stand. That is what lets runs of different shapes combine, "
             "and it retires a reading strictly sooner than a whole-bench rule would.", ""]
    lines.append("| device | firmware |")
    lines.append("|---|---|")
    for d, fw in sorted(now.items()):
        lines.append("| `%s` | %s |" % (d, fw))
    lines.append("")
    lines.append("legend  " + "   ".join("%s %s" % (g, k or "never measured")
                                         for k, g in GLYPH.items())
                 + "   %s refused by rule" % REFUSED_GLYPH)
    lines.append("")

    refused = refused or {}
    disputed, never, blocked = [], [], []
    for rdr in readers:
        cols = [s for s in sources if any((p.key, s, rdr) in found for p in protocols)]
        if not cols:
            continue
        w = max(len(p.key) for p in protocols)
        lines.append("## reader `%s`" % rdr)
        lines.append("")
        lines.append("| %-*s | %s |" % (w, "protocol", " | ".join("%-9s" % s for s in cols)))
        lines.append("|" + "|".join(["-" * (w + 2)] + ["-" * 11] * len(cols)) + "|")
        for p in protocols:
            row = []
            for s in cols:
                k = found.get((p.key, s, rdr))
                row.append("%-9s" % (GLYPH[k.verdict] if k else
                                     REFUSED_GLYPH if (p.key, s, rdr) in refused else GLYPH[""]))
                if k and k.disputed:
                    disputed.append(k)
                elif not k:
                    (blocked if (p.key, s, rdr) in refused else never).append((p.key, s, rdr))
            lines.append("| %-*s | %s |" % (w, p.key, " | ".join(row)))
        lines.append("")

    if disputed:
        lines += ["## ⁇ disputed — no verdict is published for these", "",
                  "Readings on the SAME devices and the same firmware that do not agree. **The "
                  "newest does not win**: taking it would turn contradictory evidence into "
                  "\"it works now\", which is the same mistake as locking in an old bad run, "
                  "pointing the other way. What settles one is a cause.", "",
                  "| protocol | source | reader | readings |", "|---|---|---|---|"]
        for k in disputed:
            got = "; ".join("`%s` %s" % (r.session, r.outcome) for r in k.readings[:5])
            lines.append("| `%s` | `%s` | `%s` | %s |" % (k.protocol, k.source, k.reader, got))
        lines.append("")

    if blocked:
        by = {}
        for n in blocked:
            by.setdefault(refused[n], []).append(n)
        lines += ["## %s refused by rule — %d cell(s)" % (REFUSED_GLYPH, len(blocked)), "",
                  "⚠ **Not work outstanding.** Each was removed from a plan before any bench time "
                  "was spent on it, and the run that refused it records the full reason. These are "
                  "not a thing to go and measure.", ""]
        for rule, ns in sorted(by.items()):
            lines.append("- **%s** (%d) — %s"
                         % (rule, len(ns), "; ".join("%s (%s → %s)" % n for n in ns[:8])
                            + (" …" if len(ns) > 8 else "")))
        lines.append("")

    if never:
        lines += ["## %s never measured on these devices — %d cell(s)" % (GLYPH[""], len(never)),
                  "",
                  "⚠ Not a failure and not a refusal: no published run has an answer for these on "
                  "the firmware currently attached. A refusal has a rule behind it and appears in "
                  "the run that refused it; this is simply work nobody has done yet.", ""]
        lines.append("  " + "; ".join("%s (%s → %s)" % n for n in never[:24])
                     + (" …" if len(never) > 24 else ""))
        lines.append("")

    counts = {}
    for k in found.values():
        counts[k.verdict] = counts.get(k.verdict, 0) + 1
    lines += ["## totals", "",
              "⚠ Cells, not evidence about any one protocol (RULES.md §1).", "",
              "  " + "  ".join("%s %s %d" % (GLYPH[v], v, n) for v, n in sorted(counts.items()))
              + "  ·  never measured %d" % len(never), ""]
    return "\n".join(lines)
