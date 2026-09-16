"""The crowded-stack rule and the isolation phase (RULES.md §7).

The asymmetry is the whole point: a parasitic coil cannot manufacture a byte-exact decode of the
credential we armed, so a SUCCESS in a crowded stack is a success. A silence or a wrong decode might
be the crowding, so it is not a verdict — it is screened, and only an isolated re-measurement may
call it SILENT or WRONG.
"""

import unittest

from tests.helpers import EMITTERS, answers_all_exact, make_devices, quiet, reg, runner
from benchmatrix import grid, plan as planning
from benchmatrix import outcomes
from benchmatrix.outcomes import Outcome
from benchmatrix.stations import Bench


def crowded_run(answers, keys=("em410x", "keri"), sources=("t55.pm3",),
                readers=("rd.pm3", "rd.cu1"), bench=None, cu1_answers=None):
    bench = bench or Bench(tag_count=1)
    protos = reg.resolve(list(keys))
    plan = planning.build(protos, list(sources), list(readers), bench)
    res = runner.run(plan, make_devices(answers=answers, cu1_answers=cu1_answers),
                     interactive=False, session="S", out=quiet)
    return plan, res, bench, protos


def cu1_deaf_to(protocol, protos):
    """⚠ A DECODER GAP IN ONE READER, NOT A DEAD TAG. The Proxmark still reads the credential back,
    which proves the write landed — so Chameleon 1's silence is about Chameleon 1. Scripting the tag
    as silent to EVERYONE would instead be an unverified write, which is a different finding and
    reaches the grid by a different path (RULES.md §10)."""
    return {(protocol, e): "" for e in EMITTERS}


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
        protos = reg.resolve(["em410x", "keri"])
        _, res, _, _ = crowded_run(ans, cu1_answers=cu1_deaf_to("keri", protos))
        keri = [c for c in res.cells if c.protocol == "keri" and c.reader == "rd.cu1"]
        self.assertTrue(keri)
        for c in keri:
            self.assertIs(c.outcome, Outcome.UNGRADED, "a screened reading is never SILENT/WRONG")
            self.assertIn("not a verdict until isolated", c.note)
        self.assertEqual({c.protocol for c in res.to_isolate}, {"keri"})

    def test_a_screened_calibration_does_not_claim_the_reader_cannot_judge(self):
        """⛔ Saying so would publish the crowding as a finding about the reader."""
        ans = answers_all_exact(reg.resolve(["em410x", "keri"]))
        protos = reg.resolve(["em410x", "keri"])
        _, res, _, _ = crowded_run(ans, cu1_answers=cu1_deaf_to("keri", protos))
        for pair, why in res.refusals.items():
            if pair == ("keri", "rd.cu1"):
                self.assertIn("awaits isolation", why)
                self.assertNotIn("cannot judge", why)

    def test_dependents_of_a_screened_calibration_are_still_measured(self):
        """⭐ The reads are hands-off and cost nothing. Skipping them would mean phase 2 rescues the
        calibration only to find the cells it licenses were never read."""
        protos = reg.resolve(["em410x", "keri"])
        _, res, _, _ = crowded_run(answers_all_exact(protos), sources=("t55.pm3", "t55.cu1"),
                                   cu1_answers=cu1_deaf_to("keri", protos))
        keri = {(c.source, c.reader) for c in res.to_isolate if c.protocol == "keri"}
        self.assertEqual(keri, {("t55.pm3", "rd.cu1"), ("t55.cu1", "rd.cu1")},
                         "both tag sources are queued for the reader that missed them")


class TheIsolationPhase(unittest.TestCase):

    def test_isolation_uses_stacks_with_no_bystanders(self):
        protos = reg.resolve(["em410x", "keri"])
        ans = answers_all_exact(protos)
        _, res, bench, _ = crowded_run(ans, cu1_answers=cu1_deaf_to("keri", protos))
        p2 = planning.isolate(res.to_isolate, bench)
        for b in p2.blocks:
            for o in b.ops:
                if o.kind == "read":
                    self.assertFalse(o.crowded, "%s is still crowded in phase 2" % b.station.name)

    def test_the_gold_row_is_re_measured_as_a_calibration_row(self):
        """⛔ Rebuilt as an ordinary cell it would look for a licence it is itself meant to issue,
        and every cell in the pair would come back UNGRADED from a run that measured them all."""
        protos = reg.resolve(["keri"])
        ans = answers_all_exact(protos)
        _, res, bench, _ = crowded_run(ans, keys=("keri",),
                                       cu1_answers=cu1_deaf_to("keri", protos))
        p2 = planning.isolate(res.to_isolate, bench)
        gold = [c for c in p2.cells if c.source == "t55.pm3"]
        self.assertTrue(gold)
        self.assertTrue(all(c.is_calibration for c in gold))

    def test_a_calibration_row_is_never_isolated_after_what_it_licenses(self):
        protos = reg.resolve(["em410x", "keri"])
        ans = answers_all_exact(protos)
        _, res, bench, _ = crowded_run(ans, sources=("t55.pm3", "t55.cu1"),
                                       cu1_answers=cu1_deaf_to("keri", protos))
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
        protos = reg.resolve(["em410x", "keri"])
        ans = answers_all_exact(protos)
        deaf = cu1_deaf_to("keri", protos)
        _, res, bench, _ = crowded_run(ans, cu1_answers=deaf)
        p2 = planning.isolate(res.to_isolate, bench)
        r2 = runner.run(p2, make_devices(answers=ans, cu1_answers=deaf), interactive=False,
                        session="S", out=quiet, licences=res.licences)
        merged = grid.merge(res, r2)
        keri = [c for c in merged.cells if c.protocol == "keri" and c.reader == "rd.cu1"]
        self.assertTrue(keri)
        self.assertTrue(all("cannot judge" in c.note for c in keri),
                        "an isolated silence IS the finding that the reader cannot judge it")
        self.assertTrue(all(not c.crowding for c in keri), "the screening placeholder is replaced")

    def test_more_tags_make_isolation_cheaper(self):
        keys = tuple(p.key for p in reg.TIER0.values()
                     if p.can("cu_read") and p.can("pm3_write") and p.expect and p.cu_expect)
        protos = reg.resolve(keys)
        deaf = {(k, e): "" for k in keys for e in EMITTERS}
        _, res, _, _ = crowded_run(answers_all_exact(protos), keys=keys, cu1_answers=deaf)
        one = planning.isolate(res.to_isolate, Bench(tag_count=1))
        many = planning.isolate(res.to_isolate, Bench(tag_count=16))
        self.assertLess(many.interventions, one.interventions)

    def test_an_isolated_failure_may_become_a_gap_and_a_screened_one_may_not(self):
        """⛔ A gap is a claim that something does NOT work, and a crowded stack cannot support it."""
        protos = reg.resolve(["em410x", "keri"])
        ans = answers_all_exact(protos)
        deaf = cu1_deaf_to("keri", protos)
        _, res, bench, _ = crowded_run(ans, cu1_answers=deaf)
        before = grid.gap_register(res, protos)
        r2 = runner.run(planning.isolate(res.to_isolate, bench),
                        make_devices(answers=ans, cu1_answers=deaf),
                        interactive=False, session="S", out=quiet, licences=res.licences)
        after = grid.gap_register(grid.merge(res, r2), protos)
        self.assertEqual(len(before), len(after),
                         "an UNGRADED cell is not a gap either way — it is an open question")


