"""Move cues. The failure these prevent is the operator and the agent disagreeing about the bench."""

import unittest

from benchmatrix.topology import (Bench, CU1, CU2, PM3, T5577, Topology, TopologyError,
                                  null_topology, plan_move, topology_for)

B = Bench()


class ACueNamesWhatComesOff(unittest.TestCase):

    def test_removal_is_stated_before_placement(self):
        """⛔ It is the half that gets forgotten, and it is the half that ruins a run."""
        frm = topology_for("emu.cu1", "rd.pm3", B)
        to = topology_for("emu.cu2", "rd.pm3", B)
        text = plan_move(frm, to).text()
        self.assertLess(text.index("Chameleon 1"), text.index("Chameleon 2"))
        self.assertIn("take", text.lower())

    def test_a_reader_change_clears_the_old_pad_even_for_a_device_it_keeps(self):
        """⛔ THE CASE A SET DIFFERENCE GETS WRONG, IN THE DANGEROUS DIRECTION. PM3_CU2 -> CU1_CU2
        keeps Chameleon 2 in the run, but it still has to come off the Proxmark first; a naive diff
        says "no change" and leaves a Chameleon on the wrong pad with a grid that looks fine."""
        frm = Topology("PM3_CU2", PM3, (CU2,))
        to = Topology("CU1_CU2", CU1, (CU2,))
        move = plan_move(frm, to)
        self.assertFalse(move.is_noop)
        self.assertIn("clear", move.text().lower())
        self.assertIn("Chameleon 2", move.text())

    def test_the_spoken_form_pronounces_device_numbers(self):
        move = plan_move(None, topology_for("emu.cu2", "rd.pm3", B))
        self.assertIn("Chameleon two", move.spoken())
        self.assertNotIn("Chameleon 2", move.spoken())

    def test_the_first_move_has_nothing_to_remove(self):
        move = plan_move(None, topology_for("t55.pm3", "rd.pm3", B))
        self.assertEqual(move.remove, ())
        self.assertEqual(move.place, (T5577,))


class ADeviceCannotJudgeItself(unittest.TestCase):

    def test_the_three_self_judging_pairs_are_refused(self):
        """README.md: all three failures had the same shape — one device used as both the
        instrument and the thing being measured."""
        for source, reader in (("emu.flip", "rd.flip"), ("emu.cu1", "rd.cu"), ("t55.pm3", "rd.pm3")):
            with self.subTest(source=source, reader=reader):
                if source == "t55.pm3":
                    topology_for(source, reader, B)     # a tag is not a device — this is fine
                    continue
                with self.assertRaises(TopologyError):
                    topology_for(source, reader, B)

    def test_the_other_chameleon_can_judge(self):
        t = topology_for("emu.cu2", "rd.cu", B)
        self.assertEqual((t.reader_dev, t.on_pad), (CU1, (CU2,)))

    def test_the_designated_reader_is_configurable(self):
        t = topology_for("emu.cu1", "rd.cu", Bench(cu_reader=CU2))
        self.assertEqual((t.reader_dev, t.on_pad), (CU2, (CU1,)))


class TheNullArrangement(unittest.TestCase):

    def test_an_active_emitter_stays_on_the_pad(self):
        """pm3grade.sh's rule: a null taken with the pad cleared measures a different bench."""
        self.assertEqual(null_topology(Topology("PM3_CU2", PM3, (CU2,))).on_pad, (CU2,))

    def test_a_passive_tag_is_removed(self):
        """It has no idle state — it answers the field whenever it is in one."""
        self.assertEqual(null_topology(Topology("PM3_T55", PM3, (T5577,))).on_pad, ())


if __name__ == "__main__":
    unittest.main()
