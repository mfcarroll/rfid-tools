"""Stations, stacks, and the move cues that get the operator from one to the next."""

import unittest

from benchmatrix.stations import (Bench, CU1, CU2, PM3, T5577, Station, StationError,
                                  build_station, devices_to_measure, devices_to_produce,
                                  move_cost, null_station, plan_move, station_admits)

B = Bench()


class WhatACellNeeds(unittest.TestCase):

    def test_the_writer_is_needed_to_produce_but_not_to_measure(self):
        """⭐ THE WHOLE BASIS OF ISOLATION. A tag keeps its credential when the writer is taken
        away, so the writer is not part of the measurement — which is exactly why it counts as
        crowding, and why a crowded failure can be retaken without it."""
        self.assertEqual(devices_to_produce("t55.pm3", "rd.cu1"), {PM3, T5577, CU1})
        self.assertEqual(devices_to_measure("t55.pm3", "rd.cu1"), {T5577, CU1})

    def test_an_emulation_needs_only_the_pair(self):
        self.assertEqual(devices_to_produce("emu.cu2", "rd.pm3"), {CU2, PM3})

    def test_a_device_cannot_judge_itself(self):
        for source, reader in (("emu.cu1", "rd.cu1"), ("emu.flip", "rd.flip")):
            with self.subTest(source=source, reader=reader):
                with self.assertRaises(StationError):
                    devices_to_measure(source, reader)

    def test_a_chameleon_may_judge_the_other_one(self):
        self.assertEqual(devices_to_measure("emu.cu2", "rd.cu1"), {CU2, CU1})


class WhatAStationAdmits(unittest.TestCase):

    def test_a_tag_and_an_emulation_never_share_a_station(self):
        """⛔ If the tag holds P and a device emulates P, a reader that decodes P cannot say which
        it heard. The two kinds of station are disjoint by construction, not by care."""
        tag_station = build_station({PM3, T5577, CU1}, B)
        self.assertTrue(station_admits(tag_station, "t55.pm3", "rd.cu1"))
        self.assertFalse(station_admits(tag_station, "emu.cu1", "rd.pm3"))

        emu_station = build_station({PM3, CU1}, B)
        self.assertTrue(station_admits(emu_station, "emu.cu1", "rd.pm3"))
        self.assertFalse(station_admits(emu_station, "t55.pm3", "rd.pm3"))

    def test_the_cycle_station_admits_four_cells_per_protocol(self):
        """The arrangement the whole design is built around."""
        st = build_station({PM3, T5577, CU1}, B)
        admitted = [(s, r) for s in ("t55.pm3", "t55.cu1") for r in ("rd.pm3", "rd.cu1")
                    if station_admits(st, s, r)]
        self.assertEqual(len(admitted), 4)

    def test_crowding_is_what_is_present_but_uninvolved(self):
        st = build_station({PM3, T5577, CU1}, B)
        self.assertEqual(st.crowding(devices_to_measure("t55.pm3", "rd.cu1")), {PM3})
        self.assertEqual(st.crowding(devices_to_measure("t55.pm3", "rd.pm3")), {CU1})
        pair = build_station({T5577, CU1}, B)
        self.assertEqual(pair.crowding(devices_to_measure("t55.pm3", "rd.cu1")), frozenset())


class Stacks(unittest.TestCase):

    def test_the_stack_is_ordered_physically(self):
        """Proxmark at the bottom, tag in the middle, the rest on top."""
        self.assertEqual(build_station({CU1, PM3, T5577}, B).stack, (PM3, T5577, CU1))

    def test_a_stack_holds_at_most_one_tag(self):
        """⛔ Two passive tags both answer the field, so a decode cannot say which it came from —
        the same ambiguity as mixing a tag with an emulation."""
        from benchmatrix.stations import OEMTAG
        bench = Bench(has_oem=frozenset({"pac"}))
        with self.assertRaises(StationError):
            build_station({PM3, T5577, OEMTAG}, bench)
        self.assertFalse(station_admits(Station((PM3, T5577, OEMTAG)), "t55.pm3", "rd.pm3"))

    def test_an_oem_card_counts_as_a_device_only_when_one_is_owned(self):
        from benchmatrix.stations import OEMTAG
        self.assertFalse(Bench().available(OEMTAG))
        self.assertTrue(Bench(has_oem=frozenset({"pac"})).available(OEMTAG))

    def test_a_bench_without_a_device_refuses_to_build_it_in(self):
        with self.assertRaises(StationError):
            build_station({PM3, CU2}, Bench(has=frozenset({PM3, CU1, T5577})))


class MoveCues(unittest.TestCase):

    def test_removal_is_named_before_placement(self):
        """⛔ It is the half that gets forgotten, and the half that leaves a device in the field
        that nothing in the plan knows about."""
        frm = build_station({PM3, T5577, CU1}, B)
        to = build_station({PM3, T5577, CU2}, B)
        text = plan_move(frm, to).text()
        self.assertLess(text.index("Chameleon 1"), text.index("Chameleon 2"))
        self.assertIn("take", text.lower())

    def test_the_spoken_form_reads_the_stack_back(self):
        move = plan_move(None, build_station({PM3, T5577, CU2}, B))
        self.assertIn("Chameleon two", move.spoken())
        self.assertNotIn("Chameleon 2", move.spoken())
        self.assertIn("on", move.spoken())

    def test_cost_counts_devices_handled(self):
        a = build_station({PM3, T5577, CU1}, B)
        b = build_station({PM3, T5577, CU2}, B)
        c = build_station({CU1, CU2}, B)
        self.assertEqual(move_cost(a, b), 2)
        self.assertGreater(move_cost(a, c), move_cost(a, b))

    def test_an_unchanged_stack_is_a_noop(self):
        a = build_station({PM3, T5577}, B)
        self.assertTrue(plan_move(a, a).is_noop)


class TheNullArrangement(unittest.TestCase):

    def test_active_devices_stay_and_passive_tags_leave(self):
        st = build_station({PM3, T5577, CU1}, B)
        self.assertEqual(null_station(st).stack, (PM3, CU1))

    def test_a_station_with_no_tag_is_swept_as_it_stands(self):
        st = build_station({PM3, CU1, CU2}, B)
        self.assertEqual(null_station(st), st)


if __name__ == "__main__":
    unittest.main()
