"""Stations, stacks, and the move cues that get the operator from one to the next."""

import unittest

from benchmatrix.stations import (Bench, CU1, CU2, FLIPPER, PM3, T5577, Station, StationError,
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
        st = build_station({PM3, CU1}, B)
        self.assertEqual(null_station(st), st)

class TwoFacesTwoDevices(unittest.TestCase):
    """⛔⛔ THE CAP IS ABOUT FACES, NOT ABOUT TAGS, AND GATING IT ON TAGS LEFT A HOLE THE PLANNER
    WALKED INTO. Every device here reads and writes from a SINGLE FACE. With a tag, the tag sits in
    the middle and two devices face it; with no tag, two devices face each other. Either way two is
    the limit — and a station with no tag had no limit at all.

    ⚠ IT REACHED THE BENCH. The planner built `FLIP+CU1+CU2` for the emulation cells and the
    operator refused to build it: "A Chameleon in the middle of the sandwich is meaningless. All the
    electronic rfid devices read and write from a single face." A third device is not weakly
    coupled — it is stacked behind one of the other two and takes no part in anything.
    """

    def test_three_active_devices_with_a_tag_are_refused(self):
        with self.assertRaises(StationError):
            build_station({PM3, T5577, CU1, CU2}, B)

    def test_and_three_without_one_are_refused_too(self):
        """⛔ THE CASE THAT WAS ALLOWED. Removing the tag does not add a face to anything."""
        with self.assertRaises(StationError) as cm:
            build_station({FLIPPER, CU1, CU2}, B)
        self.assertIn("ONE FACE", str(cm.exception))
        self.assertIn("takes no part", str(cm.exception))

    def test_two_with_a_tag_between_them_is_the_sandwich(self):
        self.assertEqual(build_station({PM3, T5577, CU1}, B).stack, (PM3, T5577, CU1))

    def test_two_facing_each_other_with_no_tag_is_fine(self):
        self.assertEqual(build_station({FLIPPER, CU1}, B).stack, (FLIPPER, CU1))

    def test_the_planner_never_proposes_one_it_could_not_build(self):
        """⚠ `choose_stations` had its own copy of the rule, gated the same way, so the planner and
        the builder disagreed — and the planner is what the operator is asked to obey."""
        from benchmatrix import learned, plan as planning, registry as reg
        from benchmatrix.stations import TAGS, MAX_ACTIVE_IN_A_STACK
        protos, _ = learned.apply(reg.resolve(["em410x"]), learned.load(), "LATER")
        p = planning.build(protos, ["t55.pm3", "emu.cu1", "emu.cu2", "emu.flip"],
                           ["rd.pm3", "rd.cu1", "rd.cu2", "rd.flip"], B)
        for b in p.blocks:
            active = [d for d in b.station.stack if d not in TAGS]
            self.assertLessEqual(len(active), MAX_ACTIVE_IN_A_STACK, b.station.name)

if __name__ == "__main__":
    unittest.main()


class AnyDeviceMayBeLeftOut(unittest.TestCase):
    """⚠ CU1 WAS UNCONDITIONAL. `--no-cu2` and `--no-flipper` existed from the start and the first
    Chameleon was simply assumed present — so "measure only Chameleon 2" was the one single-device
    session the harness could not express, and the two are deliberately flashed differently."""

    def _bench_for(self, **flags):
        from benchmatrix.cli import _bench
        import argparse
        a = argparse.Namespace(no_cu1=False, no_cu2=False, no_flipper=False,
                               max_stack=3, oem=None, pad="pad0", tags=1)
        for k, v in flags.items():
            setattr(a, k, v)
        return _bench(a)

    def test_the_default_bench_has_everything(self):
        self.assertEqual(self._bench_for().has, frozenset({PM3, T5577, CU1, CU2, FLIPPER}))

    def test_chameleon_one_can_be_left_out_like_any_other(self):
        self.assertEqual(self._bench_for(no_cu1=True, no_flipper=True).has,
                         frozenset({PM3, T5577, CU2}))

    def test_a_cu2_only_bench_can_still_be_planned(self):
        """⭐ THE POINT OF THE FLAG. Chameleon 2 needs the Proxmark to write its gold tag and to
        judge its emulation, and nothing else."""
        from benchmatrix import plan as planning, registry as reg
        p = planning.build(reg.resolve(["em410x"]), ["t55.pm3", "t55.cu2", "emu.cu2"],
                           ["rd.pm3", "rd.cu2"], self._bench_for(no_cu1=True, no_flipper=True))
        self.assertTrue(p.cells)
        for b in p.blocks:
            self.assertNotIn(CU1, b.station.stack)

    def test_excluding_everything_but_the_proxmark_is_refused_with_a_reason(self):
        """⛔ A PROXMARK ALONE MEASURES NOTHING — every cell it can reach by itself is self-judging,
        so the plan would refuse them all and print an EMPTY GRID. That reads as "this bench has no
        capabilities" rather than "you excluded every device that could answer"."""
        with self.assertRaises(ValueError) as cm:
            self._bench_for(no_cu1=True, no_cu2=True, no_flipper=True)
        self.assertIn("cannot judge itself", str(cm.exception))
