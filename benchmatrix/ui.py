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
         "wipe": ("⌫", ("magenta",)), "write": ("✎", ("blue",)), "move": ("↔", ("cyan",))}


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
