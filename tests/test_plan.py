"""Plan-time refusals, move minimisation, and the physical facts the plan has to respect."""

import unittest
from unittest import mock

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
        #   no-read-arm    — the firmware has no scan command for it at all
        self.assertEqual({e.rule for e in plan.exclusions}, {"no-expectation", "no-read-arm"})
        electra = {e.rule for e in plan.exclusions if e.protocol == "em410x_electra"}
        self.assertEqual(electra, {"no-read-arm"},
                         "Electra has no EM410X_ELECTRA_SCAN — that is the reason for THIS column")

    def test_a_missing_expectation_is_never_reported_as_an_impossible_bench(self):
        """⛔ THE TWO NEED DIFFERENT THINGS DONE ABOUT THEM. "Unlicensable" is a verdict about the
        bench; "no expectation" is a note that nobody has looked yet, and its message must name
        the remedy.

        ⛔⛔ THIS TEST USED TO USE `em410x_electra` AND ITS PREMISE WAS REFUTED (2026-09-16).
        It asserted that the Proxmark "can both write and read" Electra and only the printed
        token was missing. The bench says otherwise: `lf em 410x reader` cannot distinguish
        Electra from plain `em410x` at all, so that column is PERMANENTLY refused and is the
        subject of its own test below. ⇒ the principle is unchanged and is now tested on a
        SYNTHETIC protocol, because after that measurement `em410x_electra` was the last real
        one with a missing pm3 expectation and there is no genuine example left to point at.
        """
        import dataclasses
        base = reg.TIER0["em410x"]
        unmeasured = dataclasses.replace(base, key="synthetic_unmeasured", expect=None)
        with mock.patch.dict(reg.ALL, {"synthetic_unmeasured": unmeasured}), \
                mock.patch.object(reg, "ORDER", list(reg.ORDER) + ["synthetic_unmeasured"]):
            plan = tiny_plan(keys=("synthetic_unmeasured",), sources=("t55.pm3",),
                             readers=("rd.pm3",))
        self.assertEqual(plan.cells, [])
        rules = {e.rule for e in plan.exclusions}
        self.assertEqual(rules, {"no-expectation"})
        why = " ".join(e.why for e in plan.exclusions)
        self.assertIn("go and measure", why,
                      "a refusal that is really a to-do must say so")
        self.assertIn("bench learn", why,
                      "a refusal that is really a to-do must name the remedy")

    def test_a_reader_that_cannot_DISTINGUISH_is_refused_permanently_not_queued(self):
        """⛔⛔ `em410x_electra` on `rd.pm3` is not *nobody has looked yet* — looking cannot
        answer it. Measured 2026-09-16: `lf em 410x clone --electra` writes the tag and prints
        `Electra 0x7e1eaaaaaaaaaaaa`, but `lf em 410x reader` then prints `EM 410x ID
        2244668800` and nothing else, and `reader -h` has no Electra flag at all.

        ⛔ AND THE TOKEN IS THE DANGER, NOT JUST THE ABSENCE: `2244668800` is byte-identical to
        plain `em410x`'s, so a registry that recorded it would let an `em410x` emission pass an
        `electra` cell and vice versa — a false pass built in by construction. So this refusal
        must NOT carry the to-do wording, or a future tick does exactly that.
        """
        plan = tiny_plan(keys=("em410x_electra",), sources=("t55.pm3",), readers=("rd.pm3",))
        self.assertEqual(plan.cells, [])
        self.assertEqual({e.rule for e in plan.exclusions}, {"gap:pm3-indistinguishable"})
        why = " ".join(e.why for e in plan.exclusions)
        self.assertIn("PERMANENT", why)
        self.assertNotIn("bench learn", why, "this is not a to-do and must not read as one")
        self.assertNotIn("go and measure", why.replace("do NOT go and measure", ""),
                         "it must not send anyone to measure an unanswerable question")

    def test_bench_scope_does_not_tell_anyone_to_learn_an_indistinguishable_protocol(self):
        """⛔ THE SAME INSTRUCTION LIVED ON A SECOND SURFACE FOR A DAY AFTER THE PLANNER LOST IT.

        The refusal above was fixed on 2026-09-17, but `bench scope`'s *expectations known*
        column falls back to "— none; `bench learn` them" whenever a protocol has no recorded
        token — and `expect=None` is THREE states, not one: unmeasured (learn it),
        unlicensable (the bench cannot), and indistinguishable (looking cannot answer). For
        Electra the fallback published exactly the to-do the planner had just stopped
        publishing, and following it builds in the false pass the registry row forbids.

        ⇒ this guards both directions: the indistinguishable protocol must NOT be sent to
        `bench learn`, and a genuinely unmeasured one still must be.
        """
        import argparse
        import io
        import contextlib
        from benchmatrix import cli

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.cmd_scope(argparse.Namespace(protocol=None))
        rows = {ln.split()[0]: ln for ln in out.getvalue().splitlines()
                if ln.startswith("  ") and len(ln.split()) > 2}

        electra = rows["em410x_electra"]
        self.assertNotIn("bench learn", electra,
                         "Electra's token cannot be learned — recording it is the false pass")
        self.assertIn("INDISTINGUISHABLE", electra, "and the reason has to be on the row")

        self.assertIn("bench learn", rows["instafob"],
                      "a genuinely unmeasured protocol must still be sent to measure it")

    def test_a_protocol_with_no_gold_writer_IS_unlicensable(self):
        """`fdxa`: the Proxmark has no recorded clone signature, so nothing can make a gold tag."""
        plan = tiny_plan(keys=("fdxa",), sources=("t55.cu1",), readers=("rd.pm3",))
        self.assertEqual(plan.cells, [])
        self.assertIn("unlicensable", {e.rule for e in plan.exclusions})

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
        # ⭐⭐ THREE, NOT FOUR, AND THE FOURTH WAS NEVER WORTH THE BENCH TIME. The cycle used to
        # claim `t55.cu1 → rd.cu1` as well — the Chameleon reading back its own write. A T5577's
        # state after a write is DIGITAL, so nothing of the writer survives into what the tag
        # transmits, and that cell is answered by (t55.cu1 → rd.pm3) plus (t55.pm3 → rd.cu1), both
        # of which are right here in the same station. Operator: "there's nothing additional to be
        # learned that a tag written *by* the chameleon can be read by the flipper."
        for p in full:
            self.assertEqual(len(by_protocol[p.key]), 3, "%s should yield the cycle" % p.key)
            self.assertNotIn(("t55.cu1", "rd.cu1"), by_protocol[p.key])
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


