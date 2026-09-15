"""⭐⭐ THE CENTRAL CLAIM: a grid cannot be scored without a passing calibration row.

README.md: "No calibration row ⇒ no verdict. Not a weaker verdict — the harness prints UNGRADED and
refuses to score the cell." Everything else in this project is scaffolding around that sentence, so
it is tested from four directions: the type cannot be forged, the grader honours it, the planner
guarantees it, and the CLI offers no way around it.
"""

import unittest

from tests.helpers import (answers_all_exact, answers_silent, make_devices, pm3_exact,
                           pm3_wrong, reg, runner, tiny_plan)
from benchmatrix.cli import build_parser
from benchmatrix.outcomes import Calibration, CalibrationRefused, Outcome, grade, observe
from benchmatrix.topology import REAL_SOURCES

P = reg.TIER0["em410x"]


def obs(source="t55.pm3", text=None, protocol="em410x", reader="rd.pm3", session="S", pad="p"):
    p = reg.TIER0[protocol]
    return observe(protocol, source, reader, pm3_exact(p) if text is None else text,
                   p.expect, p.pm3_decode_marker, session=session, pad=pad)


class TheLicenceCannotBeForged(unittest.TestCase):

    def test_bare_constructor_is_refused(self):
        """⛔ The one thing that would make every other guard cosmetic."""
        with self.assertRaises(CalibrationRefused):
            Calibration(protocol="em410x", reader="rd.pm3", session="S", pad="p",
                        source="t55.pm3", evidence="")

    def test_vouched_flag_cannot_be_passed_by_hand(self):
        # Even naming the private field, the only supported path stays from_row — this test exists
        # so that if someone later relaxes __post_init__, it fails loudly rather than silently.
        with self.assertRaises(CalibrationRefused):
            Calibration("em410x", "rd.pm3", "S", "p", "t55.pm3", "")

    def test_an_emulation_cannot_license_itself(self):
        """The calibration rule in one line: an emulate column graded with no real-tag row in it."""
        for source in ("emu.cu1", "emu.cu2", "emu.flip", "t55.flip"):
            with self.subTest(source=source):
                with self.assertRaises(CalibrationRefused) as cm:
                    Calibration.from_row(obs(source=source), REAL_SOURCES)
                self.assertIn("not a real-tag source", str(cm.exception))

    def test_a_silent_row_reports_the_reader_cannot_judge(self):
        with self.assertRaises(CalibrationRefused) as cm:
            Calibration.from_row(obs(text=""), REAL_SOURCES)
        self.assertIn("cannot judge", str(cm.exception))
        self.assertIn("only finding", str(cm.exception))

    def test_a_wrong_row_is_a_registry_fault_not_a_deaf_reader(self):
        """⚠ The two failures are different and must not be reported as the same thing."""
        with self.assertRaises(CalibrationRefused) as cm:
            Calibration.from_row(obs(text=pm3_wrong(P)), REAL_SOURCES)
        self.assertIn("REGISTRY/WRITE fault", str(cm.exception))
        self.assertNotIn("cannot judge", str(cm.exception))

    def test_an_exact_real_tag_row_is_accepted(self):
        lic = Calibration.from_row(obs(), REAL_SOURCES)
        self.assertEqual((lic.protocol, lic.reader, lic.source), ("em410x", "rd.pm3", "t55.pm3"))


class TheGraderHonoursIt(unittest.TestCase):

    def test_no_licence_means_ungraded_even_when_byte_exact(self):
        """⛔⛔ The tempting exception. A byte-exact hit proves the reader was listening for THAT
        cell and nothing else; the moment it is allowed through, licensed and unlicensed rows are
        back in the same grid with no way to tell them apart."""
        cell = grade(obs(source="emu.cu1"), None)
        self.assertIs(cell.outcome, Outcome.UNGRADED)
        self.assertTrue(cell.observation.matched, "the read really was byte-exact")

    def test_a_licence_for_a_different_pair_does_not_carry(self):
        lic = Calibration.from_row(obs(), REAL_SOURCES)
        for kw in ({"protocol": "viking"}, {"reader": "rd.flip"},
                   {"session": "OTHER"}, {"pad": "OTHER"}):
            with self.subTest(**kw):
                self.assertIs(grade(obs(source="emu.cu1", **kw), lic).outcome, Outcome.UNGRADED)

    def test_a_matching_licence_lets_the_three_real_outcomes_through(self):
        lic = Calibration.from_row(obs(), REAL_SOURCES)
        self.assertIs(grade(obs(source="emu.cu1"), lic).outcome, Outcome.EXACT)
        self.assertIs(grade(obs(source="emu.cu1", text=pm3_wrong(P)), lic).outcome, Outcome.WRONG)
        self.assertIs(grade(obs(source="emu.cu1", text=""), lic).outcome, Outcome.SILENT)


