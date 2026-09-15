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