class ATagIsADigitalIntermediary(unittest.TestCase):
    """⭐⭐ WHICH MAKES MOST OF THE TAG GRID REDUNDANT, AND IT WAS BEING MEASURED ANYWAY.

    A T5577's state after a write is a set of configuration and data blocks; the tag transmits from
    those blocks and nothing of the writer survives into the emission. So `t55.X → rd.Y` asks what
    (t55.X → rd.pm3) and (t55.pm3 → rd.Y) have already answered between them.

    ⚠ THE OPERATOR SPOTTED IT ON THE BENCH, mid-run, looking at a station built to measure exactly
    those cells: "Flipper → Tag → Chameleon and Chameleon → tag → Flipper are already covered by
    PM → tag → Chameleon and Chameleon → tag → PM." Three stations and nine operator interventions
    to answer nothing new.

    ⛔ AND IT DOES NOT EXTEND TO EMULATION. An emulated waveform IS the emitter's analogue output,
    so every (emitter, reader) pair is a distinct question.
    """

    S = ["t55.pm3", "t55.cu1", "t55.cu2", "t55.flip", "emu.cu1", "emu.cu2", "emu.flip"]
    R = ["rd.pm3", "rd.cu1", "rd.cu2", "rd.flip"]

    def _plan(self, cross):
        return planning.build(reg.resolve(["em410x"]), self.S, self.R, Bench(tag_count=16),
                              cross=cross)

    def test_a_tag_cell_needs_the_reference_instrument_on_one_side(self):
        for c in self._plan(False).cells:
            if c.source.startswith("t55."):
                self.assertTrue(c.source == "t55.pm3" or c.reader == "rd.pm3",
                                "%s → %s has the Proxmark on neither side" % (c.source, c.reader))

    def test_but_every_emulation_pair_is_still_asked(self):
        """⛔ The analogue path is the whole question there."""
        emu = {(c.source, c.reader) for c in self._plan(False).cells if c.source.startswith("emu.")}
        for src, rdr in (("emu.flip", "rd.cu1"), ("emu.cu1", "rd.flip"), ("emu.cu2", "rd.cu1")):
            self.assertIn((src, rdr), emu)

    def test_the_refusal_names_the_two_cells_that_cover_it(self):
        covered = [e for e in self._plan(False).exclusions if e.rule == "covered"]
        self.assertTrue(covered)
        why = covered[0].why
        self.assertIn("rd.pm3", why)
        self.assertIn("--cross", why, "and how to get it back when a covering cell fails")

    def test_it_removes_whole_stations_not_just_cells(self):
        """⭐ THE SAVING IS IN SETUPS, WHICH IS THE SCARCE RESOURCE. Those cells were the only
        reason three of the stations existed."""
        lean, full = self._plan(False), self._plan(True)
        self.assertLess(lean.interventions, full.interventions)
        for name in ("FLIP+T55+CU1", "FLIP+T55+CU2", "CU1+T55+CU2"):
            self.assertNotIn(name, [b.station.name for b in lean.blocks])
            self.assertIn(name, [b.station.name for b in full.blocks])


