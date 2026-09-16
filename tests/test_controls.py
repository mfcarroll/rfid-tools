"""The controls that bracket every block: identity, null sweeps, A/B/A, and what voiding costs.

The identity rule, the A/B/A rule and the liveness rule (RULES.md §§3-5). Each cost a bench session
to learn, and each is tested for the behaviour the rule demands, not merely for "it returns
something".
"""

import unittest

from tests.helpers import (answers_all_exact, make_devices, obedient_operator, reg, runner,
                           tiny_plan)
from benchmatrix import identity
from benchmatrix.devices import Air
from benchmatrix.identity import NullSweep, sweeps_agree
from benchmatrix.outcomes import Outcome
from benchmatrix.stations import Bench, CU1, CU2


def quiet(*a, **k):
    pass


class TheIdentityCheck(unittest.TestCase):

    def test_the_probe_is_not_the_em410x_arm(self):
        """⛔ Two different questions that share a read command. If the probe used the `em410x` key,
        a probe read could be filed as an em410x result and vice versa."""
        self.assertEqual(identity.probe_protocol(CU1).key, identity.PROBE_KEY)
        self.assertNotEqual(identity.probe_protocol(CU1).key, "em410x")
        self.assertNotEqual(identity.probe_protocol(CU1).expect,
                            identity.probe_protocol(CU2).expect)

    def test_the_wrong_chameleon_aborts_the_run(self):
        """The null arms cannot catch a SWAPPED device — the wrong one is just as silent."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3", "emu.cu1"))
        air = Air()

        def careless(station):
            # The operator puts Chameleon 2 wherever Chameleon 1 was asked for.
            air.in_stack = {CU2 if d == CU1 else d for d in station.stack}

        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x"])),
                           air=air, operator=careless)
        with self.assertRaises(runner.RunAborted) as cm:
            runner.run(plan, dev, interactive=False, session="S", out=quiet)
        self.assertIn("WRONG DEVICE", str(cm.exception))

    def test_a_second_emitter_in_the_field_is_a_different_fault(self):
        """Both answering is not the same as the wrong one answering, and is not reported as it."""
        from benchmatrix.stations import Bench, PM3, build_station
        air = Air(in_stack={PM3, CU1, CU2})
        dev = make_devices(air=air)
        station = build_station({PM3, CU1}, Bench())        # CU2 is meant to be OUT of this stack
        res = identity.check(station, dev, {CU1: dev.cu1, CU2: dev.cu2})
        self.assertFalse(res.ok)
        self.assertEqual(res.found, frozenset({CU1}))
        self.assertEqual(res.strays, frozenset({CU2}))
        self.assertIn("EXTRA EMITTER", identity.explain(res))


class TheNullSweeps(unittest.TestCase):

    def test_aba_agreement(self):
        clean = NullSweep("before")
        self.assertTrue(sweeps_agree(clean, NullSweep("after"))[0])
        dirty = NullSweep("after", frozenset({"pac"}))
        ok, why = sweeps_agree(clean, dirty)
        self.assertFalse(ok)
        self.assertIn("VOID, not degraded", why)
        # Both dirty in the same way is agreement — the bench did not CHANGE. It is still a bad
        # bench, which the opening sweep already aborted on; this function only compares.
        self.assertTrue(sweeps_agree(dirty, dirty)[0])

    def test_a_dirty_opening_sweep_aborts_before_anything_is_measured(self):
        """pm3grade.sh's rule, kept: a hit with nothing armed makes every arm below it worthless."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",))
        protos = reg.resolve(["em410x"])
        # A stray emitter that is never disarmed: it answers even during the sweep.
        air = Air()
        dev = make_devices(answers=answers_all_exact(protos), air=air)
        dev.cu1.disarm = lambda: None           # a stray emitter nothing can switch off
        dev.cu1.arm(protos[0])
        air.in_stack = None                     # everything armed is audible
        dev.operator = None                     # ...and no operator clears it
        with self.assertRaises(runner.RunAborted) as cm:
            runner.run(plan, dev, interactive=False, session="S", out=quiet)
        self.assertIn("ambient contamination", str(cm.exception))

    def test_a_passive_tag_is_physically_removed_for_the_sweep(self):
        """⛔ The bug the harness found in itself: a T5577 has no idle state, so disarming the
        emitters is not enough and the closing sweep voids the block that just wrote the tag."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",))
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x"])))
        res = runner.run(plan, dev, interactive=False, session="S", out=quiet)
        self.assertEqual(res.void_blocks, [], "the block must not void itself on its own tag")
        self.assertEqual([c.outcome for c in res.cells], [Outcome.EXACT])


class VoidingIsContagious(unittest.TestCase):

    def test_a_void_block_revokes_the_licences_it_issued(self):
        """⛔ Including rows measured in LATER blocks. A licence is a claim that the bench was stable
        while the control was taken; if that block turns out not to have been, the claim goes too."""
        protos = reg.resolve(["em410x"])
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3", "emu.cu1"))
        air = Air()
        dev = make_devices(answers=answers_all_exact(protos), air=air)

        # The operator leaves the tag on the pad for the CLOSING sweep of the calibration block
        # only, so that sweep disagrees with the opening one and the block voids.
        real = obedient_operator(air)
        state = {"nulls": 0}

        def sloppy(station):
            real(station)
            if "T55" not in station.name:       # a null arrangement: the tag has been taken out
                state["nulls"] += 1
                if state["nulls"] == 2:         # the CLOSING sweep of the first station
                    air.in_stack.add("t5577")   # ...but the operator left the tag in

        dev.operator = sloppy
        res = runner.run(plan, dev, interactive=False, session="S", out=quiet)
        self.assertTrue(res.void_blocks, "the disagreeing A/B/A must void its block")
        self.assertEqual(res.licences, {}, "a void block's licence must not survive it")
        self.assertTrue(all(c.outcome is Outcome.UNGRADED for c in res.cells))


class TheInstrumentMustBeAlive(unittest.TestCase):

    def test_a_dead_device_aborts_before_a_single_cell(self):
        """A silent reader and a silent emulator produce IDENTICAL numbers."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",))
        with self.assertRaises(runner.RunAborted):
            runner.run(plan, make_devices(alive=False), interactive=False, session="S", out=quiet)


