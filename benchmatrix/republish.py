"""Render a published run's markdown again, from its own JSON.

⭐ THE JSON IS THE RECORD AND THE MARKDOWN IS A VIEW OF IT. Every reading a run took is filed with
its evidence, its crowding, its station and its licence, so the grid can always be drawn again —
and a run that took forty minutes of somebody's hands should never have to be repeated because the
code that DREW it was wrong. Run 20260916_114253 was: ten measured cells had no column to appear
in, and re-running the bench to fix a missing table header would have been an absurd price.

⛔⛔ AND THE TWO REASONS TO REDRAW ARE NOT THE SAME THING, SO THEY ARE NOT THE SAME COMMAND.

  `verbatim` (the default) republishes the outcomes exactly as they were graded. It fixes a
  RENDERING fault and nothing else: no cell changes, and the file becomes what should have been
  written at the time.

  `--regrade` puts every stored transcript back through TODAY's registry and TODAY's matcher and
  grades it again. That answers a different question — "what would this run say now?" — and it is
  the honest way to see what a registry correction did, because the alternative is editing an
  expectation and re-running the bench to find out. Every outcome that MOVES is named.

⚠ CONFLATING THEM WOULD BE THE WORST OPTION AVAILABLE. A file that silently re-grades looks like
the original measurement and is not; a file that can only ever be verbatim cannot show what a
correction bought. The published markdown says which of the two it is, in its own first lines.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from . import registry as reg
from .outcomes import (Calibration, CalibrationRefused, Cell, Outcome, grade, observe,
                       unaccounted)
from .plan import Exclusion
from .resume import load as load_run
from .stations import Bench, GOLD_SOURCES


class RepublishError(Exception):
    """The record cannot be drawn again, and why."""


@dataclasses.dataclass
class _Block:
    """Just enough of a run block for the grid's station line and its void section."""
    block: object
    void_why: str = ""


@dataclasses.dataclass
class _Station:
    name: str


@dataclasses.dataclass
class _HasStation:
    station: _Station


@dataclasses.dataclass
class _Plan:
    bench: Bench
    exclusions: list


@dataclasses.dataclass
class Republished:
    """A stand-in for `runner.Result`, carrying exactly what `grid.render` reads.

    ⚠ NOT A `Result`. A `Result` is something a bench produced; this is something a file said. They
    render the same and they must never be confusable in the other direction — nothing here can be
    fed back to a runner, and `mode` is on the face of it.
    """

    session: str
    provenance: str
    firmware: dict
    harness: str
    started: str
    finished: str
    aborted: str
    plan: _Plan
    cells: list
    licences: dict
    refusals: dict
    blocks: list
    void_blocks: list
    carried_from: str
    unparsed: dict
    bad_markers: dict
    #: Filled in by the caller from `history`: cells an earlier run on this firmware graded
    #: differently, and the keys no finding may be built on. ⚠ Supplied rather than computed here,
    #: so a redraw and a live run are judged by the same code.
    disagreements: tuple = ()
    unstable: frozenset = frozenset()
    mode: str = "verbatim"
    #: Cells whose outcome changed under today's code. Empty in verbatim mode by construction.
    moved: tuple = ()
    #: Cells with no stored transcript, which `--regrade` cannot re-derive and keeps as filed.
    unregradable: tuple = ()


def republish(path: str, protocols: list[reg.Protocol], regrade: bool = False) -> Republished:
    """Rebuild a renderable run from `runs/<something>.json`."""
    earlier = load_run(path)
    doc = _raw(earlier.path)
    table = {p.key: p for p in protocols}
    rows = [c for c in doc.get("cells", []) if c["protocol"] in table]
    missing = sorted({c["protocol"] for c in doc.get("cells", []) if c["protocol"] not in table})
    if missing:
        raise RepublishError(
            "the run graded %s and the protocol list given here does not include %s. Republishing "
            "a subset would drop measured cells from the grid, which is the fault this command was "
            "written to fix." % (", ".join(missing[:4]), "them" if len(missing) > 1 else "it"))

    cells, licences, moved, unregradable, odd = _cells(rows, table, doc, earlier, regrade)
    bench = doc.get("bench", {})
    return Republished(
        session=doc.get("session", "?"), provenance=doc.get("provenance", "bench"),
        firmware=doc.get("firmware", {}), harness=doc.get("harness", ""),
        started=doc.get("started", ""), finished=doc.get("finished", ""),
        aborted=doc.get("aborted") or "",
        plan=_Plan(bench=Bench(pad=bench.get("pad", "pad0"),
                               max_stack=bench.get("max_stack", 3),
                               tag_count=bench.get("tags", 1),
                               has=frozenset(bench.get("devices", []))),
                   exclusions=[Exclusion(protocol=e["protocol"], source=e["source"],
                                         reader=e["reader"], rule=e["rule"], why=e["why"])
                               for e in doc.get("exclusions", [])]),
        cells=cells, licences=licences,
        refusals={(r["protocol"], r["reader"]): r["why"] for r in doc.get("refusals", [])},
        blocks=[_Block(_HasStation(_Station(n))) for n in doc.get("stations", [])],
        void_blocks=[_Block(_HasStation(_Station(v["station"])), v["why"])
                     for v in doc.get("void_blocks", [])],
        carried_from=next((c["carried_from"] for c in doc.get("cells", [])
                           if c.get("carried_from")), ""),
        # ⛔ REGRADING HAS TO REDO THE CONTROLS TOO. "Silences that may be OURS" is a claim about
        # today's registry, not about the reading — copying the stored list into a regraded file
        # would republish a suspicion that today's code no longer holds, which is precisely the
        # kind of stale claim this mode exists to clear. Verbatim keeps what was filed, because
        # verbatim keeps everything that was filed.
        unparsed=odd if regrade else {(u["protocol"], u["reader"]): tuple(u["printed"])
                                      for u in doc.get("unparsed", [])},
        bad_markers={(b["protocol"], b["reader"]): b["observed"]
                     for b in doc.get("bad_markers", [])},
        mode="regraded" if regrade else "verbatim",
        moved=tuple(moved), unregradable=tuple(unregradable))


