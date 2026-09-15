"""Learned expectations, and the guard that stops one licensing the session that learned it."""

import unittest

from tests.helpers import reg
from benchmatrix import learned


def rec(session="S1", value="ABCD1234", protocol="pac"):
    return learned.Learned(protocol=protocol, reader="rd.flip", value=value, session=session,
                           source="t55.pm3", when="now", evidence="PAC/Stanley ABCD1234")


class TheSelfLicensingTrap(unittest.TestCase):

    def test_an_expectation_cannot_license_the_session_that_learned_it(self):
        """⛔⛔ Otherwise the calibration row is compared against itself and CANNOT FAIL — a control
        quietly inverted into a tautology, invisible in the grid: every licence green, every licence
        worthless. C473 with one more step of indirection."""
        with self.assertRaises(learned.LearningRefused) as cm:
            learned.check_independence(rec(session="S1"), "S1")
        self.assertIn("unfailable", str(cm.exception))

    def test_a_later_session_may_use_it(self):
        learned.check_independence(rec(session="S1"), "S2")     # must not raise

    def test_apply_folds_it_in_and_says_where_it_came_from(self):
        protos = reg.resolve(["pac"])
        out, notes = learned.apply(protos, {("pac", "rd.flip"): rec()}, "S2")
        self.assertEqual(out[0].flip_expect, "ABCD1234")
        self.assertTrue(any("learned:" in n for n in notes))

    def test_apply_refuses_in_the_learning_session_and_leaves_the_registry_alone(self):
        protos = reg.resolve(["pac"])
        out, notes = learned.apply(protos, {("pac", "rd.flip"): rec(session="S1")}, "S1")
        self.assertIsNone(out[0].flip_expect, "the column stays unplannable, which is correct")
        self.assertTrue(any(n.startswith("⛔") for n in notes))

    def test_a_registry_value_is_never_overwritten_by_a_learned_one(self):
        """The registry's six are derived from the armed credential width and are not up for
        revision by a single bench read."""
        protos = reg.resolve(["em410x"])
        out, _ = learned.apply(protos, {("em410x", "rd.flip"): rec(protocol="em410x",
                                                                  value="DEADBEEF")}, "S2")
        self.assertEqual(out[0].flip_expect, "2244668800")


class ReadingTheFlippersAnswer(unittest.TestCase):

    def test_only_the_anchored_line_with_the_right_name_counts(self):
        text = ("Available protocols: PAC/Stanley, Viking\n"
                "PAC/Stanley ABCD1234\n"
                "Reading stopped")
        self.assertEqual(learned.observed_value(text, "PAC/Stanley"), "ABCD1234")
        self.assertIsNone(learned.observed_value(text, "Viking"),
                          "a name in the protocol listing is not a decode — the M28 trap")

    def test_a_name_with_a_space_is_read_correctly(self):
        self.assertEqual(learned.observed_value("Radio Key 7FCB4000", "Radio Key"), "7FCB4000")


if __name__ == "__main__":
    unittest.main()