class ProvenanceIsOnTheFace(unittest.TestCase):
    """⛔ A grid from scripted devices is indistinguishable from a bench grid once it is a table of
    ticks, and this project exists because a grid that looked like a result was not one."""

    def test_a_scripted_run_says_so_in_its_first_lines(self):
        from benchmatrix import grid
        protos = reg.resolve(["em410x"])
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3", "emu.cu1"))
        res = runner.run(plan, make_devices(answers=answers_all_exact(protos)),
                         interactive=False, session="S", out=quiet)
        self.assertNotEqual(res.provenance, "bench")
        head = grid.render(res, protos).split("legend")[0]
        self.assertIn("NOT A RESULT", head)
        self.assertIn("dry-run", grid.to_json(res, protos))


if __name__ == "__main__":
    unittest.main()


class InterruptingIsNormal(unittest.TestCase):
    """⛔ Stopping a run is a normal thing to do — hands full, something wrong on the bench, a cue
    that turned out to be for the wrong station. None of that deserves a traceback, and none of it
    may leave a device emulating."""

    def _plan(self):
        return tiny_plan(keys=("em410x", "viking"), sources=("t55.pm3", "emu.cu1"))

    def test_ctrl_c_becomes_an_abort_not_a_crash(self):
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x", "viking"])))
        calls = {"n": 0}

        def interrupt(station):
            calls["n"] += 1
            if calls["n"] >= 3:
                raise KeyboardInterrupt
        dev.operator = interrupt
        with self.assertRaises(runner.RunAborted) as cm:
            runner.run(self._plan(), dev, interactive=False, session="S", out=quiet)
        self.assertIn("interrupted by the operator", str(cm.exception))

    def test_the_partial_readings_come_back_with_the_abort(self):
        """Losing forty completed readings because the forty-first could not be trusted helps
        nobody — but what comes back must never look like a grid."""
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x", "viking"])))
        calls = {"n": 0}

        def interrupt(station):
            calls["n"] += 1
            if calls["n"] >= 4:
                raise KeyboardInterrupt
        dev.operator = interrupt
        try:
            runner.run(self._plan(), dev, interactive=False, session="S", out=quiet)
            self.fail("should have aborted")
        except runner.RunAborted as e:
            self.assertIsNotNone(e.result)
            self.assertTrue(e.result.cells)
            self.assertTrue(e.result.aborted)

    def test_the_bench_is_left_idle_whatever_went_wrong(self):
        """⛔ A device left emulating contaminates whatever runs next, and the operator cannot see
        it — the giveaway is a null sweep failing at the start of a session for no visible reason."""
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x", "viking"])))
        dev.cu1.arm(reg.TIER0["em410x"])
        self.assertIn("cu1", dev.air.armed)

        def interrupt(station):
            raise KeyboardInterrupt
        dev.operator = interrupt
        with self.assertRaises(runner.RunAborted):
            runner.run(self._plan(), dev, interactive=False, session="S", out=quiet)
        self.assertNotIn("cu1", dev.air.armed, "nothing may be left emulating after an abort")

    def test_a_faulted_run_also_leaves_the_bench_idle(self):
        """The cleanup is in a `finally`, so it happens for every exit, not just Ctrl-C."""
        dev = make_devices(alive=False)
        dev.cu1.alive_ok = False
        dev.cu2.arm(reg.TIER0["em410x"])
        with self.assertRaises(runner.RunAborted):
            runner.run(self._plan(), dev, interactive=False, session="S", out=quiet)
        self.assertEqual(dev.air.armed, {})


