"""Drawing a published run's grid again, without touching the bench.

⭐ THE READINGS AND THE RENDERING ARE DIFFERENT THINGS, and only one of them costs bench time. Every
cell is filed with its transcript, so a grid drawn wrongly can be drawn again — and run
20260916_114253 needed exactly that: ten measured cells had no column to appear in, a fault entirely
in the drawing.

⛔ WHICH MAKES THE VERBATIM/REGRADE SPLIT THE WHOLE POINT OF THE MODULE. Redrawing must not quietly
become re-judging; re-judging must not be impossible. Both are here, both say which they are.
"""

import json
import os
import tempfile
import unittest

from benchmatrix import grid, registry as reg, republish


def _doc(cells, **over):
    d = {"session": "S1", "provenance": "bench", "harness": "aaaaaaa",
         "started": "2026-01-01T00:00:00", "finished": "2026-01-01T00:10:00",
         "firmware": {"pm3": "fw-1"}, "bench": {"pad": "pad0", "max_stack": 3, "tags": 1,
                                                "devices": ["pm3", "t5577"]},
         "cells": cells, "licences": [], "refusals": [], "exclusions": [],
         "stations": ["PM3+T55"], "completed_stations": ["PM3+T55"], "void_blocks": [],
         "unparsed": [], "bad_markers": []}
    d.update(over)
    return d


def _cell(key, source, reader, outcome, evidence, note="", **over):
    c = {"protocol": key, "source": source, "reader": reader, "outcome": outcome, "note": note,
         "crowding": [], "isolated": False, "station": "PM3+T55", "carried_from": None,
         "provisional": False, "decoded": None, "evidence": evidence}
    c.update(over)
    return c