if __name__ == "__main__":
    unittest.main()


class AnUnlicensedReadingIsNotAPlaceholder(unittest.TestCase):
    """⛔⛔ `crowding` IS A FACT ABOUT THE STACK; `provisional` IS A JUDGEMENT ABOUT THE READING.

    Three call sites asked the first and meant the second — the phase-2 work list, the phase-2
    merge, and the grid's ◌ glyph — and every reading taken in a crowded stack answers yes to
    `crowding`, INCLUDING a byte-exact one. On 2026-09-15 that sent a byte-exact `t55.cu1 -> rd.cu1`
    fdxb read back to the bench. It was the only evidence in that run that the Chameleon can see
    fdxb at all; it was re-measured behind a failed park, overwritten with a non-result, and the
    published record went on citing the reading it had just deleted.
    """

    def _unlicensed_exact(self):
        """fdxb from both tag sources, with the Proxmark's write failing to land.

        ⇒ No gold row passes, so every cell is UNGRADED for want of a licence — but the Chameleon's
        own tag still reads back byte-exact, in a crowded stack.
        """
        protos = reg.resolve(["fdxb"])
        plan = planning.build(protos, ["t55.pm3", "t55.cu1"], ["rd.pm3", "rd.cu1"], Bench())
        dev = make_devices()
        dev.pm3.write_works = False
        res = runner.run(plan, dev, interactive=False, session="S", out=quiet)
        return res, [c for c in res.cells if c.source == "t55.cu1" and c.reader == "rd.cu1"][0]

    def test_the_reading_is_exact_and_unlicensed_and_crowded(self):
        """The fixture is only interesting if it really is all three."""
        _, cell = self._unlicensed_exact()
        self.assertIs(cell.outcome, Outcome.UNGRADED, "no gold row passed")
        self.assertIs(cell.observation.outcome_if_licensed, Outcome.EXACT)
        self.assertTrue(cell.crowding, "the cycle station has the Proxmark in it too")

    def test_so_it_is_not_provisional(self):
        _, cell = self._unlicensed_exact()
        self.assertFalse(cell.provisional,
                         "a bystander coil cannot manufacture a byte-exact decode (RULES.md §7)")

    def test_and_is_never_sent_back_to_the_bench(self):
        """⚠ Isolation cannot help: what is missing is a gold row, and no rearrangement supplies
        one. Re-taking it can only lose the reading."""
        res, _ = self._unlicensed_exact()
        self.assertNotIn(("fdxb", "t55.cu1", "rd.cu1"),
                         {(c.protocol, c.source, c.reader) for c in res.to_isolate})

    def test_and_phase_two_may_not_overwrite_it(self):
        """⛔ THE DATA LOSS ITSELF. `merge` replaced any cell carrying `crowding`, so a real
        observation could be replaced by a worse one taken later."""
        res, cell = self._unlicensed_exact()

        class Phase2:                                   # the same cell, re-measured and silent
            cells = [outcomes.grade(
                outcomes.Observation(protocol="fdxb", source="t55.cu1", reader="rd.cu1", text="",
                                     matched=False, decoded=False, marker_fired=False,
                                     summary=()), None, note="nothing read it back")]
            blocks, refusals, finished = [], {}, "later"

        merged = grid.merge(res, Phase2())
        kept = [c for c in merged.cells if c.source == "t55.cu1" and c.reader == "rd.cu1"][0]
        self.assertIsNotNone(kept.observation, "the evidence survives")
        self.assertIs(kept.observation.outcome_if_licensed, Outcome.EXACT)
        self.assertIn("has no licence", kept.note, "still unlicensed — but still a reading")
