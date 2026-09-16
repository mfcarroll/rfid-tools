"""What earlier published runs said about the same cells.

⭐⭐ A CELL THAT DISAGREES WITH ITSELF IS THE MOST IMPORTANT THING THIS BENCH CAN FIND, AND UNTIL NOW
IT COULD NOT SEE IT. Every control in this harness defends a single run: calibration licenses a
reader, null sweeps prove the field was quiet, the crowded-stack rule refuses a failure taken beside
a bystander. All of them are WITHIN a run. None of them can tell you that the reading you are about
to publish as a firmware gap read byte-exact thirty minutes ago.

⛔ AND ONE DID. `em410x emu.pm3 -> rd.cu1` decoded `EM410X/64: 2244668800` at 11:19 and answered
`LF tag not found` at 11:52 — same firmware, same registry entry, same command. A single SILENT is
therefore not sufficient evidence of a decoder gap, and the gap register was about to assert one.

⚠ IT IS NOT A VOTE, AND THE MAJORITY DOES NOT WIN. Two readings that disagree are not resolved by
counting them; they are a finding in their own right, and the honest thing is to withhold the gap
and say the cell is unstable. RULES.md §11 still applies — a cell is a claim about a FIRMWARE — so
only runs whose firmware matches device-for-device are compared at all. A reflashed device makes an
earlier reading a claim about a different instrument, not a contradiction of this one.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    """One earlier run's answer for a cell."""
    session: str
    outcome: str


#: ⛔ UNGRADED IS NOT AN ANSWER. It means the run could not judge the cell — no licence, no arm, a
#: crowded stack — so it contradicts nothing and must never be counted as a disagreement.
_NO_ANSWER = "UNGRADED"


def load(runs_dir: str, firmware: dict, exclude: str = "") -> dict:
    """Index earlier runs by cell, keeping only those taken on THIS firmware.

    ⚠ THE FIRMWARE MUST MATCH DEVICE FOR DEVICE, and a run that does not record firmware at all is
    skipped rather than assumed to match. Comparing across a reflash would report the harness
    working correctly as an instability.
    """
    out: dict = {}
    for path in sorted(glob.glob(os.path.join(runs_dir, "*.json"))):
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue                          # an unreadable run is not evidence either way
        session = doc.get("session", "")
        if not session or session == exclude or doc.get("aborted"):
            continue
        was = doc.get("firmware") or {}
        if not was or was != firmware:
            continue
        for c in doc.get("cells", []):
            if c.get("outcome") == _NO_ANSWER:
                continue
            key = (c["protocol"], c["source"], c["reader"])
            out.setdefault(key, []).append(Reading(session, c["outcome"]))
    return out


def disagreements(cells, earlier: dict) -> list:
    """Cells this run grades differently from an earlier run on the same firmware.

    Returns (protocol, source, reader, now, [Reading, ...]), one per cell, ordered as given.
    """
    out = []
    for c in cells:
        if c.outcome.value == _NO_ANSWER:
            continue
        key = (c.protocol, c.source, c.reader)
        other = [r for r in earlier.get(key, ()) if r.outcome != c.outcome.value]
        if other:
            out.append((c.protocol, c.source, c.reader, c.outcome.value, other))
    return out


def unstable(cells, earlier: dict) -> set:
    """The (protocol, source, reader) keys no claim may be built on."""
    return {(p, s, r) for p, s, r, _, _ in disagreements(cells, earlier)}
