"""The published grid must show every cell that was measured.

⛔⛔ THE GRID IS THE CLAIM. Everything else in this harness exists to make a cell trustworthy —
calibration, null sweeps, crowding, provenance — and all of it is spent the moment the table the
operator reads disagrees with the readings behind it. There are three honest states for a square:
measured (a glyph), refused (`– refsd`, with a reason below) and not reached (blank). A fourth one
appeared in run 20260916_114253: MEASURED AND RENDERED NOWHERE.
"""

import unittest

from benchmatrix import grid, plan as planning, registry as reg, runner
from benchmatrix.stations import Bench, EMULATED_SOURCES, READER_NOTE, REAL_SOURCES
from tests.helpers import make_devices, quiet


class EveryMeasuredCellIsShown(unittest.TestCase):

    def _run(self, keys, sources, readers):
        protos = reg.resolve(list(keys))
        plan = planning.build(protos, list(sources), list(readers), Bench())
        res = runner.run(plan, make_devices(), interactive=False, session="S", out=quiet)
        return grid.render(res, protos), res

    def test_the_proxmarks_emulation_gets_a_column(self):
        """⛔⛔ THE COLUMN THAT WENT MISSING. `SOURCE_ORDER` was a hand-kept fourth copy of the
        source list and `emu.pm3` was never added when the Proxmark became an emitter. The filter
        that builds the header keeps only sources IT knows, so ten measured `emu.pm3 → rd.cu1`
        readings were dropped from the table in silence — `rd.cu1` tallied 26 EXACT and displayed
        17, and the operator read the gap as the Chameleon failing to read. The ten were the very
        readings proving the emitter fixes had worked.

        ⚠ AND THE COMMENT WARNING ABOUT THIS ALREADY EXISTED, on `plan.EMULATED_ORDER`: a new
        emitter "cannot be added to one and forgotten in the other". It was added to that one.
        """
        md, res = self._run(["em410x"], ["emu.pm3"], ["rd.cu1"])
        measured = [c for c in res.cells if c.source == "emu.pm3" and c.reader == "rd.cu1"]
        self.assertTrue(measured, "the fixture only bites if the cell is really measured")
        header = [l for l in md.splitlines() if l.startswith("| protocol")]
        self.assertTrue(header, "there is a table at all")
        self.assertTrue(any("emu.pm3" in l for l in header),
                        "emu.pm3 was measured and has no column: %s" % header)

    def test_a_cell_with_nowhere_to_go_is_an_error_not_a_quiet_drop(self):
        """⭐ THE AXIS LISTS ARE NOT THE TEST, THE CELLS ARE. An assertion on `SOURCE_ORDER` proves
        it agrees with `stations.py` and would still have missed a source absent from both."""
        _, res = self._run(["em410x"], ["t55.pm3"], ["rd.pm3"])
        with self.assertRaises(grid.GridError) as cm:
            grid._audit(res.cells, ["emu.cu2"], ["rd.pm3"], reg.resolve(["em410x"]))
        self.assertIn("contradicts its own totals", str(cm.exception))

    def test_the_tally_and_the_table_count_the_same_cells(self):
        """⚠ THE SYMPTOM THE OPERATOR SAW. The tallies are computed from the cells and the table
        from the axis lists, so the two can only disagree when a cell has no square."""
        md, res = self._run(["em410x", "viking"], ["t55.pm3", "emu.pm3"], ["rd.pm3", "rd.cu1"])
        for rdr in ("rd.pm3", "rd.cu1"):
            shown = sum(1 for c in res.cells if c.reader == rdr
                        and c.source in [s for s in grid.SOURCE_ORDER
                                         if any(x.source == s for x in res.cells)])
            self.assertEqual(shown, sum(1 for c in res.cells if c.reader == rdr), rdr)


class TheAxesAreDerivedNotRemembered(unittest.TestCase):

    def test_source_order_covers_every_source_a_run_can_produce(self):
        self.assertEqual(set(grid.SOURCE_ORDER), REAL_SOURCES | EMULATED_SOURCES)

    def test_reader_order_covers_every_reader(self):
        """⚠ The same shape of bug one axis over: a reader missing here gets no table at all."""
        self.assertEqual(set(grid.READER_ORDER), set(READER_NOTE))


if __name__ == "__main__":
    unittest.main()