class TheProxmarkAsAGoldEmitter(unittest.TestCase):
    """⭐ `emu.pm3` — THE CONTROL THE EMULATION HALF OF THE GRID NEVER HAD. A reader is licensed from
    a gold TAG row, which proves its decoder against silicon and says nothing about an emulated
    waveform. Without a known-good emitter, a reader that decodes NO emulation is indistinguishable
    from every emitter being bad.

    ⚠ ITS COMMANDS ARE CLASS 2 — the client's own documented `sim` examples with our credential
    substituted, never run. A wrong one fails at ARM time, which scores no cell.
    """

    def test_it_is_an_emulated_source_and_the_two_lists_agree(self):
        from benchmatrix.stations import EMULATED_SOURCES
        from benchmatrix.plan import EMULATED_ORDER
        self.assertIn("emu.pm3", EMULATED_SOURCES)
        self.assertEqual(set(EMULATED_ORDER), set(EMULATED_SOURCES),
                         "a new emitter added to one list and forgotten in the other loses cells")

    def test_the_proxmark_cannot_judge_its_own_emission(self):
        p = planning.build(reg.resolve(["em410x"]), ["t55.pm3", "emu.pm3"], ["rd.pm3"], Bench())
        self.assertNotIn(("emu.pm3", "rd.pm3"), [(c.source, c.reader) for c in p.cells])
        self.assertIn("self-judging", [e.rule for e in p.exclusions])

    def test_but_every_other_reader_is_asked(self):
        p = planning.build(reg.resolve(["em410x"]), ["t55.pm3", "emu.pm3"],
                           ["rd.pm3", "rd.cu1", "rd.cu2", "rd.flip"], Bench())
        got = {c.reader for c in p.cells if c.source == "emu.pm3"}
        self.assertEqual(got, {"rd.cu1", "rd.cu2", "rd.flip"})

    def test_a_protocol_with_no_sim_is_refused_by_name(self):
        """⛔ `lf em 410x sim` has no `--electra`, so nothing here may guess at one."""
        p = planning.build(reg.resolve(["em410x_electra"]), ["t55.pm3", "emu.pm3"], ["rd.cu1"],
                           Bench())
        self.assertIn("no-emitter", [e.rule for e in p.exclusions])

    def test_the_subcarrier_rule_still_applies_to_it(self):
        """⚠ It is the GOLD emitter, not a magic one: a subcarrier-dependent read arm judged against
        any emulation measures the bench, not the arm (RULES.md §2)."""
        p = planning.build(reg.resolve(["indala"]), ["t55.pm3", "emu.pm3"], ["rd.cu1"], Bench())
        self.assertIn("subcarrier", [e.rule for e in p.exclusions])


