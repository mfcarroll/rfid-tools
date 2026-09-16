"""The cues the operator acts on. Positioning error is the largest uncontrolled risk in this work."""

import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import ui
from benchmatrix.stations import Bench, CU1, CU2, FLIPPER, PM3, T5577, build_station

B = Bench()


class TheVoiceSaysOneThing(unittest.TestCase):
    """⛔ "Add the Proxmark and Chameleon 1, stack is Chameleon one on the Proxmark" is a delta and
    a restatement fighting each other, and the ear cannot hold it."""

    def say(self, *devs):
        return ui.spoken_arrangement([build_station(set(devs), B)])

    def test_a_simple_pair(self):
        self.assertEqual(self.say(PM3, CU1), "put Chameleon one on the Proxmark")

    def test_a_tag_in_between_is_said_as_such(self):
        self.assertEqual(self.say(PM3, T5577, CU1),
                         "put Chameleon one on the Proxmark, with a tag in between")

    def test_a_chameleon_pair_around_a_tag(self):
        self.assertEqual(self.say(CU1, T5577, CU2),
                         "put Chameleon two on Chameleon one, with a tag in between")

    def test_a_lone_device_is_said_to_be_alone(self):
        self.assertIn("nothing on it", self.say(PM3))

    def test_several_rigs_are_one_sentence_each(self):
        said = ui.spoken_arrangement([build_station({PM3, CU1}, B),
                                      build_station({FLIPPER, CU2}, B)])
        self.assertEqual(said, "put Chameleon one on the Proxmark. "
                               "put Chameleon two on the Flipper")

    def test_it_never_mentions_what_comes_off(self):
        """The removals are on the screen, where they can be checked against the bench, not in the
        ear where they have to be remembered."""
        for text in (self.say(PM3, CU1), self.say(PM3, T5577, CU1)):
            for word in ("take", "remove", "off", "clear"):
                self.assertNotIn(word, text)


class TheScreenShowsTheWholeTruth(unittest.TestCase):

    def setUp(self):
        self.was, ui.ENABLED = ui.ENABLED, False

    def tearDown(self):
        ui.ENABLED = self.was

    def draw(self, devs, idle=()):
        return "\n".join(ui.diagram([build_station(set(devs), B)], idle))

    def test_the_stack_is_drawn_top_down(self):
        lines = [l.strip() for l in self.draw({PM3, T5577, CU1}).splitlines() if l.strip()]
        self.assertEqual(lines[0], "Rig 1")
        self.assertEqual(lines[2:], ["Chameleon 1", "( T5577 tag )", "the Proxmark"])

    def test_a_tag_is_bracketed(self):
        """⭐ It is the one passive thing in the stack and the piece most often left in place."""
        self.assertIn("( T5577 tag )", self.draw({PM3, T5577}))
        self.assertNotIn("( the Proxmark )", self.draw({PM3, T5577}))

    def test_what_must_not_be_there_is_named(self):
        drawn = self.draw({PM3, CU1}, idle=[CU2, FLIPPER])
        self.assertIn("set aside", drawn)
        self.assertIn("Chameleon 2", drawn)
        self.assertIn("the Flipper", drawn)

    def test_several_rigs_sit_side_by_side(self):
        drawn = "\n".join(ui.diagram([build_station({PM3, T5577, CU1}, B),
                                      build_station({FLIPPER, CU2}, B)]))
        self.assertIn("Rig 1", drawn)
        self.assertIn("Rig 2", drawn)
        header = [l for l in drawn.splitlines() if "Rig 1" in l][0]
        self.assertIn("Rig 2", header, "the rigs are columns, not one after another")


class Colour(unittest.TestCase):

    def test_it_follows_whether_the_output_is_a_terminal(self):
        """⚠ A grid redirected to a file must not carry escape codes into the published record, so
        the switch is decided by `isatty` and `NO_COLOR` and nothing else."""
        self.assertEqual("\x1b" in ui.paint("x", "red"), ui.ENABLED)

    def test_painting_is_a_no_op_when_disabled(self):
        was, ui.ENABLED = ui.ENABLED, False
        try:
            self.assertEqual(ui.paint("hello", "red", "bold"), "hello")
        finally:
            ui.ENABLED = was

    def test_an_outcome_is_coloured_by_what_it_means(self):
        was, ui.ENABLED = ui.ENABLED, True
        try:
            self.assertIn("32", ui.outcome("✅", "EXACT"))      # green
            self.assertIn("31", ui.outcome("❌", "WRONG"))       # red
            self.assertNotEqual(ui.outcome("·", "SILENT"), ui.outcome("▒", "UNGRADED"))
        finally:
            ui.ENABLED = was

    def test_width_is_measured_without_the_escape_codes(self):
        """Otherwise a coloured column is padded by the length of its own colour codes."""
        was, ui.ENABLED = ui.ENABLED, True
        try:
            self.assertEqual(ui._plain(ui.paint("abc", "red")), "abc")
        finally:
            ui.ENABLED = was


if __name__ == "__main__":
    unittest.main()