class Fixture(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.protos = reg.resolve(["em410x", "viking"])

    def write(self, doc, name="run_S1.json"):
        path = os.path.join(self.dir, name)
        with open(path, "w") as fh:
            json.dump(doc, fh)
        return path

    def exact(self, key, source="t55.pm3", reader="rd.pm3"):
        from tests.helpers import pm3_exact
        return _cell(key, source, reader, "EXACT", pm3_exact(reg.ALL[key]))


class AVerbatimRedrawChangesNoVerdict(Fixture):

    def test_the_outcomes_come_back_exactly_as_filed(self):
        """⛔⛔ THE GUARANTEE THAT MAKES THIS SAFE TO RUN ON ANYTHING. A redraw is for a RENDERING
        fault, and a rendering fix that also moved a cell would be indistinguishable from the
        harness quietly rewriting history. The stored outcome is reproduced even where today's
        registry would grade the same transcript differently."""
        # ⚠ THE FIXTURE ONLY BITES IF TODAY DISAGREES. A stored outcome that today's code would
        # reproduce anyway proves nothing about which mode ran — so this one is a byte-exact
        # transcript filed as SILENT, which no current grading of it could return.
        stored = _cell("viking", "t55.pm3", "rd.pm3", "SILENT",
                       "[+] Viking - Card 1A337102, Raw: 1A337102")
        path = self.write(_doc([stored]))
        verbatim = republish.republish(path, self.protos)
        self.assertEqual([c.outcome.value for c in verbatim.cells], ["SILENT"])
        self.assertEqual(verbatim.mode, "verbatim")
        self.assertFalse(verbatim.moved)

        regraded = republish.republish(path, self.protos, regrade=True)
        self.assertNotEqual([c.outcome.value for c in regraded.cells], ["SILENT"],
                            "the two modes must be able to disagree, or one of them is a no-op")

    def test_and_it_says_on_its_face_that_it_is_a_redraw(self):
        r = republish.republish(self.write(_doc([self.exact("em410x")])), self.protos)
        head = " ".join(republish.banner(r, "bbbbbbb"))
        self.assertIn("REDRAWN", head)
        self.assertIn("exactly as graded at the time", head)

    def test_a_cell_with_no_transcript_is_kept_not_dropped(self):
        """⛔ `resume.rebuild` FILTERS THESE OUT, CORRECTLY, AND THAT IS THE WRONG RULE HERE. A
        reading you cannot re-derive must not be re-attributed to a NEW run — but this run already
        happened, and "not measured: source not armed" has no transcript BECAUSE the arm was
        refused. That absence is the finding. Dropping it leaves a blank where the record has a
        reason, and a blank reads as data that was never taken."""
        doc = _doc([self.exact("em410x"),
                    _cell("viking", "t55.cu1", "rd.pm3", "UNGRADED",
                          None, note="not measured: source not armed")])
        r = republish.republish(self.write(doc), self.protos)
        self.assertEqual(len(r.cells), 2)
        kept = [c for c in r.cells if c.protocol == "viking"][0]
        self.assertEqual(kept.outcome.value, "UNGRADED")
        self.assertIn("source not armed", kept.note)


class ARegradeSaysWhatMoved(Fixture):

    def test_an_outcome_that_changes_is_named(self):
        """⭐ THE POINT OF THE MODE. Correcting a registry expectation otherwise costs a whole bench
        run to find out what it bought; the stored transcripts already answer it."""
        stale = _cell("viking", "t55.pm3", "rd.pm3", "SILENT",
                      "[+] Viking - Card 1A337102, Raw: 1A337102")
        r = republish.republish(self.write(_doc([stale])), self.protos, regrade=True)
        self.assertEqual(r.mode, "regraded")
        self.assertTrue(r.moved, "the fixture must contain a transcript that grades differently")
        key, src, rdr, was, now = r.moved[0]
        self.assertEqual((key, was), ("viking", "SILENT"))
        self.assertIn("moved", " ".join(republish.banner(r, "bbbbbbb")))

    def test_nothing_moving_is_stated_too(self):
        """⚠ A SILENT 'no change' IS INDISTINGUISHABLE FROM A REGRADE THAT DID NOT RUN."""
        r = republish.republish(self.write(_doc([self.exact("em410x")])), self.protos, regrade=True)
        self.assertFalse(r.moved)
        self.assertIn("No outcome moved", " ".join(republish.banner(r, "bbbbbbb")))

    def test_what_cannot_be_regraded_is_declared(self):
        doc = _doc([_cell("em410x", "t55.cu1", "rd.pm3", "UNGRADED", None, note="not armed")])
        r = republish.republish(self.write(doc), self.protos, regrade=True)
        self.assertEqual(len(r.unregradable), 1)
        self.assertIn("no stored transcript", " ".join(republish.banner(r, "bbbbbbb")))


class ItRefusesToPublishAnIncompleteGrid(Fixture):

    def test_a_protocol_subset_that_would_drop_cells_is_refused(self):
        """⛔ THE VERY FAULT THIS COMMAND EXISTS TO FIX. `-p em410x` on a run that graded viking
        would render a grid missing every viking row — measured, and shown nowhere."""
        doc = _doc([self.exact("em410x"), self.exact("viking")])
        with self.assertRaises(republish.RepublishError) as cm:
            republish.republish(self.write(doc), reg.resolve(["em410x"]))
        self.assertIn("viking", str(cm.exception))
        self.assertIn("drop measured cells", str(cm.exception))


class TheRedrawIsRenderable(Fixture):

    def test_it_renders_through_the_real_grid_code(self):
        """⚠ A SHIM THAT ONLY SATISFIES A TEST IS NOT A SHIM. `Republished` stands in for a
        `runner.Result`, so the test that matters is that `grid.render` — including its audit —
        accepts it and puts every cell in a square."""
        doc = _doc([self.exact("em410x"), self.exact("viking"),
                    self.exact("em410x", source="emu.cu1")])
        r = republish.republish(self.write(doc), self.protos)
        md = grid.render(r, self.protos)
        self.assertIn("emu.cu1", md)
        self.assertIn("run S1", md)
        self.assertIn("PM3+T55", md)


if __name__ == "__main__":
    unittest.main()
