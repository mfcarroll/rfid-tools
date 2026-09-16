"""Carrying completed stations forward from an earlier run.

⭐⭐ THE STATION IS THE UNIT, AND IT ALREADY WAS. Every station takes a null sweep before its
routine and another after, and refuses its own readings if the two disagree (RULES.md §3). That
makes a station that finished with both sweeps agreeing a SELF-CONTAINED measurement — it carries
its own proof that nothing was emitting when it started and nothing was when it ended. A run is a
sequence of those; it is not itself the unit of evidence.

⛔ SO AN ABORT SHOULD NOT COST THE STATIONS THAT FINISHED. A USB dropout at station 3 threw away two
complete stations, 97 byte-exact readings and 49 licences — data with every control it needed,
discarded because the sequence containing it stopped early. The readings were filed; the grid was
not, which is correct for a claim and wrong for an afternoon.

⛔⛔ AND THIS IS NOT A CACHE OF "ALREADY VERIFIED". The distinction matters and it is the whole
design of this module. A resumed station is carried forward only when the bench it was measured on
is demonstrably the SAME bench: same firmware on every device, same pad, same harness commit. Change
any of those and the earlier reading is a claim about something else — a cell is a claim about a
firmware, not a device (RULES.md §11) — so it is refused and re-measured. A general "skip what
passed last time" would quietly build a grid whose cells came from different instruments.

⚠ AND THE GRID SAYS WHICH IS WHICH. Every carried cell is marked, and the published run names the
session it came from. A composite that does not admit to being one is worse than re-measuring.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


class ResumeRefused(Exception):
    """The earlier run cannot be carried forward, and why."""


@dataclass(frozen=True)
class Earlier:
    """What a previous run left behind that a new one may use."""

    session: str
    path: str
    firmware: dict
    pad: str
    harness: str
    stations: tuple           # stations that completed with both null sweeps agreeing
    cells: tuple              # raw cell dicts, as published
    licences: tuple

    @property
    def usable_cells(self) -> tuple:
        """⛔ ONLY CELLS FROM A COMPLETED STATION. A cell taken at the station that aborted has no
        closing null sweep, so nothing proves the bench was still quiet when it was read."""
        return tuple(c for c in self.cells if c.get("station") in self.stations
                     or c.get("station") is None)


def load(path: str) -> Earlier:
    """Read a published run. ⚠ Accepts the `.json`, with or without the extension."""
    for cand in (path, path + ".json", os.path.join("runs", path),
                 os.path.join("runs", path + ".json"),
                 os.path.join("runs", "run_%s.json" % path),
                 os.path.join("runs", "run_%s_ABORTED.json" % path)):
        if os.path.isfile(cand):
            with open(cand) as fh:
                got = json.load(fh)
            return Earlier(session=got.get("session", "?"), path=cand,
                           firmware=got.get("firmware", {}), pad=got.get("bench", {}).get("pad", ""),
                           harness=got.get("harness", ""),
                           stations=tuple(got.get("completed_stations", [])),
                           cells=tuple(got.get("cells", [])),
                           licences=tuple(got.get("licences", [])))
    raise ResumeRefused("no published run found at %r — looked in ./ and ./runs/" % path)


def check(earlier: Earlier, firmware: dict, pad: str, harness: str) -> list[str]:
    """Why this run may not carry that one forward. Empty means it may.

    ⛔⛔ THE FIRMWARE HAS TO MATCH, DEVICE BY DEVICE. A cell is a claim about a firmware; carrying a
    reading taken against a different build and publishing it beside today's is exactly the
    misattribution `provenance` exists to prevent. The Chameleons on this bench are deliberately
    flashed differently at times — that is half the reason there are two.

    ⚠ THE HARNESS COMMIT COUNTS TOO, and it is the one people forget. Every reading in this project
    has at some point been changed by a harness fix: a decode marker corrected, an expectation
    replaced, a parser that was discarding real decodes. A cell measured by different code is not
    the same measurement, however still the bench was.
    """
    bad = []
    if not earlier.stations:
        bad.append("%s completed no station with both null sweeps agreeing — there is nothing in "
                   "it that carries its own controls" % earlier.session)
    for dev, was in sorted(earlier.firmware.items()):
        now = firmware.get(dev)
        if now is None:
            bad.append("%s is not on this bench, and %s has readings that depend on it"
                       % (dev, earlier.session))
        elif now != was:
            bad.append("%s was running %r and is now running %r — every cell about it is a claim "
                       "about a different firmware (RULES.md §11)" % (dev, was, now))
    if earlier.pad != pad:
        bad.append("that run was taken on pad %r and this one is on %r; a licence is pad-scoped "
                   "because moving a reader invalidates it" % (earlier.pad, pad))
    if earlier.harness != harness:
        bad.append("that run was measured by harness %s and this is %s — a decode marker or an "
                   "expectation may have changed under it, which has happened repeatedly"
                   % (earlier.harness or "?", harness or "?"))
    return bad


def rebuild(earlier: Earlier, protocols, session: str):
    """Turn a carried run's stored readings back into graded cells, and say if any moved.

    ⭐⭐ THE STORED EVIDENCE IS RE-GRADED, NOT COPIED. Every cell is rebuilt by putting the recorded
    device output back through `observe` and `grade` under TODAY's registry and TODAY's licences. A
    copied outcome would be a number with no derivation behind it; a re-graded one is the same
    measurement, checked again.

    ⛔ AND A DISAGREEMENT IS A FINDING, NOT A DETAIL. `resume.check` already refuses a carry when the
    harness commit differs — so if an outcome nonetheless changes, something is wrong that neither
    the firmware nor the commit accounted for, and the caller is told which cells and how.

    ⚠ GOLD ROWS FIRST, exactly as a run does it, because a licence has to exist before the cells it
    licenses can be graded (RULES.md §1).
    """
    from .outcomes import Calibration, CalibrationRefused, Outcome, grade, observe
    from .stations import GOLD_SOURCES
    table = {p.key: p for p in protocols}
    rows = [c for c in earlier.usable_cells if c.get("evidence") and c["protocol"] in table]
    rows.sort(key=lambda c: c["source"] not in GOLD_SOURCES)

    licences, cells, moved = {}, [], []
    for c in rows:
        p = table[c["protocol"]]
        try:
            obs = observe(p.key, c["source"], c["reader"], c["evidence"],
                          p.expect_for(c["reader"]) or "", p.marker_for(c["reader"]) or "",
                          session=earlier.session, pad=earlier.pad)
        except Exception:                                    # noqa: BLE001 - never lose the run
            continue
        pair = (p.key, c["reader"])
        if c["source"] in GOLD_SOURCES and obs.outcome_if_licensed is Outcome.EXACT:
            try:
                licences[pair] = Calibration.from_row(obs, GOLD_SOURCES)
            except CalibrationRefused:
                pass
        cell = grade(obs, licences.get(pair), crowding=frozenset(c.get("crowding") or ()))
        cell = _stamp(cell, c.get("station") or "", earlier.session)
        if cell.outcome.value != c["outcome"]:
            moved.append("%s / %s / %s was %s and re-grades as %s"
                         % (p.key, c["source"], c["reader"], c["outcome"], cell.outcome.value))
        cells.append(cell)
    return cells, licences, moved


def _stamp(cell, station: str, from_session: str):
    import dataclasses
    return dataclasses.replace(cell, station=station, carried_from=from_session)
