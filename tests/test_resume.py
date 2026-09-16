"""Carrying completed stations forward from an earlier run.

⭐ THE STATION IS THE UNIT, AND IT ALREADY WAS. Each takes a null sweep before its routine and
another after, and voids itself if they disagree (RULES.md §3) — so one that finished cleanly
carries its own proof that nothing was emitting around it.

⚠ A USB DROPOUT AT STATION 3 COST TWO COMPLETE STATIONS: 97 byte-exact readings and 49 licences,
every one with the controls it needed, discarded because the sequence containing it stopped.
"""

import json
import os
import tempfile
import unittest

from tests.helpers import reg                                        # noqa: F401
from benchmatrix import learned, registry, resume

FIRMWARE = {"rd.pm3": "os Iceman/x", "cu1": "CU v2.2", "rd.flip": "unknown"}


def _run_file(tmp, **over):
    doc = {"session": "20260916_085441", "harness": "abc1234",
           "bench": {"pad": "pad0"}, "firmware": dict(FIRMWARE),
           "completed_stations": ["PM3+T55+CU1"],
           "cells": [{"protocol": "em410x", "source": "t55.pm3", "reader": "rd.pm3",
                      "outcome": "EXACT", "station": "PM3+T55+CU1", "crowding": [],
                      "evidence": "[+] EM 410x ID 2244668800\n"},
                     {"protocol": "em410x", "source": "t55.pm3", "reader": "rd.cu1",
                      "outcome": "EXACT", "station": "PM3+T55+CU1", "crowding": ["pm3"],
                      "evidence": "[+] EM410X/64: 2244668800\n"},
                     {"protocol": "viking", "source": "t55.pm3", "reader": "rd.pm3",
                      "outcome": "EXACT", "station": "THE-ONE-THAT-ABORTED", "crowding": [],
                      "evidence": "[+] Viking - Card 1A337102\n"}],
           "licences": []}
    doc.update(over)
    path = os.path.join(tmp, "run.json")
    with open(path, "w") as fh:
        json.dump(doc, fh)
    return path


class OnlyTheSameBenchMayBeCarriedForward(unittest.TestCase):
    """⛔⛔ NOT A CACHE OF "ALREADY VERIFIED". A cell is a claim about a FIRMWARE (RULES.md §11), so
    a reading taken against a different build is a claim about something else. A general "skip what
    passed last time" would quietly build a grid whose cells came from different instruments."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.e = resume.load(_run_file(self.tmp))

    def test_the_same_bench_is_allowed(self):
        self.assertEqual(resume.check(self.e, FIRMWARE, "pad0", "abc1234"), [])

    def test_a_reflashed_device_is_refused_by_name(self):
        bad = resume.check(self.e, dict(FIRMWARE, cu1="CU v2.3"), "pad0", "abc1234")
        self.assertTrue(any("cu1" in b and "different firmware" in b for b in bad), bad)

    def test_a_missing_device_is_refused(self):
        """⚠ Readings depend on a device even when it was only the reader on the other side."""
        gone = {k: v for k, v in FIRMWARE.items() if k != "cu1"}
        bad = resume.check(self.e, gone, "pad0", "abc1234")
        self.assertTrue(any("cu1" in b and "not on this bench" in b for b in bad), bad)

    def test_a_moved_pad_is_refused(self):
        """⚠ A licence is pad-scoped because repositioning a reader invalidates it."""
        self.assertTrue(any("pad" in b for b in resume.check(self.e, FIRMWARE, "pad1", "abc1234")))

    def test_a_different_harness_commit_is_said_but_not_refused(self):
        """⛔⛔ THE COMMIT IS A PROXY AND `rebuild` TESTS THE THING ITSELF. Refusing on it made
        `--resume` unusable during exactly the work it was built for: the first carry was refused by
        a commit that had changed because it ADDED the feature. Most commits here never touch
        grading — and one that does shows up in the re-grade, in the cells it actually affected."""
        self.assertEqual(resume.check(self.e, FIRMWARE, "pad0", "deadbee"), [])
        note = resume.harness_note(self.e, "deadbee")
        self.assertIn("abc1234", note)
        self.assertIn("re-graded", note)

    def test_and_says_nothing_when_it_matches(self):
        self.assertEqual(resume.harness_note(self.e, "abc1234"), "")

    def test_a_run_that_completed_nothing_carries_nothing(self):
        e = resume.load(_run_file(self.tmp, completed_stations=[]))
        self.assertTrue(any("completed no station" in b
                            for b in resume.check(e, FIRMWARE, "pad0", "abc1234")))


class OnlyReadingsWithBothNullSweepsBehindThem(unittest.TestCase):
    """⛔ A cell taken at the station that ABORTED has no closing null sweep, so nothing proves the
    bench was still quiet when it was read."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.e = resume.load(_run_file(self.tmp))

    def test_cells_from_the_aborted_station_are_dropped(self):
        got = {(c["protocol"], c["station"]) for c in self.e.usable_cells}
        self.assertIn(("em410x", "PM3+T55+CU1"), got)
        self.assertNotIn(("viking", "THE-ONE-THAT-ABORTED"), got)


