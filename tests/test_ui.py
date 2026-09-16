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


class APureRemovalIsSaidAsARemoval(unittest.TestCase):
    """⚠ Describing the arrangement is right when something is being placed, and confusing when the
    only thing to do is take the tag out of a stack that is otherwise already correct."""

    def test_one_thing(self):
        self.assertEqual(ui.spoken_removal((T5577,)), "take out the tag")

    def test_several_things(self):
        self.assertEqual(ui.spoken_removal((T5577, CU2)), "take out the tag and Chameleon two")

    def test_the_runner_says_it_when_nothing_is_being_added(self):
        from benchmatrix.stations import plan_move
        full = build_station({PM3, T5577, CU1}, B)
        empty = build_station({PM3, CU1}, B)
        move = plan_move(full, empty)
        self.assertTrue(move.remove and not move.place, "this is the pure-removal case")
        self.assertEqual(ui.spoken_removal(move.remove), "take out the tag")


class APureAdditionIsSaidAsAnAddition(unittest.TestCase):
    """⚠ THE MIRROR OF A PURE REMOVAL, AND THE PRINCIPLE WAS ONLY HALF APPLIED. "Put Chameleon one
    on the Proxmark, with a tag in between" describes a rig that is already built except for the
    tag, so the one word that is an instruction is buried in a sentence about things that have not
    moved. Operator, on the bench: same principle as "take out the tag"."""

    def _cue(self, frm, to):
        """Exactly the branch `_move` takes, so the test cannot pass while the runner says
        something else."""
        from benchmatrix.stations import plan_move
        move = plan_move(frm, to)
        if move.remove and not move.place:
            return ui.spoken_removal(move.remove)
        if move.place and not move.remove and frm is not None:
            return ui.spoken_addition(move.place, to)
        return ui.spoken_arrangement([to])

    def test_a_tag_going_into_an_unchanged_rig(self):
        self.assertEqual(self._cue(build_station({PM3, CU1}, B),
                                   build_station({PM3, T5577, CU1}, B)),
                         "put the tag in between")

    def test_and_it_is_the_exact_inverse_of_taking_it_out(self):
        bare, full = build_station({PM3, CU1}, B), build_station({PM3, T5577, CU1}, B)
        self.assertEqual(self._cue(bare, full), "put the tag in between")
        self.assertEqual(self._cue(full, bare), "take out the tag")

    def test_a_device_added_on_top_says_on_top(self):
        """⭐ The position comes from the stack, not from what the thing is — so this needed no
        second rule. A tag lands in the middle because devices read from one face."""
        self.assertEqual(self._cue(build_station({PM3, T5577}, B),
                                   build_station({PM3, T5577, CU1}, B)),
                         "put Chameleon one on top")

    def test_the_first_station_still_gets_the_whole_arrangement(self):
        """⛔ There is no previous state for a delta to be a delta against, and an arrangement is
        the only thing the operator can check against the bench in front of them."""
        self.assertEqual(self._cue(None, build_station({PM3, T5577, CU1}, B)),
                         "put Chameleon one on the Proxmark, with a tag in between")

    def test_a_rebuild_is_still_an_arrangement(self):
        """⚠ Something on AND something off is not a delta anyone can follow."""
        said = self._cue(build_station({PM3, CU2}, B), build_station({PM3, T5577, CU1}, B))
        self.assertEqual(said, "put Chameleon one on the Proxmark, with a tag in between")


class ALongOperationSaysSoBeforeItBlocks(unittest.TestCase):
    """⛔⛔ SILENCE DURING A LONG CALL IS INDISTINGUISHABLE FROM A HANG, and the operator's only move
    is Ctrl-C — which aborts a healthy session. `cue_done` already exists for exactly this reason at
    the END of a run; the same argument applies to any step that blocks for tens of seconds.

    ⚠ `lf t55xx wipe` writes eight blocks and then proves itself with `detect`. Its timeout is 120s,
    so on a real bench "stuck" and "working" looked identical for as long as it took. Operator,
    mid-session, on a wipe that was doing its job: "Appears to be stuck".
    """

    def test_the_announcement_comes_first(self):
        said = []
        done = ui.working(said.append, "wiping the tag")
        self.assertEqual(len(said), 1, "the operator hears about it BEFORE the wait, not after")
        self.assertIn("wiping the tag", said[0])
        done("  wiped")
        self.assertEqual(len(said), 2)

    def test_and_the_result_carries_how_long_it_took(self):
        """⭐ This bench optimises operator interventions, so which machine steps cost twenty
        seconds and which cost two is what says whether a station is worth restructuring."""
        said = []
        ui.working(said.append, "wiping")("  wiped")
        self.assertRegex(said[-1], r"^  wiped\s+\(\d+s\)$")
