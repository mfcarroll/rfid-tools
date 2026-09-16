"""Plan-time refusals, move minimisation, and the physical facts the plan has to respect."""

import unittest

from tests.helpers import reg, tiny_plan
from benchmatrix import plan as planning
from benchmatrix.registry import SUBCARRIER_RULE
from benchmatrix.stations import Bench, READERS, SOURCES


class TheSubcarrierRule(unittest.TestCase):

    def test_emulated_rows_against_the_chameleon_reader_are_refused_for_the_subcarrier_family(self):
        """RULES.md §2: refused, never recorded as failures."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("emu.cu2",), readers=("rd.cu1",))
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
        plan = tiny_plan(keys=("indala",), sources=("emu.cu2",), readers=("rd.cu1",))
        self.assertEqual({(c.source, c.reader) for c in plan.cells}, {("t55.pm3", "rd.cu1")})
        self.assertNotIn("emu.cu2", {c.source for c in plan.cells})


class WhatCannotBeMeasured(unittest.TestCase):

    def test_the_chameleon_reads_real_silicon_and_that_is_the_point(self):
        """⭐ An emulation is a waveform driven onto a coil; only a real tag's silicon produces
        genuine load modulation. `(t55.pm3, rd.cu)` is the ONLY measurement that says whether our
        own decoders work on real RF, and it is both the control for the column and the headline
        result of the run. All 16 must plan."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("t55.pm3",), readers=("rd.cu1",))
        known = [p.key for p in reg.TIER0.values()
                 if p.cu_expect and p.can("cu_read") and p.can("pm3_write") and p.expect]
        self.assertEqual({c.protocol.key for c in plan.cells}, set(known))
        self.assertTrue(all(c.is_calibration for c in plan.cells))
        # Two distinct reasons the rest drop out, and the grid must not conflate them:
        #   no-expectation — the Chameleon renders it in wording nobody has recorded
        #   unlicensable   — nothing can produce a gold tag it and the Proxmark agree on
        self.assertEqual({e.rule for e in plan.exclusions}, {"no-expectation", "unlicensable"})
        electra = [e for e in plan.exclusions if e.protocol == "em410x_electra"]
        self.assertTrue(electra)
        self.assertIn("different credentials", electra[0].why,
                      "it must name the real cause, not claim a T5577 cannot hold it")

    def test_a_protocol_with_no_registered_read_arm_is_still_refused(self):
        """Defensive: every tier-0 protocol has one, but a tier-1 addition might not."""
        armless = reg.Protocol(**{**reg.TIER0["pac"].__dict__, "key": "armless", "cu_read": None})
        plan = planning.build([armless], ["t55.pm3"], ["rd.cu1"], Bench())
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
        bench = Bench(has_oem=frozenset({"fictional"}))
        plan = planning.build([no_t55], ["emu.cu1"], ["rd.pm3"], bench)
        self.assertIn("oem", {c.source for c in plan.cells}, "the card licenses the column")
        self.assertEqual(plan.audit(), [])


class ThePlanIsPhysicallyPossible(unittest.TestCase):

    def test_the_tag_always_holds_what_the_row_is_about_to_read(self):
        """⛔ ONE T5577, SIXTEEN CREDENTIALS, THREE WRITERS. A read is attributed to whoever last
        wrote the tag (RULES.md §9); getting that wrong files the previous step's credential under
        this protocol."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("t55.pm3", "t55.cu1"),
                         readers=("rd.pm3", "rd.cu1"))
        self.assertEqual(plan.audit(), [])

    def test_the_cycle_costs_one_station_however_many_protocols(self):
        """⭐ THE POINT OF THE WHOLE MODEL. Write, read back, let the other device read, let it
        write, read that — four cells a protocol, every protocol, ONE arrangement."""
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("t55.pm3", "t55.cu1"),
                         readers=("rd.pm3", "rd.cu1"))
        self.assertEqual([b.station.name for b in plan.blocks], ["PM3+T55+CU1"])
        self.assertEqual(plan.interventions, 3)      # one setup, plus the null-sweep round trip

        full = [p for p in reg.TIER0.values() if p.cu_expect]
        by_protocol = {}
        for c in plan.cells:
            by_protocol.setdefault(c.protocol.key, set()).add((c.source, c.reader))
        for p in full:
            self.assertEqual(len(by_protocol[p.key]), 4, "%s should yield the full cycle" % p.key)
        # ...and the two with no Chameleon expectation keep only the Proxmark half of it.
        for key in ("hidprox", "ioprox"):
            self.assertEqual({r for _, r in by_protocol[key]}, {"rd.pm3"})

    def test_emulation_needs_its_own_station_because_the_tag_must_be_out(self):
        plan = tiny_plan(keys=reg.TIER0_ORDER, sources=("t55.pm3", "emu.cu1"), readers=("rd.pm3",))
        names = [b.station.name for b in plan.blocks]
        self.assertEqual(len(names), 2)
        self.assertTrue(any("T55" in n for n in names) and any("T55" not in n for n in names))

    def test_a_calibration_row_is_never_measured_after_what_it_licenses(self):
        for source in ("emu.cu1", "emu.cu2", "t55.cu1"):
            with self.subTest(source=source):
                plan = tiny_plan(keys=reg.TIER0_ORDER, sources=(source,), readers=("rd.pm3",))
                self.assertEqual(plan.audit(), [])

    def test_the_audit_catches_a_hand_broken_plan(self):
        """The invariant is asserted independently of the builder, so the two cannot drift."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",))
        for b in plan.blocks:
            b.ops = [o for o in b.ops if o.kind != "write"]
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
