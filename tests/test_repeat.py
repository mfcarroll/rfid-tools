"""Reading a cell more than once, under conditions that did not move in between.

⭐⭐ THIS IS THE ONLY WAY TO EARN THE WORD "INTERMITTENT". Comparing across runs catches a cell that
disagrees with itself, but never under controlled conditions — run order, prior device workload and
everything else moved in between. Repeating within one station holds all of it fixed, so a
disagreement means the READING varies, and agreement is worth something.

⛔ AND THE COST IS WHY IT HAD TO BE A FLAG. `em410x emu.pm3 → rd.cu1` needs its calibration row from
a real tag, so answering it once took two stations and four operator interventions; ten answers
meant ten rebuilds. The licence is earned once and the read taken N times.
"""

import unittest

from benchmatrix import plan as planning, registry as reg, runner
from benchmatrix.stations import Bench
from tests.helpers import make_devices, quiet


class RepeatingHoldsTheConditionsFixed(unittest.TestCase):

    def _run(self, repeat, pm3_answers=None):
        protos = reg.resolve(["em410x"])
        p = planning.build(protos, ["t55.pm3"], ["rd.pm3"], Bench())
        p.repeat = repeat
        dev = make_devices(pm3_answers=pm3_answers)
        return runner.run(p, dev, interactive=False, session="S", out=quiet), dev

    def _reads(self, dev):
        # ⚠ NOT EVERY READ IS A CELL. Null sweeps and the write verification go through the same
        # channel, so the absolute count is not the measurement — the DELTA between two runs that
        # differ only in `repeat` is.
        return len([e for e in dev.pm3.log if e[0] == "read"])

    def test_one_read_by_default_so_nothing_changes_for_anyone_else(self):
        res, _ = self._run(1)
        self.assertFalse(res.repeated)

    def test_n_reads_costs_exactly_n_minus_one_extra_per_cell(self):
        _, one = self._run(1)
        _, four = self._run(4)
        cells = 1
        self.assertEqual(self._reads(four) - self._reads(one), 3 * cells,
                         "repeat must cost reads, not stations")

    def test_agreeing_repeats_leave_the_cell_alone(self):
        """⚠ THE HALF THAT MATTERS. A flag that marked everything unstable would be no better than
        no flag: agreement across N reads is the evidence the option exists to produce."""
        res, _ = self._run(4)
        self.assertFalse(res.repeated, "four identical answers are not a disagreement")
        self.assertFalse(getattr(res, "unstable", set()))
        self.assertEqual([c.outcome.value for c in res.cells], ["EXACT"])


class ADisagreementIsNotResolvedByVoting(unittest.TestCase):

    class Flaky:
        """A reader that answers differently on successive reads OF AN ARMED CELL.

        ⛔ IT MUST NOT ANSWER THE NULL SWEEPS. They go through the same channel, and a sweep that
        hears a decode voids the whole block — so the first version of this fixture made every run
        abort before a single cell was measured. Delegating and substituting only where the real
        scripted bench heard something keeps the sweeps honest and the flakiness where it belongs.
        """

        def __init__(self, real, replies):
            self._real, self._replies, self._n = real, replies, 0

        def __getattr__(self, k):
            return getattr(self._real, k)

        def read(self, p):
            heard = self._real.read(p)
            if not heard:
                return heard                         # a null sweep, or nothing armed
            self._n += 1
            return self._replies[min(self._n - 1, len(self._replies) - 1)]

    def _flaky_run(self, replies, repeat=3):
        from tests.helpers import pm3_exact
        protos = reg.resolve(["em410x"])
        p = planning.build(protos, ["t55.pm3"], ["rd.pm3"], Bench())
        p.repeat = repeat
        dev = make_devices()
        dev.pm3 = self.Flaky(dev.pm3, replies)
        return runner.run(p, dev, interactive=False, session="S", out=quiet)

    def test_a_cell_that_varies_is_marked_unstable(self):
        from tests.helpers import pm3_exact
        good = pm3_exact(reg.ALL["em410x"])
        res = self._flaky_run([good, "", good])
        self.assertIn(("em410x", "t55.pm3", "rd.pm3"), res.repeated)
        self.assertIn(("em410x", "t55.pm3", "rd.pm3"), getattr(res, "unstable", set()))

    def test_the_counts_are_recorded_and_are_never_a_vote(self):
        """⛔ 2 EXACT AND 1 SILENT IS NOT "EXACT". The whole rule this project applies to
        cross-run disagreement applies harder here, where the conditions genuinely did not move:
        the counts are evidence about stability, not a poll to be won."""
        from tests.helpers import pm3_exact
        good = pm3_exact(reg.ALL["em410x"])
        res = self._flaky_run([good, good, ""])
        tally = res.repeated[("em410x", "t55.pm3", "rd.pm3")]
        self.assertEqual(tally, {"EXACT": 2, "SILENT": 1})
        self.assertIn(("em410x", "t55.pm3", "rd.pm3"), getattr(res, "unstable", set()),
                      "a 2-1 majority does not make the cell settled")

    def test_the_first_reading_is_still_the_cell(self):
        """⚠ The repeats say whether to TRUST the cell; they do not manufacture a different one."""
        from tests.helpers import pm3_exact
        good = pm3_exact(reg.ALL["em410x"])
        res = self._flaky_run([good, "", ""])
        self.assertEqual([c.outcome.value for c in res.cells], ["EXACT"])


if __name__ == "__main__":
    unittest.main()
