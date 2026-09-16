"""What the bench believes NOW, amalgamated across runs of different shapes."""

import json
import os
import tempfile
import unittest

from benchmatrix import registry as reg, state

PM3 = "os Iceman/v4.21611"
CU1 = "Chameleon Ultra v2.2"
FLIP = "Flipper 1.3"


class Fixture(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def run_doc(self, session, firmware, cells, **over):
        doc = {"session": session, "started": "2026-09-16T%s:00:00" % session[-2:],
               "firmware": firmware,
               "cells": [{"protocol": p, "source": s, "reader": r, "outcome": o}
                         for p, s, r, o in cells], "exclusions": []}
        doc.update(over)
        with open(os.path.join(self.dir, "run_%s.json" % session), "w") as fh:
            json.dump(doc, fh)


class RunsOfDifferentShapesCombine(Fixture):
    """⛔⛔ THE WHOLE-BENCH RULE IS THE WRONG ONE HERE, and `resume` uses it correctly for a
    different job. A carried station is republished as part of a NEW run, so everything about that
    run must line up. Amalgamating current state under the same rule would refuse to combine a
    `--no-cu2` run with a full one because of a device neither reading was about."""

    def test_a_cell_is_a_claim_about_only_the_devices_in_it(self):
        self.assertEqual(state.devices_in("t55.pm3", "rd.cu1"), {"pm3", "cu1"})
        self.assertEqual(state.devices_in("emu.flip", "rd.pm3"), {"flipper", "pm3"})

    def test_a_run_without_the_flipper_still_combines_with_one_that_had_it(self):
        self.run_doc("10", {"rd.pm3": PM3, "cu1": CU1, "flipper": FLIP},
                     [("em410x", "emu.flip", "rd.pm3", "EXACT")])
        self.run_doc("11", {"rd.pm3": PM3, "cu1": CU1},
                     [("em410x", "t55.pm3", "rd.cu1", "EXACT")])
        now = {"rd.pm3": PM3, "cu1": CU1, "flipper": FLIP}
        got = state.gather(self.dir, now)
        self.assertIn(("em410x", "emu.flip", "rd.pm3"), got)
        self.assertIn(("em410x", "t55.pm3", "rd.cu1"), got)

    def test_reflashing_a_device_retires_only_the_cells_that_depended_on_it(self):
        """⭐ STRICTER THAN THE WHOLE-BENCH RULE, NOT LOOSER. A reading is retired the moment
        anything it actually depended on changed — and kept when something else did."""
        self.run_doc("10", {"rd.pm3": PM3, "cu1": CU1, "flipper": FLIP},
                     [("em410x", "emu.flip", "rd.pm3", "EXACT"),
                      ("em410x", "t55.pm3", "rd.cu1", "EXACT")])
        got = state.gather(self.dir, {"rd.pm3": PM3, "cu1": CU1, "flipper": "Flipper 2.0"})
        self.assertNotIn(("em410x", "emu.flip", "rd.pm3"), got, "the Flipper cell is about a "
                                                                "different instrument now")
        self.assertIn(("em410x", "t55.pm3", "rd.cu1"), got, "the Chameleon cell is untouched")


class WhatMustNotBeAssumed(Fixture):

    def test_two_unknown_firmwares_do_not_compare_equal(self):
        """⛔⛔ CAUGHT ON THE FIRST REAL OUTPUT. A missing entry was filled with `"?"` and the
        tuples compared, so a run that never recorded the Flipper matched a bench with NO FLIPPER
        ATTACHED — and `t55.flip → rd.pm3` appeared in the current state off a device that was not
        in the room. "We do not know what was running" is not "it was the same"."""
        self.run_doc("10", {"rd.pm3": PM3}, [("em410x", "emu.flip", "rd.pm3", "EXACT")])
        self.assertIsNone(state.firmware_for({"flipper", "pm3"}, {"rd.pm3": PM3}))
        self.assertFalse(state.gather(self.dir, {"rd.pm3": PM3}))

    def test_an_aborted_run_contributes_nothing(self):
        self.run_doc("10", {"rd.pm3": PM3, "cu1": CU1},
                     [("em410x", "t55.pm3", "rd.cu1", "EXACT")], aborted="usb dropped")
        self.assertFalse(state.gather(self.dir, {"rd.pm3": PM3, "cu1": CU1}))

    def test_ungraded_is_not_an_answer(self):
        self.run_doc("10", {"rd.pm3": PM3, "cu1": CU1},
                     [("em410x", "t55.pm3", "rd.cu1", "UNGRADED")])
        self.assertFalse(state.gather(self.dir, {"rd.pm3": PM3, "cu1": CU1}))


class DisagreementIsItsOwnAnswer(Fixture):

    def test_the_newest_does_not_win(self):
        """⛔⛔ THE OPERATOR'S OWN CONCERN, POINTING BOTH WAYS. "We don't want to lock in a past bad
        run's results" — and taking the newest instead would lock in a past GOOD one just as
        blindly, turning contradictory evidence into "it works now"."""
        self.run_doc("10", {"rd.pm3": PM3, "cu1": CU1},
                     [("em410x", "emu.pm3", "rd.cu1", "SILENT")])
        self.run_doc("11", {"rd.pm3": PM3, "cu1": CU1},
                     [("em410x", "emu.pm3", "rd.cu1", "EXACT")])
        k = state.gather(self.dir, {"rd.pm3": PM3, "cu1": CU1})[("em410x", "emu.pm3", "rd.cu1")]
        self.assertTrue(k.disputed)
        self.assertEqual(k.verdict, "DISPUTED")
        self.assertEqual(k.latest.session, "11", "the newest is still reported, just not as truth")

    def test_agreement_publishes_the_outcome(self):
        for s in ("10", "11"):
            self.run_doc(s, {"rd.pm3": PM3, "cu1": CU1},
                         [("em410x", "emu.pm3", "rd.cu1", "SILENT")])
        k = state.gather(self.dir, {"rd.pm3": PM3, "cu1": CU1})[("em410x", "emu.pm3", "rd.cu1")]
        self.assertFalse(k.disputed)
        self.assertEqual(k.verdict, "SILENT")


class RefusedIsNotOutstanding(Fixture):
    """⛔ THE FIRST VERSION LUMPED THEM TOGETHER under a sentence explicitly promising it had not,
    listing `covered` cells and every `em410x_electra` row as work nobody had got round to. Whoever
    read that would spend an afternoon on cells the planner refuses and always will."""

    def test_a_refused_cell_is_separated_from_one_nobody_has_measured(self):
        self.run_doc("10", {"rd.pm3": PM3, "cu1": CU1}, [],
                     exclusions=[{"protocol": "viking", "source": "t55.cu1", "reader": "rd.cu1",
                                  "rule": "covered", "why": "answered by two other cells"}])
        got = state.refusals(self.dir)
        self.assertEqual(got[("viking", "t55.cu1", "rd.cu1")], "covered")

    def test_and_the_two_get_different_marks(self):
        """⚠ Printing both as `–` is what sent the reader wrong; they are opposite kinds of empty."""
        self.assertNotEqual(state.GLYPH[""], state.REFUSED_GLYPH)


if __name__ == "__main__":
    unittest.main()
