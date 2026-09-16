"""Protocols down, and what each DEVICE can do with each — the grid people actually open.

⭐⭐ A READER-BY-SOURCE GRID ANSWERS A QUESTION ABOUT PAIRS. "Can the Chameleon read a Proxmark
emulation" is worth knowing and is not why anybody opens the file. They open it to ask whether the
Chameleon on the desk does gproxii — read it, clone it, pretend to be it — three facts about one
device, spread across three different cells in the other layout.
"""

import unittest

from benchmatrix import capability as cap, registry as reg
from benchmatrix.state import Known, Reading


def known(protocol, source, reader, *outcomes):
    k = Known(protocol, source, reader)
    k.readings = [Reading("S%d" % i, o, "2026-01-0%d" % (i + 1), ()) for i, o in enumerate(outcomes)]
    return k


def found(*ks):
    return {(k.protocol, k.source, k.reader): k for k in ks}


class ThreeQuestionsPerDevice(unittest.TestCase):

    def test_each_capability_maps_to_the_cell_that_answers_it(self):
        self.assertEqual(cap.cell_for("em410x", "cu1", "read"), ("em410x", "t55.pm3", "rd.cu1"))
        self.assertEqual(cap.cell_for("em410x", "cu1", "write"), ("em410x", "t55.cu1", "rd.pm3"))
        self.assertEqual(cap.cell_for("em410x", "cu1", "emulate"), ("em410x", "emu.cu1", "rd.pm3"))

    def test_the_flippers_reader_id_is_not_rd_flipper(self):
        """⚠ The device is `flipper` and its reader is `rd.flip`; spelling it by rule produces a
        reader that does not exist and a column of blanks."""
        self.assertEqual(cap.cell_for("em410x", "flipper", "read")[2], "rd.flip")

    def test_a_devices_capability_reads_off_the_amalgamated_record(self):
        got = cap.assess(found(known("em410x", "emu.cu1", "rd.pm3", "SILENT")),
                         reg.resolve(["em410x"]), devices=("cu1",))
        self.assertEqual(got[("em410x", "cu1", "emulate")].state, "SILENT")
        self.assertEqual(got[("em410x", "cu1", "read")].state, "unmeasured")


class TheProxmarkMayNotJudgeItself(unittest.TestCase):
    """⛔ `emu.pm3 → rd.pm3` IS THE SELF-JUDGING CELL THE PLANNER REFUSES OUTRIGHT. A device cannot
    be both the instrument and the thing measured, so the Proxmark's own write and emulate columns
    have to be answered by somebody else — and must say who, because a verdict reached by a
    different instrument is a different claim."""

    def test_its_emulation_is_judged_by_another_reader_and_says_which(self):
        got = cap.assess(found(known("em410x", "emu.pm3", "rd.cu1", "EXACT")),
                         reg.resolve(["em410x"]), devices=("pm3", "cu1"))
        v = got[("em410x", "pm3", "emulate")]
        self.assertEqual((v.state, v.via), ("EXACT", "rd.cu1"))

    def test_and_never_by_itself(self):
        got = cap.assess(found(known("em410x", "emu.pm3", "rd.pm3", "EXACT")),
                         reg.resolve(["em410x"]), devices=("pm3", "cu1"))
        self.assertEqual(got[("em410x", "pm3", "emulate")].state, "unmeasured")


class TheReferenceIsCheckedNotAsserted(unittest.TestCase):
    """⛔ THE OPERATOR ASKED THE QUESTION DIRECTLY — "unless there are any examples where the
    proxmark cannot read it, but another device can". A yardstick nobody checks is an assumption."""

    def test_a_reader_beating_the_reference_is_reported(self):
        got = cap.check_reference(found(known("indala", "emu.cu1", "rd.pm3", "SILENT"),
                                        known("indala", "emu.cu1", "rd.flip", "EXACT")))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][:3], ("indala", "emu.cu1", "SILENT"))

    def test_one_chameleon_hearing_the_other_is_not_a_counterexample(self):
        """⚠ EXCLUDED BY NAME. Two Chameleons on the same firmware are one implementation talking
        to itself, so one decoding the other says nothing by any independent standard."""
        got = cap.check_reference(found(known("indala", "emu.cu1", "rd.pm3", "SILENT"),
                                        known("indala", "emu.cu1", "rd.cu2", "EXACT")))
        self.assertFalse(got)

    def test_agreement_reports_nothing(self):
        self.assertFalse(cap.check_reference(found(known("em410x", "t55.pm3", "rd.pm3", "EXACT"))))


class NoSuchCommandIsNotWorkOutstanding(unittest.TestCase):

    def test_a_firmware_with_no_arm_is_marked_as_such(self):
        """⚠ The ChameleonUltra reads and clones fdxa and emulates none; printing that as a blank
        sends somebody to the bench to discover what is already written down."""
        got = cap.assess({}, reg.resolve(["fdxa"]), devices=("cu1",))
        self.assertEqual(got[("fdxa", "cu1", "emulate")].state, "none")
        self.assertEqual(got[("fdxa", "cu1", "read")].state, "unmeasured")

    def test_keri_has_no_proxmark_emitter_registered(self):
        got = cap.assess({}, reg.resolve(["keri"]), devices=("pm3",))
        self.assertEqual(got[("keri", "pm3", "emulate")].state, "none")

    def test_the_two_kinds_of_empty_print_differently(self):
        self.assertNotEqual(cap.GLYPH["none"], cap.GLYPH["unmeasured"])


class UnanswerableIsNotUndone(unittest.TestCase):
    """⛔ `emu.pm3 → rd.cu1` IS REFUSED FOR EVERY SUBCARRIER PROTOCOL (RULES.md §2) and
    `emu.pm3 → rd.pm3` is self-judging, so on a bench of Proxmark + one Chameleon the Proxmark's
    indala emulation is UNANSWERABLE. Reported as plain "not measured" it reads as an afternoon's
    work that does not exist."""

    def test_a_cell_no_attached_reader_may_judge_is_flagged_blocked(self):
        refused = {("indala", "emu.pm3", "rd.cu1"): "subcarrier"}
        got = cap.assess({}, reg.resolve(["indala"]), devices=("pm3", "cu1"), refused=refused)
        self.assertTrue(got[("indala", "pm3", "emulate")].blocked)

    def test_but_not_when_a_reader_that_could_answer_is_attached(self):
        """⚠ The same cell with a Flipper on the bench is ordinary outstanding work."""
        refused = {("indala", "emu.pm3", "rd.cu1"): "subcarrier"}
        got = cap.assess({}, reg.resolve(["indala"]), devices=("pm3", "cu1", "flipper"),
                         refused=refused)
        self.assertFalse(got[("indala", "pm3", "emulate")].blocked)


if __name__ == "__main__":
    unittest.main()
