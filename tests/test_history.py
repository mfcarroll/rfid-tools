"""A cell that disagrees with itself across runs, and what may not be claimed from it.

⭐⭐ EVERY OTHER CONTROL IN THIS HARNESS DEFENDS A SINGLE RUN. Calibration licenses a reader, null
sweeps prove the field was quiet, the crowded-stack rule refuses a failure taken beside a bystander
— all of them WITHIN a run. None could tell you that the silence about to be published as a
firmware gap read byte-exact thirty minutes earlier.

⛔ ONE DID. `em410x emu.pm3 → rd.cu1` decoded `EM410X/64: 2244668800` at 11:19 and answered
`LF tag not found` at 11:52, same firmware and same registry entry, and the gap register was about
to write it up as a Proxmark gap.
"""

import json
import os
import tempfile
import unittest

from benchmatrix import grid, history, registry as reg
from benchmatrix.outcomes import Outcome


class _Cell:
    """⚠ `observation` AND `crowding` ARE PART OF THE CONTRACT, not padding. A gap needs evidence
    behind it and must come from an uncrowded stack, so a stub without them would be exercising a
    path the real register never takes."""

    def __init__(self, protocol, source, reader, outcome, observation="present", crowding=()):
        self.protocol, self.source, self.reader = protocol, source, reader
        self.outcome = Outcome(outcome)
        self.observation = observation
        self.crowding = frozenset(crowding)


FW = {"rd.pm3": "pm3-a", "cu1": "cu-a"}


class Fixture(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def earlier(self, session, cells, firmware=None, **over):
        doc = {"session": session, "firmware": FW if firmware is None else firmware,
               "cells": [{"protocol": p, "source": s, "reader": r, "outcome": o}
                         for p, s, r, o in cells]}
        doc.update(over)
        with open(os.path.join(self.dir, "run_%s.json" % session), "w") as fh:
            json.dump(doc, fh)


class ItFindsTheDisagreement(Fixture):

    def test_the_same_cell_grading_two_ways_is_reported(self):
        self.earlier("S0", [("em410x", "emu.pm3", "rd.cu1", "EXACT")])
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        rows = history.disagreements(now, history.load(self.dir, FW, exclude="S1"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:4], ("em410x", "emu.pm3", "rd.cu1", "SILENT"))
        self.assertEqual(rows[0][4][0].session, "S0")

    def test_agreement_is_not_reported(self):
        self.earlier("S0", [("em410x", "emu.pm3", "rd.cu1", "SILENT")])
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW)))

    def test_a_run_of_its_own_is_never_compared_with_itself(self):
        self.earlier("S1", [("em410x", "emu.pm3", "rd.cu1", "EXACT")])
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW, exclude="S1")))


class WhatIsNotEvidence(Fixture):

    def test_a_different_firmware_is_a_claim_about_another_instrument(self):
        """⛔ RULES.md §11. A reflashed device makes the earlier reading a claim about something
        else, not a contradiction of this one — reporting it as instability would flag the harness
        working correctly."""
        self.earlier("S0", [("em410x", "emu.pm3", "rd.cu1", "EXACT")],
                     firmware={"rd.pm3": "pm3-b", "cu1": "cu-a"})
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW)))

    def test_an_aborted_run_is_not_compared(self):
        self.earlier("S0", [("em410x", "emu.pm3", "rd.cu1", "EXACT")], aborted="usb dropped")
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW)))

    def test_ungraded_contradicts_nothing_in_either_direction(self):
        """⚠ UNGRADED means the run COULD NOT JUDGE the cell — no licence, no arm, a crowded stack.
        Counting it as a disagreement would make every unlicensed run poison the next one."""
        self.earlier("S0", [("em410x", "emu.pm3", "rd.cu1", "UNGRADED")])
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW)))
        self.earlier("S2", [("em410x", "emu.pm3", "rd.cu1", "EXACT")])
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "UNGRADED")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW)))

    def test_a_run_with_no_firmware_recorded_is_skipped_not_assumed(self):
        self.earlier("S0", [("em410x", "emu.pm3", "rd.cu1", "EXACT")], firmware={})
        now = [_Cell("em410x", "emu.pm3", "rd.cu1", "SILENT")]
        self.assertFalse(history.disagreements(now, history.load(self.dir, FW)))


class NoFindingIsBuiltOnAnUnstableCell(unittest.TestCase):

    class _Result:
        provenance = "bench"
        def __init__(self, cells, unstable=frozenset()):
            self.cells, self.unstable = cells, unstable

    def _gaps(self, unstable=frozenset()):
        cells = [_Cell("em410x", "emu.cu1", "rd.pm3", "SILENT")]
        return grid._observed_gaps(self._Result(cells, unstable))

    def test_a_stable_silence_still_asserts_its_gap(self):
        """⚠ THE HALF THAT MATTERS. A guard that withheld everything would be no better than the
        register that asserted everything."""
        self.assertTrue(self._gaps(), "a cell nothing contradicts is still evidence")

    def test_and_an_unstable_one_does_not(self):
        self.assertFalse(self._gaps({("em410x", "emu.cu1", "rd.pm3")}))

    def test_the_proxmarks_own_emitter_can_finally_own_a_gap(self):
        """⛔⛔ `emitter_owner` WAS A FOURTH HAND-KEPT COPY OF THE SOURCE LIST and had no `emu.pm3`.
        A cell with no owner falls through every branch, so a failure of the gold emitter was not
        suppressed — it was UNREPRESENTABLE. `emu.pm3` was the one source in the registry that could
        never be the subject of a finding, which is a poor property for the reference instrument."""
        cells = [_Cell("indala", "emu.pm3", "rd.cu1", "SILENT")]
        gaps = grid._observed_gaps(self._Result(cells))
        self.assertTrue(gaps)
        self.assertEqual(gaps[0][0], "Proxmark")


if __name__ == "__main__":
    unittest.main()
