"""What the operator sees and hears when the bench has to change.

⛔⛔ OPERATOR POSITIONING ERROR IS THE LARGEST UNCONTROLLED RISK IN THIS WORK, and the cues are the
only thing keeping the bench and the plan in step. Two rules follow:

  • **The voice says one thing.** "Add the Proxmark and Chameleon 1, stack is Chameleon one on the
    Proxmark" is a delta and a restatement fighting each other, and the ear cannot hold it. The
    spoken form is the ARRANGEMENT — "put Chameleon 1 on the Proxmark, with a tag in between" — one
    sentence per rig, no removals, no recap.
  • **The screen shows the whole truth**, including what must NOT be on the bench. A diagram is
    read at a glance and checked against what is physically there; a list of removals has to be
    held in the head and compared. Anything not in a rig is named under "set aside", because the
    forgotten device is the one that ruins a run.
"""

from __future__ import annotations

import os
import sys

from .stations import HUMAN, SPOKEN, TAGS

#: ⚠ Colour is off unless stdout is a terminal, and `NO_COLOR` always wins — a grid redirected to a
#: file must not carry escape codes into the published record.
ENABLED = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

_C = {"dim": "2", "bold": "1", "red": "31", "green": "32", "yellow": "33",
      "blue": "34", "magenta": "35", "cyan": "36"}


def paint(text: str, *styles: str) -> str:
    if not ENABLED or not styles:
        return text
    codes = ";".join(_C[s] for s in styles if s in _C)
    return "\x1b[%sm%s\x1b[0m" % (codes, text) if codes else text


def spoken_removal(devices) -> str:
    """⚠ WHEN NOTHING IS BEING ADDED, THE ARRANGEMENT IS NOT AN INSTRUCTION. "Put Chameleon 1 on the
    Proxmark" is confusing when it is already there and the only thing to do is take the tag out.
    A pure removal is the one case where the delta IS the clearest thing to say."""
    names = [SPOKEN[d] for d in devices]
    if len(names) > 1:
        names = ["%s and %s" % (", ".join(names[:-1]), names[-1])]
    return "take out %s" % names[0]


def spoken_addition(added, station) -> str:
    """The mirror of `spoken_removal`: nothing is coming off, so say only what goes on.

    ⚠ THE SAME PRINCIPLE, AND IT WAS ONLY HALF APPLIED. "Put Chameleon 1 on the Proxmark, with a tag
    in between" describes a rig that is already built except for the tag, so the operator has to
    read the whole sentence, compare it against the bench, and work out that the one word that
    matters is "tag". "Put a tag in between" is the instruction.

    ⛔ ONLY WHEN NOTHING ELSE MOVES, and only when there IS a previous arrangement to add to — at
    the first station of a run the full description is what the operator needs, because there is no
    state to be a delta against. The caller enforces both; this just words it.

    ⭐ THE POSITION COMES FROM THE STACK, not from what the thing is. A tag usually goes in the
    middle because devices read from one face, but it is the index that knows that, and a device
    added on top should say "on top" without a second rule being written for it.
    """
    stack = list(station.stack)
    where = {}
    for d in added:
        i = stack.index(d)
        where[d] = ("in between" if 0 < i < len(stack) - 1
                    else "on top" if i == len(stack) - 1 else "underneath")
    said = ["put %s %s" % (SPOKEN[d], where[d]) for d in added]
    if len(said) > 1:
        return "%s, and %s" % (", ".join(said[:-1]), said[-1].replace("put ", ""))
    return said[0]


def spoken_arrangement(stations) -> str:
    """One sentence per rig, describing where things go. Nothing about what comes off.

    ⚠ THE ARRANGEMENT, NOT THE DELTA. A delta is only meaningful against a state the operator is
    holding in their head; an arrangement can be checked against the bench in front of them.
    """
    parts = [_one_rig_spoken(st) for st in stations]
    return ". ".join(p for p in parts if p)


def _one_rig_spoken(station) -> str:
    stack = list(station.stack)
    if len(stack) == 1:
        return "%s on its own, with nothing on it" % SPOKEN[stack[0]]
    base, top = stack[0], stack[-1]
    middle = [d for d in stack[1:-1]]
    said = "put %s on %s" % (SPOKEN[top], SPOKEN[base])
    if any(d in TAGS for d in middle):
        said += ", with a tag in between"
    elif middle:
        said += ", with %s in between" % " and ".join(SPOKEN[d] for d in middle)
    return said