class TheEvidenceIsReGradedNotCopied(unittest.TestCase):
    """⭐⭐ A copied outcome is a number with no derivation behind it. Re-grading the stored device
    output under today's registry is the same measurement, checked again — and when one moves, that
    is a finding about the harness, not a detail."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.protos, _ = learned.apply(registry.resolve(None), learned.load(), "T")

    def test_a_carried_reading_grades_and_is_marked(self):
        e = resume.load(_run_file(self.tmp))
        cells, lic, moved = resume.rebuild(e, self.protos, "NEW")
        self.assertEqual(moved, [], "nothing should move on an unchanged harness")
        self.assertTrue(cells)
        for c in cells:
            self.assertEqual(c.carried_from, "20260916_085441")
            self.assertEqual(c.station, "PM3+T55+CU1")

    def test_the_gold_row_licenses_the_others(self):
        """⚠ Gold rows first, exactly as a run does it — a licence must exist before the cells it
        licenses can be graded (RULES.md §1)."""
        e = resume.load(_run_file(self.tmp))
        cells, lic, _ = resume.rebuild(e, self.protos, "NEW")
        self.assertIn(("em410x", "rd.pm3"), lic)
        self.assertTrue(any(c.outcome.value == "EXACT" for c in cells))

    def test_a_reading_that_no_longer_grades_the_same_is_reported(self):
        """⛔ The check that makes carrying safe rather than convenient."""
        e = resume.load(_run_file(self.tmp, cells=[
            {"protocol": "em410x", "source": "t55.pm3", "reader": "rd.pm3", "outcome": "EXACT",
             "station": "PM3+T55+CU1", "crowding": [], "evidence": "[+] EM 410x ID 9999999999\n"}]))
        _, _, moved = resume.rebuild(e, self.protos, "NEW")
        self.assertTrue(moved)
        self.assertIn("re-grades as", moved[0])


if __name__ == "__main__":
    unittest.main()


class ARunFromBeforeTheFeatureCannotBeCarried(unittest.TestCase):
    """⚠ AND SAYING SO BEATS GUESSING. A run published before `--resume` existed records neither
    which stations completed nor which station produced each cell — so a reading with a closing
    null sweep behind it is indistinguishable from one taken at the station that died. The first
    real file anyone tried to resume was exactly that, and the refusal it got blamed the bench
    ("completed no station with both null sweeps agreeing") for a missing field."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_it_is_refused_for_the_right_reason(self):
        path = _run_file(self.tmp)
        doc = json.load(open(path))
        del doc["completed_stations"]
        json.dump(doc, open(path, "w"))
        e = resume.load(path)
        self.assertFalse(e.knows_stations)
        bad = resume.check(e, FIRMWARE, "pad0", "abc1234")
        self.assertTrue(any("before runs recorded which stations completed" in b for b in bad), bad)
        self.assertFalse(any("completed no station" in b for b in bad),
                         "that message blames the bench for a missing field")

    def test_a_run_that_records_them_and_completed_none_says_that_instead(self):
        e = resume.load(_run_file(self.tmp, completed_stations=[]))
        self.assertTrue(e.knows_stations)
        self.assertTrue(any("completed no station" in b
                            for b in resume.check(e, FIRMWARE, "pad0", "abc1234")))
