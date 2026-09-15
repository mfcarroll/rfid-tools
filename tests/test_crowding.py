"""The crowded-stack rule and the isolation phase (RULES.md §7).

The asymmetry is the whole point: a parasitic coil cannot manufacture a byte-exact decode of the
credential we armed, so a SUCCESS in a crowded stack is a success. A silence or a wrong decode might
be the crowding, so it is not a verdict — it is screened, and only an isolated re-measurement may
call it SILENT or WRONG.
"""

import unittest

from tests.helpers import answers_all_exact, make_devices, quiet, reg, runner
from benchmatrix import grid, plan as planning
from benchmatrix.outcomes import Outcome
from benchmatrix.stations import Bench


def crowded_run(answers, keys=("em410x", "keri"), sources=("t55.pm3",),
                readers=("rd.pm3", "rd.cu1"), bench=None):
    bench = bench or Bench(tag_count=1)
    protos = reg.resolve(list(keys))
    plan = planning.build(protos, list(sources), list(readers), bench)
    res = runner.run(plan, make_devices(answers=answers), interactive=False, session="S", out=quiet)
    return plan, res, bench, protos


class SuccessSurvivesCrowding(unittest.TestCase):

    def test_an_exact_reading_in_a_crowded_stack_is_a_verdict(self):
        _, res, _, _ = crowded_run(answers_all_exact(reg.resolve(["em410x", "keri"])))
        self.assertTrue(res.cells)
        self.assertTrue(all(c.outcome is Outcome.EXACT for c in res.cells))
        self.assertTrue(any(c.crowding for c in res.cells), "the cycle station IS crowded")
        self.assertEqual(res.to_isolate, [], "nothing failed, so nothing needs isolating")

    def test_a_crowded_exact_still_licenses_its_column(self):
        _, res, _, _ = crowded_run(answers_all_exact(reg.resolve(["em410x", "keri"])))
        self.assertEqual(len(res.licences), 4)          # 2 protocols x 2 readers


class FailureDoesNot(unittest.TestCase):

    def test_a_non_exact_reading_in_a_crowded_stack_is_screened_not_scored(self):
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, _, _ = crowded_run(ans)
        keri = [c for c in res.cells if c.protocol == "keri"]
        self.assertTrue(keri)
        for c in keri:
            self.assertIs(c.outcome, Outcome.UNGRADED, "a screened reading is never SILENT/WRONG")
            self.assertIn("not a verdict until isolated", c.note)
        self.assertEqual({c.protocol for c in res.to_isolate}, {"keri"})

    def test_a_screened_calibration_does_not_claim_the_reader_cannot_judge(self):
        """⛔ Saying so would publish the crowding as a finding about the reader."""
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, _, _ = crowded_run(ans)
        for pair, why in res.refusals.items():
            if pair[0] == "keri":
                self.assertIn("awaits isolation", why)
                self.assertNotIn("cannot judge", why)

    def test_dependents_of_a_screened_calibration_are_still_measured(self):
        """⭐ The reads are hands-off and cost nothing. Skipping them would mean phase 2 rescues the
        calibration only to find the cells it licenses were never read."""
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, _, _ = crowded_run(ans, sources=("t55.pm3", "t55.cu1"))
        keri = {(c.source, c.reader) for c in res.to_isolate if c.protocol == "keri"}
        self.assertEqual(len(keri), 4, "both sources x both readers are queued, not just the gold row")


class TheIsolationPhase(unittest.TestCase):

    def test_isolation_uses_stacks_with_no_bystanders(self):
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, bench, _ = crowded_run(ans)
        p2 = planning.isolate(res.to_isolate, bench)
        for b in p2.blocks:
            for o in b.ops:
                if o.kind == "read":
                    self.assertFalse(o.crowded, "%s is still crowded in phase 2" % b.station.name)

    def test_the_gold_row_is_re_measured_as_a_calibration_row(self):
        """⛔ Rebuilt as an ordinary cell it would look for a licence it is itself meant to issue,
        and every cell in the pair would come back UNGRADED from a run that measured them all."""
        ans = answers_all_exact(reg.resolve(["keri"]))
        ans[("keri", "t5577")] = ""
        _, res, bench, _ = crowded_run(ans, keys=("keri",))
        p2 = planning.isolate(res.to_isolate, bench)
        gold = [c for c in p2.cells if c.source == "t55.pm3"]
        self.assertTrue(gold)
        self.assertTrue(all(c.is_calibration for c in gold))

    def test_a_calibration_row_is_never_isolated_after_what_it_licenses(self):
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, bench, _ = crowded_run(ans, sources=("t55.pm3", "t55.cu1"))
        p2 = planning.isolate(res.to_isolate, bench)
        seen = set()
        for b in p2.blocks:
            for o in b.ops:
                if o.kind == "read" and o.cell is not None:
                    if o.cell.is_calibration:
                        seen.add(o.cell.pair)
                    else:
                        self.assertIn(o.cell.pair, seen,
                                      "%s is isolated before its calibration row" % str(o.cell.key))

    def test_isolation_turns_a_screened_reading_into_a_verdict(self):
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, bench, protos = crowded_run(ans)
        p2 = planning.isolate(res.to_isolate, bench)
        r2 = runner.run(p2, make_devices(answers=ans), interactive=False, session="S", out=quiet,
                        licences=res.licences)
        merged = grid.merge(res, r2)
        keri = [c for c in merged.cells if c.protocol == "keri"]
        self.assertTrue(all("cannot judge" in c.note for c in keri),
                        "an isolated silence IS the finding that the reader cannot judge it")
        self.assertTrue(all(not c.crowding for c in keri), "the screening placeholder is replaced")

    def test_more_tags_make_isolation_cheaper(self):
        ans = answers_all_exact(reg.resolve(reg.TIER0_ORDER))
        for p in reg.TIER0_ORDER:
            ans[(p, "t5577")] = ""
        _, res, _, _ = crowded_run(ans, keys=reg.TIER0_ORDER)
        one = planning.isolate(res.to_isolate, Bench(tag_count=1))
        many = planning.isolate(res.to_isolate, Bench(tag_count=16))
        self.assertLess(many.interventions, one.interventions)

    def test_an_isolated_failure_may_become_a_gap_and_a_screened_one_may_not(self):
        """⛔ A gap is a claim that something does NOT work, and a crowded stack cannot support it."""
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        ans[("keri", "t5577")] = ""
        _, res, bench, protos = crowded_run(ans)
        before = grid.gap_register(res, protos)
        r2 = runner.run(planning.isolate(res.to_isolate, bench), make_devices(answers=ans),
                        interactive=False, session="S", out=quiet, licences=res.licences)
        after = grid.gap_register(grid.merge(res, r2), protos)
        self.assertEqual(len(before), len(after),
                         "an UNGRADED cell is not a gap either way — it is an open question")


if __name__ == "__main__":
    unittest.main()
