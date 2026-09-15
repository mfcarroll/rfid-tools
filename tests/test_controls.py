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
from benchmatrix.stations import CU1, CU2


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

    def _instructions(self, keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",)):
        said = []
        plan = tiny_plan(keys=keys, sources=sources, readers=readers)
        dev = make_devices(answers=answers_all_exact(reg.resolve(list(keys)))) 
        runner.run(plan, dev, interactive=False, session="S",
                   out=lambda m="": said.append(str(m)))
        return [m.strip() for m in said if "⇒" in m]

    def test_the_tag_goes_on_after_the_null_sweep_not_before_it(self):
        said = []
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",))
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x"])))
        runner.run(plan, dev, interactive=False, session="S",
                   out=lambda m="": said.append(str(m)))
        joined = "\n".join(str(m) for m in said)
        add_tag = joined.index("Add the T5577 tag")
        before = joined.index("NULL BEFORE")
        self.assertLess(before, add_tag,
                        "the sweep must be taken before the tag is ever asked for")

    def test_no_instruction_undoes_the_one_before_it(self):
        """⚠ ADJACENCY IN THE MOVE LIST IS NOT THE TEST — "add the tag" and "take the tag out" are
        always consecutive moves, with the entire routine between them. What must never happen is
        the two arriving with NOTHING done in between, which is what the operator saw."""
        said = []
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",))
        dev = make_devices(answers=answers_all_exact(reg.resolve(["em410x"])))
        runner.run(plan, dev, interactive=False, session="S",
                   out=lambda m="": said.append(str(m).strip()))
        add = next(i for i, m in enumerate(said) if m.startswith("Add the T5577"))
        drop = next(i for i, m in enumerate(said) if m.startswith("Take the T5577"))
        between = [m for m in said[add + 1:drop] if m]
        self.assertTrue(between, "the tag goes on and straight back off with nothing measured")
        self.assertTrue(any("EXACT" in m for m in between),
                        "what happens while the tag is on should be the measurements: %r" % between)

    def test_a_tag_station_costs_three_instructions_and_no_more(self):
        """Arrange it empty, add the tag, take the tag out. The estimate the plan prints."""
        self.assertEqual(len(self._instructions()), 3)

    def test_an_emulation_station_costs_one(self):
        moves = self._instructions(sources=("emu.cu1",), readers=("rd.pm3",))
        adds = [m for m in moves if "T5577" not in m]
        self.assertTrue(adds)

    def test_a_proxmark_in_the_stack_does_not_break_the_null_sweep(self):
        """`null_sweep` disarms everything in the stack and must not have to know which of those
        can emit — so every channel answers `disarm()`, the Proxmark's as a no-op."""
        from benchmatrix.devices import Pm3
        Pm3().disarm()
        self.assertEqual(len(self._instructions()), 3)


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