class ACellIsRefusedOrMeasuredNeverLost(unittest.TestCase):
    """⛔⛔ A REFUSAL IS A PUBLISHED DECISION; A DISAPPEARANCE IS A HOLE NOTHING NAMES. `_routine`
    walked a hardcoded tuple of emulated sources, so `emu.pm3` cells were created by `_cells`,
    covered by `choose_stations`, and then never given a read op — gone from the plan with no
    exclusion to explain them. `audit()` now refuses to hand back a plan that has lost one."""

    def test_audit_checks_every_requested_cell_reached_a_routine(self):
        p = planning.build(reg.resolve(["em410x"]), ["t55.pm3", "emu.pm3"],
                           ["rd.pm3", "rd.cu1", "rd.flip"], Bench())
        self.assertTrue(p.requested)
        self.assertEqual(p.audit(), [])
        planned = {c.key for c in p.cells}
        for c in p.requested:
            self.assertIn(c.key, planned)

    def test_and_says_so_when_one_is_missing(self):
        p = planning.build(reg.resolve(["em410x"]), ["t55.pm3"], ["rd.pm3"], Bench())
        ghost = planning.PlannedCell(reg.ALL["em410x"], "emu.cu2", "rd.flip")
        p.requested = list(p.requested) + [ghost]
        bad = p.audit()
        self.assertTrue(bad)
        self.assertIn("never measured", bad[0])


class TheBenchCanBeAGivenRatherThanAChoice(unittest.TestCase):
    """⭐ `--at` IS THE INVERSE OF THE USUAL QUESTION. The planner normally picks arrangements and
    asks the operator to build each one; for a rig left standing — or shared with another session —
    the useful question is what can be measured in the layout that EXISTS.

    ⛔ AND WHAT CANNOT IS REFUSED BY NAME. A small grid is fine; a grid with holes nobody can
    account for is not.
    """

    S = ["t55.pm3", "t55.cu1", "emu.pm3", "emu.cu1"]
    R = ["rd.pm3", "rd.cu1"]

    def _at(self, *stations):
        return planning.build(reg.resolve(["em410x"]), self.S, self.R, Bench(tag_count=16),
                              at=list(stations))

    def test_one_station_and_nothing_is_moved(self):
        p = self._at("PM3+T55+CU1")
        self.assertEqual([b.station.name for b in p.blocks], ["PM3+T55+CU1"])
        self.assertEqual(p.audit(), [])

    def test_a_name_is_read_the_way_the_grid_prints_it(self):
        from benchmatrix.stations import parse_station
        self.assertEqual(parse_station("PM3+T55+CU1", Bench()).name, "PM3+T55+CU1")
        self.assertEqual(parse_station("pm3 + cu1", Bench()).name, "PM3+CU1")

    def test_a_typo_is_refused_rather_than_quietly_selecting_another_rig(self):
        from benchmatrix.stations import StationError, parse_station
        with self.assertRaises(StationError):
            parse_station("PM3+NOPE", Bench())

    def test_what_the_layout_cannot_produce_is_refused_by_name(self):
        p = self._at("PM3+CU1")
        rules = {e.rule for e in p.exclusions}
        self.assertIn("not-in-this-layout", rules)
        why = [e.why for e in p.exclusions if e.rule == "not-in-this-layout"][0]
        self.assertIn("the T5577 tag", why, "it says what the cell would have needed")
        self.assertIn("PM3+CU1", why, "and what it was given")

    def test_a_tagless_layout_can_license_nothing(self):
        """⛔ THE GOLD ROW IS A CREDENTIAL WRITTEN ON A T5577. A station with no tag has nothing to
        calibrate against, so every cell is refused — and it must be refused at PLAN time, not left
        to grade as UNGRADED."""
        p = self._at("PM3+CU1")
        self.assertEqual(p.cells, [])
        self.assertTrue(p.exclusions)

    def test_a_self_judging_pair_is_refused_not_crashed_on(self):
        """⚠ `station_admits` asks what a cell needs, and asking that of a device pointed at its own
        antenna raises — so the layout check has to come AFTER the self-judging one."""
        p = self._at("PM3+CU1")
        self.assertIn("self-judging", {e.rule for e in p.exclusions})

    def test_several_layouts_may_be_named(self):
        p = self._at("PM3+T55+CU1", "PM3+CU1")
        self.assertEqual({b.station.name for b in p.blocks}, {"PM3+T55+CU1", "PM3+CU1"})
        self.assertEqual(p.audit(), [])