def _cells(rows, table, doc, earlier, regrade):
    """⛔ A CELL WITH NO TRANSCRIPT IS KEPT, NOT DROPPED. `resume.rebuild` filters to cells that have
    evidence, which is right for CARRYING a measurement forward — a reading you cannot re-derive is
    not one you may re-attribute to a new run. It is wrong here: this run already happened, and a
    cell recorded as "not measured: source not armed" has no transcript BECAUSE the source refused
    to arm, which is itself the finding. Dropping it would leave a blank where the record has a
    reason, and blanks are the one thing the grid must not invent.
    """
    licences, cells, moved, unregradable, odd = {}, [], [], [], {}
    ordered = sorted(rows, key=lambda c: c["source"] not in GOLD_SOURCES)
    for c in ordered:
        p = table[c["protocol"]]
        stored = Outcome(c["outcome"])
        obs = None
        if c.get("evidence") is not None:
            try:
                obs = observe(p.key, c["source"], c["reader"], c["evidence"],
                              p.expect_for(c["reader"]) or "", p.marker_for(c["reader"]) or "",
                              session=doc.get("session", ""), pad=earlier.pad)
            except Exception as e:                            # noqa: BLE001
                raise RepublishError("%s / %s / %s cannot be re-read from its own transcript: %s"
                                     % (p.key, c["source"], c["reader"], e)) from e
        pair = (p.key, c["reader"])
        if obs is not None and c["source"] in GOLD_SOURCES and obs.outcome_if_licensed is Outcome.EXACT:
            try:
                licences[pair] = Calibration.from_row(obs, GOLD_SOURCES)
            except CalibrationRefused:
                pass
        if regrade and obs is not None and not (obs.decoded or obs.matched):
            said = unaccounted(obs.text, obs.decode_marker or "")
            if said and pair not in odd:
                odd[pair] = said
        crowding = frozenset(c.get("crowding") or ())
        if regrade and obs is not None:
            cell = grade(obs, licences.get(pair), crowding=crowding)
            if cell.outcome is not stored:
                moved.append((p.key, c["source"], c["reader"], stored.value, cell.outcome.value))
        else:
            if regrade:
                unregradable.append((p.key, c["source"], c["reader"]))
            # ⚠ THE FILED OUTCOME AND NOTE, VERBATIM. `observation` is attached where there is one
            # so `provisional` and the gap register still work off the real transcript — but it is
            # never allowed to change the verdict, which is the whole meaning of this mode.
            cell = Cell(protocol=p.key, source=c["source"], reader=c["reader"],
                        outcome=stored, observation=obs, note=c.get("note", ""),
                        crowding=crowding)
        cells.append(dataclasses.replace(cell, isolated=bool(c.get("isolated")),
                                         station=c.get("station") or "",
                                         carried_from=c.get("carried_from") or ""))
    return cells, licences, moved, unregradable, odd


def banner(r: Republished, harness_now: str) -> list[str]:
    """What the republished file must admit about itself, before anything else in it."""
    out = ["> ⟲ **REDRAWN from `runs/run_%s.json`** — the bench was not touched." % r.session]
    if r.mode == "regraded":
        out.append("> Every reading was put back through the registry at `%s` and graded again; "
                   "it was measured under `%s`. %s"
                   % (harness_now or "?", r.harness or "?",
                      "**%d outcome(s) moved**, listed below." % len(r.moved) if r.moved
                      else "No outcome moved."))
        for k, s, rd, was, now in r.moved:
            out.append(">   · `%s` %s → %s: **%s** was **%s**" % (k, s, rd, now, was))
        if r.unregradable:
            out.append("> ⚠ %d cell(s) have no stored transcript — an arm that was refused leaves "
                       "nothing to re-read — and are shown exactly as filed."
                       % len(r.unregradable))
    else:
        out.append("> Outcomes are **exactly as graded at the time**; only the rendering is today's."
                   " Pass `--regrade` to re-derive them from the stored transcripts instead.")
    out.append("")
    return out


def _raw(path: str) -> dict:
    import json
    with open(path) as fh:
        return json.load(fh)
