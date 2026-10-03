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
from unittest import mock

from benchmatrix import plan as planning, registry as reg, runner
from benchmatrix.stations import Bench
from tests.helpers import make_devices, quiet


class NoRealPauses(unittest.TestCase):
    """⛔ EVERY TEST HERE PATCHES THE PAUSE, AND THE SUITE'S RUNTIME IS WHY IT IS A SEAM AT ALL.
    `_read` waits between repeats (C507). Left alone, a four-repeat test sleeps for real and the
    467-test suite went from 0.2 s to 2.2 s — which is how a fast suite stops being run."""

    def setUp(self):
        self.slept = []
        patch = mock.patch.object(runner, "_sleep", self.slept.append)
        patch.start()
        self.addCleanup(patch.stop)


class RepeatingHoldsTheConditionsFixed(NoRealPauses):

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


class ADisagreementIsNotResolvedByVoting(NoRealPauses):

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


class TheRepeatsAreSpacedBecauseUnspacedTheyResampleOnePhase(NoRealPauses):
    """⛔⛔ C507. Six IDENTICAL reads in one pm3 session returned the decode pattern `.X.XX.` in
    16 of 16 sessions — index 1, 3 and 4 every time and 0, 2 and 5 never — because each read lands
    at its own phase of the emission's ~61-80 ms beat and the cadence is deterministic. A host-side
    pause alone moved both the pattern and the rate (`gproxii` 29.2% → 70.8%).

    ⇒ back-to-back repeats revisit the same phases, so AGREEMENT CAN BE MANUFACTURED BY THE
    SCHEDULE. The flag's whole purpose is that agreement means something, so the pause is not a
    nicety — without it the option reports a tight, confident and wrong answer.
    """

    def _run(self, repeat, jitter=None):
        protos = reg.resolve(["em410x"])
        p = planning.build(protos, ["t55.pm3"], ["rd.pm3"], Bench())
        p.repeat = repeat
        if jitter is not None:
            p.repeat_jitter = jitter
        return runner.run(p, make_devices(), interactive=False, session="S", out=quiet)

    def test_a_single_read_of_a_real_tag_never_waits(self):
        """⚠ THE DEFAULT PATH FOR A TAG MUST BE UNTOUCHED. `repeat` is 1 for every run ever
        banked, and a tag has no beat to decorrelate from, so a pause there would tax every
        station for nothing. (An EMULATED source does wait — see the class below.)"""
        self._run(1)
        self.assertEqual(self.slept, [])

    def test_the_pauses_go_BETWEEN_the_reads_so_n_reads_take_n_minus_one(self):
        """⛔ Not before the first and not after the last: a pause with no read on both sides of
        it decorrelates nothing and still costs the operator time."""
        self._run(4)
        self.assertEqual(len(self.slept), 3)

    def test_every_pause_is_inside_the_configured_span(self):
        self._run(6)
        self.assertTrue(all(0.0 <= d <= runner.REPEAT_JITTER_S for d in self.slept), self.slept)

    def test_the_span_is_bounded_from_BOTH_sides_because_it_is_measured(self):
        """⛔⛔ BOTH BOUNDS, AND THE UPPER ONE IS THE ONE THAT WAS MISSING. The span has to
        exceed what it decorrelates — C486's ~61-80 ms nulls, a 121.6 ms full phase cycle.
        It ALSO has to stay under the gap at which the Chameleon's burst restarts, because a
        FRESH burst does not decode at all: C512 measured `gproxii` at 0% for gaps of 600 and
        900 ms, and C513 put the knee near 160 ms (arrivals per read leaving 0.50).

        ⚠ The first version of this test pinned only the lower bound, and the constant shipped
        at 0.25 — inside the region where the rate is suppressed. A one-sided bound on a
        two-sided constraint is how that got through."""
        self.assertGreater(runner.REPEAT_JITTER_S, 0.080)
        self.assertLessEqual(runner.REPEAT_JITTER_S, 0.160)

    def test_the_pauses_are_not_all_identical(self):
        """⚠ A CONSTANT pause is not a fix — it is a different fixed cadence, which is what
        C507 measured as deterministic in the first place. They must be drawn, not set."""
        self._run(12)
        self.assertGreater(len(set(self.slept)), 1, "a constant pause is just another cadence")

    def test_it_can_be_turned_off_to_reproduce_a_pre_C507_run(self):
        self._run(4, jitter=0.0)
        self.assertEqual(self.slept, [0.0, 0.0, 0.0],
                         "disabled means a zero wait, not a skipped code path")

    def test_turning_it_off_does_not_change_what_is_read(self):
        """⚠ The pause must be the ONLY thing the flag changes."""
        spaced = self._run(4)
        unspaced = self._run(4, jitter=0.0)
        self.assertEqual([c.outcome.value for c in spaced.cells],
                         [c.outcome.value for c in unspaced.cells])


class AnEmulationsFirstReadIsSpacedToo(NoRealPauses):
    """⛔ ARM, THEN READ AFTER A FIXED DELAY, IS A FIXED BEAT PHASE. ChameleonUltra 2026-10-03:
    two builds with the same emission (identical long-capture analysis) read 82-91% and 40-68% at
    a near-fixed cadence, and both ~55% once the reads were randomised. So an emulated source's
    FIRST read is preceded by the same random pause the repeats use; a tag's is not."""

    def _run(self, source, reader, repeat=1):
        protos = reg.resolve(["em410x"])
        p = planning.build(protos, [source], [reader], Bench())
        p.repeat = repeat
        return runner.run(p, make_devices(), interactive=False, session="S", out=quiet)

    def test_an_emulated_single_read_waits_once_inside_the_span(self):
        self._run("emu.cu1", "rd.pm3")
        self.assertGreaterEqual(len(self.slept), 1, "the first read of an emulation must be spaced")
        self.assertTrue(all(0.0 <= d <= runner.REPEAT_JITTER_S for d in self.slept), self.slept)

    def test_each_cell_waits_once_per_read_except_a_tags_first(self):
        """⚠ The plan also reads its calibration row from a real tag, so the count is per cell:
        repeat-1 pauses for every cell, plus one before the first read of each emulated cell."""
        res = self._run("emu.cu1", "rd.pm3", repeat=4)
        sources = [c.source for c in res.cells]
        self.assertTrue(any(s.startswith("emu.") for s in sources), sources)
        self.assertTrue(any(not s.startswith("emu.") for s in sources), sources)
        want = sum(3 + (1 if s.startswith("emu.") else 0) for s in sources)
        self.assertEqual(len(self.slept), want, sources)