class ARemedyIsOnlyOfferedWhereItCanActuallyBeTaken(unittest.TestCase):
    """⛔⛔ THE `unlicensable` NOTE APPENDED ONE REMEDY TO FOUR DIFFERENT REASONS.

    It read "`bench learn` on the Proxmark side would settle it" whatever the reason was, and
    that is false for three of the four. For `fdxa` it named **the very command that refuses
    the request** — `cli._why_not_learnable` returns *no clone command, so there is no gold tag
    to learn from* — and for `instafob` it recommended writing a T5577 as the remedy for a
    T5577 being unable to hold it.

    ⇒ **A remedy offered for a reason it cannot remedy is worse than no remedy**: it sends the
    next session to spend a bench move proving the note wrong, and the note carries the
    authority of the tool.

    ⭐ The test that matters is the CROSS-SURFACE one, because this whole family of bug is one
    surface contradicting another: if the plan's note says `bench learn`, then `bench learn`
    must accept it. Nothing but an invariant catches that, since each surface is internally
    consistent.
    """

    READERS_SWEPT = ("rd.pm3", "rd.cu1", "rd.cu2", "rd.flip")
    SOURCES_SWEPT = ("t55.pm3", "emu.cu2", "t55.cu1", "emu.flip", "t55.flip")

    def _exclusions(self, key, reader, source):
        from tests.helpers import tiny_plan as _tp
        return _tp(keys=(key,), sources=(source,), readers=(reader,)).exclusions

    def _unlicensable(self, key, reader):
        return [e for e in self._exclusions(key, reader, "t55.pm3")
                if e.rule == "unlicensable"]

    def test_no_refusal_anywhere_recommends_a_learn_the_learn_command_would_refuse(self):
        """⭐⭐ THE INVARIANT, OVER EVERY RULE RATHER THAN ONE — WHICH IS WHAT MAKES IT AN AUDIT.

        This family of bug is one surface contradicting another, and each surface is
        internally consistent, so nothing but a cross-surface check finds it. The first version
        of this test swept `unlicensable` alone and guarded an EMPTY subset: every unlicensable
        protocol sits in a `cannot settle it` branch. Widened to every rule and every
        source/reader pair it guards **170 real refusals** that do recommend `bench learn`.

        ⇒ if a refusal says `bench learn`, `cli._why_not_learnable` must accept that
        protocol/reader. The phrase "cannot settle it" is the product's own opt-out and the
        sibling test below guards that it is used wherever it is due.

        ⭐ Swept when written: 0 contradictions across all four readers and five sources — so
        the four surfaces that published this instruction now agree.
        """
        from benchmatrix import cli
        recommended = 0
        for key in reg.ALL:
            for reader in self.READERS_SWEPT:
                for source in self.SOURCES_SWEPT:
                    for e in self._exclusions(key, reader, source):
                        if "bench learn" not in e.why or "cannot settle it" in e.why:
                            continue
                        recommended += 1
                        self.assertIsNone(
                            cli._why_not_learnable(reg.ALL[key], reader),
                            "%s/%s from %s (%s): the refusal says `bench learn` would settle "
                            "it and the learn command refuses it — two surfaces disagreeing"
                            % (key, reader, source, e.rule))
        self.assertGreater(recommended, 100,
                           "the sweep found almost nothing to check, so it is no longer an "
                           "audit — the plan or the fixture has changed shape")

    def test_every_cannot_settle_branch_says_so_in_the_same_words(self):
        """⛔ The invariant above is only as good as the phrase it keys on being used."""
        from benchmatrix import cli
        for key in reg.ALL:
            for reader in ("rd.pm3", "rd.cu1", "rd.flip"):
                for e in self._unlicensable(key, reader):
                    if cli._why_not_learnable(reg.ALL[key], reader) is None:
                        continue
                    self.assertIn("cannot settle it", e.why,
                                  "%s/%s cannot be learned, so the note must say so in the "
                                  "phrase the invariant keys on" % (key, reader))

    def test_each_unlicensable_reason_names_a_remedy_that_fits_it(self):
        fdxa = self._unlicensable("fdxa", "rd.pm3")
        self.assertTrue(fdxa, "fdxa has no clone signature, so it is unlicensable")
        self.assertIn("cannot settle it", fdxa[0].why)
        self.assertIn("clone signature", fdxa[0].why, "and say what would")

        insta = self._unlicensable("instafob", "rd.pm3")
        self.assertTrue(insta, "a T5577 cannot hold instafob")
        self.assertIn("genuine card", insta[0].why)
        self.assertIn("cannot settle it", insta[0].why,
                      "writing a T5577 cannot remedy a T5577 being unable to hold it")