class ThePlannerGuaranteesIt(unittest.TestCase):

    def test_every_pair_in_any_plan_has_a_calibration_row(self):
        from benchmatrix.topology import READERS, SOURCES
        for reader in READERS:
            for source in SOURCES:
                with self.subTest(source=source, reader=reader):
                    plan = tiny_plan(keys=reg.TIER0_ORDER, sources=(source,), readers=(reader,))
                    self.assertEqual(plan.audit(), [], "audit must be clean for every request")

    def test_a_pair_whose_licence_is_refused_is_dropped_entirely(self):
        """Not run and marked UNGRADED sixteen times — removed, with the reason published.

        ⚠ THE REASON IS THE CELL'S OWN, NOT "no-calibration". Every refusal rule in force today
        applies to a (protocol, reader) pair regardless of source, so a cell whose licence is
        refused is almost always refused for the same reason itself — and that reason is the useful
        one, because it says what to fix. `no-calibration` is the fallback for a rule that refuses
        only the licensing source; none exists yet, which is why nothing here asserts it.
        """
        plan = tiny_plan(keys=("pac",), sources=("emu.cu1",), readers=("rd.flip",))
        self.assertEqual(plan.cells, [])
        self.assertTrue(plan.exclusions)
        self.assertEqual({e.rule for e in plan.exclusions}, {"no-expectation"})


class TheCliOffersNoWayAround(unittest.TestCase):

    def test_no_flag_disables_calibration(self):
        """RULES.md §1: `--no-calibration` must not exist as a flag.

        ⚠ CHECKED AGAINST THE PARSER'S ACTIONS, NOT ITS HELP TEXT. The epilog says the words "there
        is no --no-calibration" on purpose, and a substring search over the help would both match
        that sentence and miss a flag added to a subcommand.
        """
        banned = {"--no-calibration", "--skip-calibration", "--force", "--assume",
                  "--uncalibrated", "--no-control", "--trust"}
        found = set()

        def walk(parser):
            for action in parser._actions:
                found.update(action.option_strings)
                choices = getattr(action, "choices", None)
                for sub in (choices.values() if isinstance(choices, dict) else ()):
                    if hasattr(sub, "_actions"):
                        walk(sub)

        walk(build_parser())
        self.assertEqual(found & banned, set(), "a calibration bypass flag exists")

    def test_an_empty_bench_aborts_rather_than_grading(self):
        """⚠ THE CORRECT OUTPUT FOR AN EMPTY BENCH IS NO GRID AT ALL.

        The identity check is reached before any cell is measured, nothing answers the probe, and
        the run stops there — which is stronger than grading every cell UNGRADED, because a bench
        that cannot even say which device is on it has not begun to measure anything.
        """
        plan = tiny_plan(keys=("em410x", "viking"), sources=("t55.pm3", "emu.cu1"))
        devices = make_devices()
        for cham in (devices.cu1, devices.cu2):
            cham.arm = lambda p, _c=cham: None          # present but emitting nothing
        with self.assertRaises(runner.RunAborted) as cm:
            runner.run(plan, devices, interactive=False, session="S", out=lambda *a: None)
        self.assertIn("NOTHING ANSWERED", str(cm.exception))

    def test_a_reader_that_hears_nothing_grades_every_cell_ungraded(self):
        """The other empty case: the bench is arranged correctly, and no decoder ever fires."""
        plan = tiny_plan(keys=("em410x", "viking"), sources=("t55.pm3", "emu.cu1"))
        protos = reg.resolve(["em410x", "viking"])
        deaf = answers_silent(protos)
        res = runner.run(plan, make_devices(pm3_answers=deaf), interactive=False,
                         session="S", out=lambda *a: None)
        self.assertTrue(res.cells)
        self.assertTrue(all(c.outcome is Outcome.UNGRADED for c in res.cells))
        self.assertEqual(res.licences, {})

    def test_a_good_run_grades_the_emulated_rows_only_because_the_control_passed(self):
        protos = reg.resolve(["em410x", "viking"])
        plan = tiny_plan(keys=("em410x", "viking"), sources=("t55.pm3", "emu.cu1"))
        answers = answers_all_exact(protos)
        dev = make_devices(pm3_answers=answers)
        res = runner.run(plan, dev, interactive=False, session="S", out=lambda *a: None)
        self.assertEqual(len(res.licences), 2)
        self.assertTrue(all(c.outcome is Outcome.EXACT for c in res.cells))

        # ...and with the calibration row silent, the SAME emulated reads are UNGRADED.
        answers[("em410x", "t5577")] = ""
        answers[("viking", "t5577")] = ""
        res2 = runner.run(plan, make_devices(pm3_answers=answers), interactive=False,
                          session="S", out=lambda *a: None)
        emulated = [c for c in res2.cells if c.source == "emu.cu1"]
        self.assertTrue(emulated)
        self.assertTrue(all(c.outcome is Outcome.UNGRADED for c in emulated))
        self.assertTrue(all("cannot judge" in c.note for c in emulated))


if __name__ == "__main__":
    unittest.main()