def spoken_move(frm, to) -> str:
    """What to say for one bench change. THE ONE PLACE THAT DECIDES, so every caller agrees.

    ⛔ A MOVE IN ONE DIRECTION IS SAID AS THAT MOVE. Describing the whole arrangement is right when
    the bench is being rebuilt and noise when one thing goes on or comes off a rig that is otherwise
    already correct — the operator has to parse the sentence to find the one word in it that is an
    instruction. At the FIRST station (`frm is None`) there is no previous state for a delta to be
    against, so the arrangement is the only thing that can be checked against the bench.
    """
    from .stations import plan_move
    move = plan_move(frm, to)
    if move.remove and not move.place:
        return spoken_removal(move.remove)
    if move.place and not move.remove and frm is not None:
        return spoken_addition(move.place, to)
    return spoken_arrangement([to])


def working(out, what: str) -> "callable":
    """Announce a slow operation BEFORE it blocks, and report how long it took.

    ⛔⛔ SILENCE DURING A LONG CALL IS INDISTINGUISHABLE FROM A HANG, and the operator's only move
    is Ctrl-C — which aborts a healthy session. `cue_done` already exists for exactly this reason at
    the END of a run; the same argument applies to any step that blocks for tens of seconds with
    nothing on screen. A `lf t55xx wipe` writes eight blocks and its timeout is 120s, so "stuck" and
    "working" looked identical for as long as it took. Operator, mid-session: "Appears to be stuck".

    ⭐ AND THE ELAPSED TIME IS WORTH KEEPING. This bench optimises operator interventions, so
    knowing which machine steps cost twenty seconds and which cost two is what says whether a
    station is worth restructuring. It turns "is it stuck?" into a number.
    """
    import time
    out("      %s %s…" % (mark("wait"), what))
    started = time.monotonic()

    def done(line: str) -> None:
        out("%s  (%.0fs)" % (line, time.monotonic() - started))
    return done


def diagram(stations, idle=()) -> list[str]:
    """The bench as a picture: one column per rig, top of the stack at the top.

    ⭐ A TAG IS DRAWN IN BRACKETS because it is the one passive thing in the stack — it answers any
    field it is in, it has no idle state, and it is the piece most often left in place by mistake.
    """
    cols = []
    for n, st in enumerate(stations, 1):
        rows = [_label(d) for d in reversed(st.stack)]
        cols.append(["Rig %d" % n, "─" * max(13, max((len(r) for r in rows), default=0))] + rows)
    width = [max(len(_plain(r)) for r in col) + 4 for col in cols]
    height = max(len(c) for c in cols)

    out = []
    for row in range(height):
        line = ""
        for col, w in zip(cols, width):
            cell = col[row] if row < len(col) else ""
            line += cell + " " * (w - len(_plain(cell)))
        out.append("     " + line.rstrip())
    if idle:
        out.append("")
        out.append("     " + paint("set aside: ", "dim")
                   + paint(", ".join(HUMAN[d] for d in idle), "dim"))
    return out


def _label(dev: str) -> str:
    if dev in TAGS:
        return paint("( %s )" % HUMAN[dev].replace("the ", ""), "yellow")
    return paint(HUMAN[dev], "cyan", "bold")


def _plain(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        if text[i] == "\x1b":
            i = text.find("m", i) + 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


#: Status marks, coloured once so every call site agrees.
MARKS = {"ok": ("✓", ("green",)), "bad": ("⛔", ("red", "bold")), "warn": ("⚠", ("yellow",)),
         "screen": ("◌", ("yellow",)), "skip": ("▒", ("dim",)), "note": ("·", ("dim",)),
         "wipe": ("⌫", ("magenta",)), "write": ("✎", ("blue",)), "move": ("↔", ("cyan",)),
         "wait": ("⧗", ("dim",))}


def mark(kind: str) -> str:
    sym, styles = MARKS[kind]
    return paint(sym, *styles)


def outcome(glyph: str, name: str) -> str:
    """Colour a cell's verdict by what it means, so a grid can be scanned rather than read."""
    style = {"EXACT": ("green",), "WRONG": ("red", "bold"), "SILENT": ("yellow",),
             "UNGRADED": ("dim",)}.get(name, ())
    return paint("%s %s" % (glyph, name), *style)


def banner(text: str) -> str:
    return paint("══ %s ══" % text, "bold", "magenta")