class TheOperatorIsNeverToldToUndoTheLastInstruction(unittest.TestCase):
    """⛔ An operator told to undo what they were just told to do stops trusting the cues, and the
    cues are the only thing keeping the bench and the plan in step."""

    def _output(self, keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",)):
        said = []
        plan = tiny_plan(keys=keys, sources=sources, readers=readers)
        dev = make_devices(answers=answers_all_exact(reg.resolve(list(keys))))
        runner.run(plan, dev, interactive=False, session="S",
                   out=lambda m="": said.append(str(m)))
        return said

    @staticmethod
    def _interventions(said):
        """Each rearrangement draws one diagram, so counting rigs counts the operator's work."""
        return [i for i, m in enumerate(said) if "Rig 1" in m]

    def test_the_tag_goes_on_after_the_null_sweep_not_before_it(self):
        said = self._output()
        # ⚠ ONLY THE TAG DRAWN INSIDE A RIG COUNTS. "set aside: ... the T5577 tag" names it too,
        # and in the very first diagram — matching that would test the opposite of the intent.
        tagged = [i for i, m in enumerate(said) if "( T5577 tag )" in m]
        before = next(i for i, m in enumerate(said) if "NULL BEFORE" in m)
        self.assertTrue(tagged, "the tag must appear in a diagram at some point")
        self.assertLess(before, min(tagged),
                        "the sweep must be taken before the tag is ever asked for")

    def test_what_must_not_be_on_the_bench_is_named(self):
        """⛔ The forgotten device is the one that ruins a run, and a removal spoken aloud is the
        easiest thing to miss. The diagram names it instead."""
        said = "\n".join(self._output())
        self.assertIn("set aside", said)
        self.assertIn("Chameleon 1", said, "a device not in the rig is listed by name")

    def test_a_tag_station_costs_three_interventions_and_no_more(self):
        """Arrange it empty, add the tag, take the tag out."""
        self.assertEqual(len(self._interventions(self._output())), 3)

    def test_only_the_tag_station_involves_a_tag(self):
        """⚠ An emulated source still needs its gold calibration row, which is a tag station — so
        the run has one. What must not happen is a tag drawn into the EMULATION rig."""
        from benchmatrix import plan as planning
        p = planning.build(reg.resolve(["em410x"]), ["emu.cu1"], ["rd.pm3"], Bench())
        tag_stations = [b.station.name for b in p.blocks if b.station.has_tag]
        emu_stations = [b.station.name for b in p.blocks if not b.station.has_tag]
        self.assertTrue(tag_stations, "the gold row needs a tag")
        self.assertTrue(emu_stations, "the emulated row must not have one")
        self.assertTrue(all("T55" not in n for n in emu_stations))

    def test_a_proxmark_in_the_stack_does_not_break_the_null_sweep(self):
        """`null_sweep` disarms everything in the stack and must not have to know which of those
        can emit — so every channel answers `disarm()`, the Proxmark's as a no-op."""
        from benchmatrix.devices import Pm3
        Pm3().disarm()
        self.assertEqual(len(self._interventions(self._output())), 3)


class OnlyPhysicalInstructionsAreSpoken(unittest.TestCase):

    def test_a_null_sweep_chimes_but_does_not_talk(self):
        """⛔ Saying "null before" out loud is noise that trains the operator to ignore the voice,
        which is precisely the channel a move cue depends on."""
        import benchmatrix.cues as c
        spoken, played = [], []
        say, play = c._say, c._play
        c._say, c._play = (lambda w, block=False: spoken.append(w)), played.append
        try:
            c.cue_check("null before")
            c.cue_move("take the tag out")
        finally:
            c._say, c._play = say, play
        self.assertEqual(spoken, ["take the tag out"])
        self.assertEqual(len(played), 2, "both still chime")


class AWriteMustSaySoItself(unittest.TestCase):
    """⛔ Without a positive check, a refused clone leaves the tag holding its previous credential,
    the read decodes nothing, and the harness reports "this reader cannot judge this protocol" — a
    bench verdict for a one-line registry error."""

    def _pm3(self, output):
        from benchmatrix.devices import Pm3
        pm3 = Pm3()
        pm3.exec = lambda *c, **k: output
        return pm3

    def test_a_confirmed_write_returns(self):
        self._pm3("[=] Preparing to clone Viking tag\n[+] Done!\n").write_t55(reg.TIER0["viking"])

    def test_an_unconfirmed_write_is_refused_rather_than_assumed(self):
        from benchmatrix.devices import DeviceError
        with self.assertRaises(DeviceError) as cm:
            self._pm3("usage: lf viking clone [-h] ...\n[!] ERROR: invalid card number\n") \
                .write_t55(reg.TIER0["viking"])
        self.assertIn("did not confirm a write", str(cm.exception))
        self.assertIn("still holds whatever it held before", str(cm.exception))

    def test_silence_is_not_success(self):
        from benchmatrix.devices import DeviceError
        with self.assertRaises(DeviceError):
            self._pm3("").write_t55(reg.TIER0["viking"])

    def test_the_reads_after_a_refused_write_are_not_scored(self):
        """They are skipped as "source not armed", never filed as the reader's failure."""
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",))
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x"])))
        from benchmatrix.devices import DeviceError

        def refuse(p):
            raise DeviceError("pm3: `lf em 410x clone` did not confirm a write.")
        dev.pm3.write_t55 = refuse
        res = runner.run(plan, dev, interactive=False, session="S", out=quiet)
        self.assertTrue(res.cells)
        for c in res.cells:
            self.assertIs(c.outcome, Outcome.UNGRADED)
            self.assertIn("never armed", c.note)


class AWriteIsNotDoneBecauseItReturned(unittest.TestCase):
    """⛔ RULES.md §10. `Done!` means the commands went out on the air. A T5577 does not acknowledge
    a write, so nothing in that reply says the credential landed — only a read-back can."""

    def test_a_silent_tag_is_a_write_failure_not_a_reader_failure(self):
        """With one reader it is ambiguous, and the harness says so instead of picking."""
        protos = reg.resolve(["em410x"])
        silent = {("em410x", e): "" for e in ("t5577", "cu1", "cu2", "flipper")}
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",))
        res = runner.run(plan, make_devices(answers=silent), interactive=False, session="S",
                         out=quiet)
        self.assertTrue(res.cells)
        for c in res.cells:
            self.assertIs(c.outcome, Outcome.UNGRADED)
            self.assertIn("nothing decoded anything at all", c.note)
            self.assertNotIn("cannot judge", c.note,
                             "a bench verdict must not be issued for an unwitnessed write")
        self.assertEqual(res.licences, {})

    def test_one_reader_seeing_it_settles_it_for_the_others(self):
        """⭐ A credential we chose cannot be conjured out of a tag that does not hold it. So one
        byte-exact read proves the write landed, and every OTHER reader's silence on the same tag
        becomes a genuine finding about that reader rather than an ambiguity."""
        protos = reg.resolve(["em410x"])
        deaf_cu1 = {("em410x", e): "" for e in ("t5577", "cu1", "cu2", "flipper")}
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3", "rd.cu1"))
        res = runner.run(plan, make_devices(answers=answers_all_exact(protos),
                                            cu1_answers=deaf_cu1),
                         interactive=False, session="S", out=quiet)
        pm3 = [c for c in res.cells if c.reader == "rd.pm3"]
        cu1 = [c for c in res.cells if c.reader == "rd.cu1"]
        self.assertTrue(all(c.outcome is Outcome.EXACT for c in pm3))
        self.assertTrue(cu1)
        for c in cu1:
            self.assertNotIn("nothing decoded", c.note,
                             "the Proxmark witnessed the write, so this is about the reader")

    def test_the_writer_reads_back_even_when_no_cell_asks_it_to(self):
        """A verify op: a read that produces no cell, whose only job is to witness the write."""
        from benchmatrix import plan as planning
        p = planning.build(reg.resolve(["em410x"]), ["t55.pm3"], ["rd.cu1"], Bench())
        kinds = [o.kind for b in p.blocks for o in b.ops]
        self.assertIn("verify", kinds)
        verifies = [o for b in p.blocks for o in b.ops if o.kind == "verify"]
        self.assertTrue(all(o.cell is None for o in verifies))
        self.assertTrue(all(o.device == "pm3" for o in verifies))

    def test_verification_survives_the_tag_being_carried_to_another_station(self):
        """⛔ The write happens at one station and the read at the next — that is the whole point of
        carrying a tag. Scoping verification to a block would make every carried tag look like a
        write that never landed."""
        from benchmatrix import plan as planning
        protos = reg.resolve(["em410x"])
        deaf_cu1 = {("em410x", e): "" for e in ("t5577", "cu1", "cu2", "flipper")}
        # The isolation phase is where a tag genuinely travels: written at one station, carried,
        # read at the next. Build that plan directly from a screened cell.
        from benchmatrix.outcomes import Cell
        screened = [Cell("em410x", "t55.pm3", "rd.cu1", Outcome.UNGRADED, None, "",
                         frozenset({"pm3"}))]
        p = planning.isolate(screened, Bench())
        self.assertGreater(len(p.blocks), 1, "the tag must be carried for this to be a test")
        self.assertIn("verify", [o.kind for b in p.blocks for o in b.ops],
                      "the write station must read its own work back")
        res = runner.run(p, make_devices(answers=answers_all_exact(protos), cu1_answers=deaf_cu1),
                         interactive=False, session="S", out=quiet)
        self.assertTrue(res.cells)
        for c in res.cells:
            self.assertNotIn("nothing decoded", c.note,
                             "the Proxmark witnessed it at the write station, one stop earlier")


class AWriterUnderTestIsNotCreditedWithAnothersWork(unittest.TestCase):
    """⛔ Every writer in the registry puts the SAME credential on the tag for a given protocol. So
    after the Proxmark has written it, a byte-exact read following the Chameleon's write is exactly
    what a write that did nothing would leave behind."""

    PROTOS = ("keri",)

    def _plan(self):
        from benchmatrix import plan as planning
        return planning.build(reg.resolve(list(self.PROTOS)), ["t55.pm3", "t55.cu1"],
                              ["rd.pm3", "rd.cu1"], Bench())

    def test_the_tag_is_wiped_before_the_writer_under_test(self):
        ops = [o for b in self._plan().blocks for o in b.ops]
        kinds = [(o.kind, o.device) for o in ops]
        wipe = next(i for i, k in enumerate(kinds) if k[0] == "wipe")
        cu_write = next(i for i, k in enumerate(kinds) if k == ("write", "cu1"))
        self.assertLess(wipe, cu_write, "the wipe must precede the write it protects")
        self.assertEqual(kinds[wipe][1], "pm3", "only the Proxmark wipes")

    def test_the_gold_write_needs_no_clearing(self):
        """The tag already holds a different protocol, and what a gold row claims is only that the
        tag carries the credential — not who put it there."""
        ops = [o for b in self._plan().blocks for o in b.ops]
        pm3_write = next(o for o in ops if o.kind == "write" and o.device == "pm3"
                         and o.protocol.key != "__park__")
        self.assertFalse(pm3_write.after_park)

    def test_a_station_without_the_proxmark_parks_on_a_distinct_credential_instead(self):
        """⚠ Weaker: it neither restores the config nor says anything about P if it fails — but the
        tag still demonstrably changed, and only the device under test touched it."""
        from benchmatrix import plan as planning
        p = planning.build(reg.resolve(["em410x"]), ["t55.cu1"], ["rd.cu2"], Bench())
        pm3less = [b for b in p.blocks if "PM3" not in b.station.name]
        self.assertTrue(pm3less, "the writer-under-test block has no Proxmark in it")
        kinds = [(o.kind, o.protocol.key) for b in pm3less for o in b.ops]
        self.assertNotIn("wipe", [k for k, _ in kinds], "nothing there can wipe")
        self.assertIn(("write", reg.PARK_KEY), kinds)
        park = reg.park_protocol()
        self.assertNotIn(park.expect, {q.expect for q in reg.TIER0.values()},
                         "the parking credential must not collide with a registry entry")

    def test_a_no_op_write_by_the_device_under_test_is_caught(self):
        """The whole point: the Chameleon's write does nothing, the tag keeps the parking
        credential, and the cells that claim to be about the Chameleon's writer go UNGRADED."""
        protos = reg.resolve(list(self.PROTOS))
        dev = make_devices(answers=answers_all_exact(protos))
        dev.cu1.write_t55 = lambda p: "ok"          # returns cheerfully, changes nothing
        res = runner.run(self._plan(), dev, interactive=False, session="S", out=quiet)
        cu_written = [c for c in res.cells if c.source == "t55.cu1"]
        self.assertTrue(cu_written)
        for c in cu_written:
            self.assertIs(c.outcome, Outcome.UNGRADED,
                          "a write that did nothing must not be scored EXACT")

    def test_an_unconfirmed_wipe_blocks_the_write_it_was_meant_to_protect(self):
        protos = reg.resolve(list(self.PROTOS))
        dev = make_devices(answers=answers_all_exact(protos))
        dev.pm3.wipe_works = False                  # returns, but the tag keeps its configuration
        res = runner.run(self._plan(), dev, interactive=False, session="S", out=quiet)
        cu_written = [c for c in res.cells if c.source == "t55.cu1"]
        self.assertTrue(cu_written)
        for c in cu_written:
            self.assertIs(c.outcome, Outcome.UNGRADED)
            self.assertIn("did not take", c.note)

    def test_a_wipe_is_confirmed_by_detect_not_by_silence(self):
        """⛔ A silent protocol decoder is weak evidence: a wiped tag, a tag off the pad and a dead
        field all look the same. `lf t55xx detect` answers positively — a chip replied, and what it
        is transmitting is the wiped configuration."""
        said = []
        protos = reg.resolve(list(self.PROTOS))
        runner.run(self._plan(), make_devices(answers=answers_all_exact(protos)),
                   interactive=False, session="S", out=lambda m="": said.append(str(m)))
        self.assertIn("tag wiped — detect reports the default configuration block",
                      "\n".join(said))

    def test_detect_output_is_what_decides_it(self):
        from benchmatrix.devices import Pm3
        pm3 = Pm3()
        pm3.exec = lambda *c, **k: ("[=] Begin wiping...\n[=]  Chip type......... T55x7\n"
                                    "[=]  Block0............ 000880E0 (auto detect)\n")
        self.assertTrue(pm3.wipe_t55()[0])

        pm3.exec = lambda *c, **k: ("[=] Begin wiping...\n[=]  Chip type......... T55x7\n"
                                    "[=]  Block0............ 00148040 (auto detect)\n")
        ok, why = pm3.wipe_t55()
        self.assertFalse(ok)
        self.assertIn("00148040", why)

        pm3.exec = lambda *c, **k: "[=] Begin wiping...\n[!] No known 125/134 kHz tag found\n"
        ok, why = pm3.wipe_t55()
        self.assertFalse(ok)
        self.assertIn("no tag answered", why)

    def test_the_gold_rows_are_unaffected_by_any_of_this(self):
        """The Chameleon's writer being untestable must not cost us the Proxmark's column."""
        protos = reg.resolve(list(self.PROTOS))
        res = runner.run(self._plan(), make_devices(answers=answers_all_exact(protos)),
                         interactive=False, session="S", out=quiet)
        gold = [c for c in res.cells if c.source == "t55.pm3"]
        self.assertTrue(gold)
        self.assertTrue(all(c.outcome is Outcome.EXACT for c in gold))


class AWrongCredentialIsLegibleOnOneReader(unittest.TestCase):
    """⭐ The registry's `pm3.write` strings were read out of the client's usage text and never run,
    so several are expected to disagree with `expect`. That has to arrive as a REGISTRY fault, not
    as an ambiguity — otherwise the most informative run available reports five shrugs."""

    def _run(self, answers, keys=("awid",), readers=("rd.pm3",)):
        from benchmatrix import plan as planning
        protos = reg.resolve(list(keys))
        plan = planning.build(protos, ["t55.pm3"], list(readers), Bench())
        return runner.run(plan, make_devices(answers=answers), interactive=False, session="S",
                          out=quiet)

    def test_a_decode_that_does_not_match_is_a_registry_fault(self):
        wrong = {("awid", e): "[+] AWID - len: 26 - Raw: 011d8171deadbeefdeadbeef"
                 for e in ("t5577", "cu1", "cu2", "flipper")}
        res = self._run(wrong)
        self.assertTrue(res.cells)
        for c in res.cells:
            self.assertIn("DECODED, but not what was written", c.note)
            self.assertNotIn("nothing decoded", c.note)

    def test_a_total_silence_is_still_ambiguous_on_one_reader(self):
        """The distinction the whole change rests on: decoding the wrong thing proves the write
        landed; decoding nothing proves nothing."""
        silent = {("awid", e): "" for e in ("t5577", "cu1", "cu2", "flipper")}
        res = self._run(silent)
        self.assertTrue(all("nothing decoded anything at all" in c.note for c in res.cells))

    def test_the_block_clears_the_tag_before_its_first_write(self):
        """⭐ Without it the FIRST protocol of a block is the one case where a wrong credential and
        a dead reader cannot be told apart, because the tag's prior contents are unknown."""
        from benchmatrix import plan as planning
        plan = planning.build(reg.resolve(["awid"]), ["t55.pm3"], ["rd.pm3"], Bench())
        kinds = [o.kind for b in plan.blocks for o in b.ops]
        self.assertEqual(kinds[0], "wipe", "the block must open by putting the tag in a known state")
        self.assertLess(kinds.index("wipe"), kinds.index("write"))


class WhatIsNotMeasuredIsSaidBeforeTheRunNotAfter(unittest.TestCase):
    """⛔ A PROTOCOL THAT NEVER APPEARS IN THE OUTPUT CANNOT BE TOLD FROM ONE THAT WAS FORGOTTEN.
    A plan-time refusal produces no ops, so the operator watches seventeen protocols scroll past
    with no way to know the eighteenth was deliberate — the reason was in the written grid, at the
    bottom, after the bench work was over."""

    def _run(self):
        from benchmatrix import plan as planning
        said = []
        protos = reg.resolve(["em410x", "em410x_electra"])
        plan = planning.build(protos, ["t55.pm3"], ["rd.pm3"], Bench())
        runner.run(plan, make_devices(answers=answers_all_exact(protos)), interactive=False,
                   session="S", out=lambda m="": said.append(str(m)))
        return said, plan

    def test_a_wholly_refused_protocol_is_named_up_front(self):
        said, _ = self._run()
        head = "\n".join(said[:6])
        self.assertIn("em410x_electra", head)
        self.assertIn("not measured at all", head)
        self.assertIn("no-expectation", head, "and why")

    def test_it_comes_before_any_measurement(self):
        said, _ = self._run()
        announced = next(i for i, m in enumerate(said) if "not measured at all" in m)
        first_cell = next((i for i, m in enumerate(said) if "EXACT" in m), len(said))
        self.assertLess(announced, first_cell,
                        "the last chance to notice a protocol has dropped out of the plan is "
                        "before the bench work, not after it")

    def test_the_grid_marks_a_refused_cell_rather_than_leaving_it_blank(self):
        from benchmatrix import grid
        said, plan = self._run()
        protos = reg.resolve(["em410x", "em410x_electra"])
        res = runner.run(plan, make_devices(answers=answers_all_exact(protos)),
                         interactive=False, session="S", out=quiet)
        md = grid.render(res, protos)
        row = [l for l in md.splitlines() if l.startswith("| em410x_electra")]
        self.assertTrue(row)
        self.assertIn("refsd", row[0], "a blank cell reads as missing data, not as a decision")
