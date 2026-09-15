"""Plan-time refusals, move minimisation, and the physical facts the plan has to respect."""

import unittest

from tests.helpers import reg, tiny_plan
from benchmatrix import plan as planning
from benchmatrix.registry import SUBCARRIER_RULE
from benchmatrix.topology import Bench, READERS, SOURCES


class TheSubcarrierRule(unittest.TestCase):

    def test_emulated_rows_against_the_chameleon_reader_are_refused_for_the_subcarrier_family(self):
        """RULES.md §2: refused, never recorded as failures."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("emu.cu2",), readers=("rd.cu",))
        refused = {e.protocol for e in plan.exclusions if e.rule == "subcarrier"}
        self.assertEqual(refused, set(SUBCARRIER_RULE))

    def test_the_rule_is_named_explicitly_not_derived_from_modulation(self):
        """⚠ Four of the five are ASK on the coil. Deriving the rule from `family` would silently
        re-admit them; deriving `family` from the rule would falsify the modulation record."""
        ask_but_m52 = [p for p in reg.TIER0.values() if p.subcarrier and p.family == "ask"]
        self.assertEqual({p.key for p in ask_but_m52},
                         {"gallagher", "securakey", "noralsy", "gproxii"})

    def test_a_refused_cell_never_becomes_an_outcome(self):
        """The emulated cell disappears; the real-tag row that licenses the column stays, because
        a Chameleon reading a real tag is exactly what the subcarrier rule does NOT forbid."""
        plan = tiny_plan(keys=("indala",), sources=("emu.cu2",), readers=("rd.cu",))
        self.assertEqual({(c.source, c.reader) for c in plan.cells}, {("t55.pm3", "rd.cu")})
        self.assertNotIn("emu.cu2", {c.source for c in plan.cells})


class WhatCannotBeMeasured(unittest.TestCase):

    def test_the_chameleon_reads_real_silicon_and_that_is_the_point(self):
        """⭐ An emulation is a waveform driven onto a coil; only a real tag's silicon produces
        genuine load modulation. `(t55.pm3, rd.cu)` is the ONLY measurement that says whether our
        own decoders work on real RF, and it is both the control for the column and the headline
        result of the run. All 16 must plan."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("t55.pm3",), readers=("rd.cu",))
        self.assertEqual(len(plan.cells), 16)
        self.assertTrue(all(c.is_calibration for c in plan.cells))
        self.assertEqual(plan.exclusions, [])

    def test_a_protocol_with_no_registered_read_arm_is_still_refused(self):
        """Defensive: every tier-0 protocol has one, but a tier-1 addition might not."""
        armless = reg.Protocol(**{**reg.TIER0["pac"].__dict__, "key": "armless", "cu_read": None})
        plan = planning.build([armless], ["t55.pm3"], ["rd.cu"], Bench())
        self.assertEqual(plan.cells, [])
        self.assertEqual([e.rule for e in plan.exclusions], ["no-read-arm"])

    def test_the_flipper_column_needs_an_expectation_first(self):
        """Ten protocols have no known Flipper hex; matching on the name alone breaks RULES.md §6."""
        unknown = [p.key for p in reg.TIER0.values() if p.flip_expect is None]
        plan = tiny_plan(keys=unknown, sources=("t55.pm3",), readers=("rd.flip",))
        self.assertEqual(plan.cells, [])
        self.assertTrue(any("name-match rule" in e.why for e in plan.exclusions))

    def test_a_registered_firmware_gap_removes_the_source(self):
        """the gap register: the Flipper cannot write keri/nexwatch/idteck/gproxii to a T5577.

        ⚠ The calibration row survives — it is a `t55.pm3` row and the Proxmark writes keri fine.
        What disappears is the `t55.flip` source, which does not exist for this protocol.
        """
        plan = tiny_plan(keys=("keri",), sources=("t55.flip",), readers=("rd.pm3",))
        self.assertEqual({c.source for c in plan.cells}, {"t55.pm3"})
        self.assertTrue(any(e.rule == "gap:flipper-write" for e in plan.exclusions))

    def test_an_unlicensable_protocol_is_dropped_with_its_reason(self):
        no_t55 = reg.Protocol(**{**reg.TIER0["pac"].__dict__, "key": "fictional",
                                 "t55_capable": False})
        plan = planning.build([no_t55], ["emu.cu1"], ["rd.pm3"], Bench())
        self.assertEqual(plan.cells, [])
        self.assertEqual([e.rule for e in plan.exclusions], ["unlicensable"])

    def test_an_oem_card_makes_it_licensable_again(self):
        no_t55 = reg.Protocol(**{**reg.TIER0["pac"].__dict__, "key": "fictional",
                                 "t55_capable": False})
        plan = planning.build([no_t55], ["emu.cu1"], ["rd.pm3"], Bench(has_oem=frozenset({"fictional"})))
        self.assertEqual({c.source for c in plan.cells}, {"oem", "emu.cu1"})
        self.assertEqual(plan.audit(), [])


class ThePlanIsPhysicallyPossible(unittest.TestCase):

    def test_the_tag_always_holds_what_the_row_is_about_to_read(self):
        """⛔ ONE T5577, SIXTEEN CREDENTIALS. Modelling the write as part of the read would read
        whatever the tag still held from the previous protocol and file it as SILENT for this one."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("t55.pm3",), readers=("rd.pm3",))
        self.assertEqual(plan.audit(), [])
        held = None
        for b in plan.blocks:
            for s in b.steps:
                if s.kind == "write":
                    held = s.protocol.key
                else:
                    self.assertEqual(held, s.protocol.key)

    def test_carrying_the_tag_to_another_reader_costs_two_moves_per_protocol(self):
        """Not a defect — the honest cost of one tag, made visible instead of hidden."""
        known = [p.key for p in reg.TIER0.values() if p.flip_expect][:3]
        plan = tiny_plan(keys=known, sources=("t55.pm3",), readers=("rd.flip",))
        self.assertEqual(len(plan.blocks), 2 * len(known))

    def test_sixteen_protocols_on_one_reader_cost_two_moves(self):
        """One arrangement for the tag that licenses the column, one for the emulator under test —
        and sixteen protocols add nothing to either, because the emitter is rearmed in place."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("emu.cu1",), readers=("rd.pm3",))
        self.assertEqual([b.topology.name for b in plan.blocks], ["PM3_T55", "PM3_CU1"])
        self.assertEqual(len(plan.cells), 2 * 16)   # the emulated row and its calibration row

    def test_a_calibration_row_is_never_measured_after_what_it_licenses(self):
        for source in ("emu.cu1", "emu.cu2", "emu.flip"):
            with self.subTest(source=source):
                plan = tiny_plan(keys=reg.TIER0_ORDER, sources=(source,), readers=("rd.pm3",))
                self.assertEqual(plan.audit(), [])

    def test_the_audit_catches_a_hand_broken_plan(self):
        """The invariant is asserted independently of the builder, so the two cannot drift."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3", "emu.cu1"), readers=("rd.pm3",))
        for b in plan.blocks:
            b.steps = [s for s in b.steps if s.kind != "write"]
        self.assertTrue(any("while it holds" in m for m in plan.audit()))


class EverySensibleRequestPlans(unittest.TestCase):

    def test_no_combination_raises(self):
        bench = Bench(has_oem=frozenset(reg.TIER0_ORDER))
        for source in SOURCES:
            for reader in READERS:
                with self.subTest(source=source, reader=reader):
                    plan = planning.build(reg.resolve(None), [source], [reader], bench)
                    self.assertEqual(plan.audit(), [])


if __name__ == "__main__":
    unittest.main()
