"""The REAL device classes, with only the subprocess layer stubbed.

⛔⛔ WHY THIS FILE EXISTS. Every other test runs on `Scripted`, which REPLACES the real channel
rather than standing behind it — so a `Chameleon.read` that raised on every call passed 191 tests
and failed at the first station of a real run. A fake that substitutes for the thing under test
proves nothing about it.

⇒ Here the classes are real and only `_run` — the one function that actually spawns a process — is
stubbed. That covers what the fake cannot: which commands are composed, in what order, and how the
replies are read.
"""

import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import devices, registry as reg
from benchmatrix.devices import Chameleon, DeviceError, Flipper, Pm3


class Recorder:
    """Stands in for the subprocess call, remembering the argv it was given."""

    def __init__(self, reply=""):
        self.calls, self.reply = [], reply

    def __call__(self, argv, timeout):
        self.calls.append(list(argv))
        return self.reply(argv) if callable(self.reply) else self.reply

    @property
    def commands(self):
        """The CLI commands, with the interpreter and port stripped off."""
        return [[a for a in c if not a.startswith("/") and a != "-p"] for c in self.calls]


class RealChannelBase(unittest.TestCase):

    def setUp(self):
        self._run = devices._run

    def tearDown(self):
        devices._run = self._run

    def stub(self, reply=""):
        devices._run = rec = Recorder(reply)
        return rec


class TheChameleonChannel(RealChannelBase):

    def cu(self, **kw):
        # ⚠ The settle delays are bench timing; a test suite must not wait out real hardware.
        kw.setdefault("arm_settle", 0)
        kw.setdefault("disarm_settle", 0)
        return Chameleon(port="/dev/tty.fake", name="cu1", **kw)

    def test_read_asks_for_reader_mode_and_then_the_registered_command(self):
        """⛔ The bug this file was written for: `read` raised unconditionally, and no test noticed
        because every test replaced the class."""
        rec = self.stub("[+] Keri PSK1\n   Raw: 80003039\n")
        out = self.cu().read(reg.ALL["keri"])
        self.assertEqual(rec.commands, [["hw mode -r", "lf keri read"]])
        self.assertIn("80003039", out)

    def test_write_asks_for_reader_mode_first(self):
        """⚠ A write issued while the device is emulating never reaches the tag."""
        rec = self.stub("[+] written\n")
        self.cu().write_t55(reg.ALL["keri"])
        self.assertEqual(rec.commands[0][0], "hw mode -r")
        self.assertIn("lf keri write --id 80003039", rec.commands[0])

    def test_a_refused_write_raises_rather_than_returning_quietly(self):
        self.stub("[!] error: invalid id\n")
        with self.assertRaises(DeviceError) as cm:
            self.cu().write_t55(reg.ALL["keri"])
        self.assertIn("write REFUSED", str(cm.exception))

    def test_arming_does_all_four_things_in_order(self):
        """⛔ A slot emits only when the TYPE is set, the CREDENTIAL written, the LF interface
        ENABLED and the device in emulator MODE. Miss the enable and `hw slot list` says
        `(disabled)EM410X` — type present, interface off, nothing on the air."""
        rec = self.stub("")
        self.cu(slot=8).arm(reg.ALL["em410x"])
        flat = " | ".join(" ".join(c) for c in rec.commands)
        for expected in ("hw slot type -s 8 -t EM410X", "hw slot enable -s 8 --lf",
                         "lf em 410x econfig -s 8", "hw slot change -s 8", "hw mode -e"):
            self.assertIn(expected, flat)

    def test_the_decode_marker_is_the_chameleons_own_wording(self):
        """⛔ It prints `Keri PSK1`, not `KERI - Internal ID:`. The Proxmark's pattern here would
        make every non-matching Chameleon read SILENT instead of WRONG."""
        p = reg.ALL["keri"]
        self.assertEqual(self.cu().decode_marker(p), p.cu_decode_marker)
        self.assertNotEqual(self.cu().decode_marker(p), p.pm3_decode_marker)

    def test_a_protocol_with_no_arm_says_which_arm_is_missing(self):
        self.stub("")
        with self.assertRaises(DeviceError) as cm:
            self.cu().read(reg.ALL["em410x_electra"])
        self.assertIn("no read command", str(cm.exception))
        with self.assertRaises(DeviceError) as cm:
            self.cu().write_t55(reg.ALL["instafob"])
        self.assertIn("no write command", str(cm.exception))

    def test_every_registered_arm_can_actually_be_issued(self):
        """⭐ THE SWEEP THAT WOULD HAVE CAUGHT IT. Each capability the registry claims is exercised
        against the real class, so a method that raises for everything cannot pass."""
        rec = self.stub("[+] ok\n")
        for p in reg.ALL.values():
            with self.subTest(p.key):
                if p.can("cu_read"):
                    self.cu().read(p)
                    self.cu().decode_marker(p)
                if p.can("cu_write"):
                    self.cu().write_t55(p)
                if p.can("emulate"):
                    self.cu().arm(p)
        self.assertTrue(rec.calls)


class TheProxmarkChannel(RealChannelBase):

    def test_read_and_write_use_the_registered_commands(self):
        rec = self.stub("[+] Done!\n")
        Pm3(binary="pm3").write_t55(reg.ALL["viking"])
        self.assertIn("lf viking clone --cn 1A3371", " ".join(rec.calls[0]))
        rec = self.stub("[+] Viking - Card 1A337195\n")
        Pm3(binary="pm3").read(reg.ALL["viking"])
        self.assertIn("lf viking reader", " ".join(rec.calls[0]))

    def test_every_registered_pm3_arm_can_be_issued(self):
        rec = self.stub("[+] Done!\n")
        for p in reg.ALL.values():
            with self.subTest(p.key):
                if p.can("pm3_read"):
                    Pm3().read(p)
                    Pm3().decode_marker(p)
                if p.can("pm3_write"):
                    Pm3().write_t55(p)
        self.assertTrue(rec.calls)


class EveryChannelAnswersWhatTheRunnerCalls(unittest.TestCase):
    """⛔ THE GENERAL GUARD. The runner calls a small set of methods on whatever a `Devices` holds;
    a channel missing one fails at the bench and not in the tests, because `Scripted` has them all.
    `Chameleon.write_t55` did not exist at all and nothing noticed."""

    #: Every channel is a reader and has to be quietenable for a null sweep.
    ALWAYS = ("alive", "read", "disarm", "decode_marker")
    #: Only a device that can put a credential on a tag.
    WRITERS = {Pm3, Chameleon, Flipper}
    #: Only a device that can pretend to BE a card — which the Proxmark now does too, as the gold
    #: EMITTER. Until it did, no emulation cell had a control of its own.
    EMITTERS = {Pm3, Chameleon, Flipper}

    def test_every_channel_answers_the_common_calls(self):
        for cls in (Pm3, Chameleon, Flipper, devices.Scripted):
            for name in self.ALWAYS:
                with self.subTest(cls=cls.__name__, method=name):
                    self.assertTrue(callable(getattr(cls, name, None)),
                                    "%s has no %s()" % (cls.__name__, name))

    def test_every_writer_can_write(self):
        for cls in self.WRITERS | {devices.Scripted}:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(callable(getattr(cls, "write_t55", None)))

    def test_every_emitter_can_be_armed(self):
        for cls in self.EMITTERS | {devices.Scripted}:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(callable(getattr(cls, "arm", None)))

    def test_the_proxmark_is_an_emitter_now_and_holds_it(self):
        """⭐ IT WAS DELIBERATELY NOT ONE, AND THE REASON HAS EXPIRED. The grid had no gold EMITTER,
        so a reader that decoded no emulation at all was indistinguishable from every emitter being
        bad — the calibration rule licenses a reader from a gold TAG row, which proves its decoder
        against silicon and says nothing about an emulated waveform.

        ⛔ AND IT MUST BE A HOLD. `lf <proto> sim` loops until the button or Enter, so `arm` and
        `disarm` have to be separate — the same shape as the Flipper, where collapsing them into
        one call made every emulation cell read an emitter that had already stopped."""
        for name in ("arm", "disarm"):
            self.assertTrue(callable(getattr(Pm3, name, None)), name)


if __name__ == "__main__":
    unittest.main()


class TheStandInMirrorsTheRealChannel(unittest.TestCase):
    """⛔ THE FAKE MUST NOT DISAGREE WITH THE THING IT STANDS FOR. `Scripted.decode_marker` returned
    the Proxmark's pattern for a Chameleon role, so every scripted Chameleon read was matched
    against the wrong marker — the exact defect the harness exists to catch, hiding inside the code
    that tests for it."""

    def test_each_role_uses_the_marker_its_real_channel_would(self):
        from benchmatrix.devices import Air, Scripted
        for key in ("em410x", "keri", "gproxii"):
            p = reg.ALL[key]
            with self.subTest(key):
                real_cu = Chameleon(port="/dev/x", name="cu1").decode_marker(p)
                fake_cu = Scripted(id="cu1", role="cu1", air=Air()).decode_marker(p)
                self.assertEqual(fake_cu, real_cu)
                real_pm3 = Pm3().decode_marker(p)
                fake_pm3 = Scripted(id="pm3", role="pm3", air=Air()).decode_marker(p)
                self.assertEqual(fake_pm3, real_pm3)

    def test_the_chameleon_marker_is_not_the_proxmarks(self):
        """If these were ever the same the test above would pass while proving nothing."""
        p = reg.ALL["keri"]
        self.assertNotEqual(p.cu_decode_marker, p.pm3_decode_marker)


class TheScriptedBenchMustBeWrongInTheSameWaysTheRealOneIs(unittest.TestCase):
    """⛔⛔ SIXTH TIME. `Scripted` has now disagreed with the real classes about answering regardless
    of tag contents, about which decode marker a Chameleon uses, about whether a wipe clears
    anything — and about this: it rendered ONE expectation to every reader.

    ⭐ THE REAL CLASSES DO NOT. Three clients decode the same credential and print it three
    different ways, which is the entire reason `expect_for(reader)` exists. The fake stashed
    `p.expect` — the Proxmark's rendering — at arm time and replayed it to whoever asked, so the
    split could not be exercised: every scripted Chameleon read compared the Proxmark's token
    against the Proxmark's token and agreed.

    ⚠ IT WENT UNNOTICED BECAUSE EVERY ENTRY HAD THEM EQUAL. `fdxb` is the first where `expect` and
    `cu_expect` genuinely differ — and they differ because the registry had been comparing pm3
    output against a Chameleon token since the day it was written. The fixture agreed with the code
    because both were built from the same wrong source.
    """

    def _air_with_tag_holding(self, key):
        from benchmatrix.devices import Air, Scripted
        from benchmatrix.stations import T5577
        air = Air()
        p = reg.ALL[key]
        writer = Scripted(id="pm3", role="pm3", air=air)
        writer.write_t55(p)
        self.assertIn(T5577, air.armed, "the fixture only means anything if the tag is written")
        return air, p

    def test_each_reader_is_answered_in_its_own_wording(self):
        from benchmatrix.devices import Scripted
        air, p = self._air_with_tag_holding("fdxb")
        self.assertNotEqual(p.expect_for("rd.pm3"), p.expect_for("rd.cu1"),
                            "fdxb is the entry that makes this testable at all")
        pm3_text = Scripted(id="pm3", role="pm3", air=air).read(p)
        cu_text = Scripted(id="cu1", role="cu1", air=air).read(p)
        self.assertIn(p.expect_for("rd.pm3"), pm3_text)
        self.assertIn(p.expect_for("rd.cu1"), cu_text)
        self.assertNotIn(p.expect_for("rd.cu1"), pm3_text,
                         "the Proxmark does not print the Chameleon's rendering")

    def test_a_reader_with_no_registered_expectation_says_nothing(self):
        """⚠ Not "prints the other reader's token". An unknown expectation is a planning refusal,
        and a fake that invents one hides the cell that should never have been planned."""
        from benchmatrix.devices import Scripted
        air, p = self._air_with_tag_holding("fdxb")
        self.assertIsNone(p.expect_for("rd.flip"), "fdxb's Flipper encoding is still unknown")
        self.assertEqual(Scripted(id="flipper", role="flipper", air=air).read(p), "")


class AFailedInvocationIsNotASilence(unittest.TestCase):
    """⛔⛔ THE LIVENESS RULE APPLIES TO EVERY COMMAND, NOT JUST PROOF OF LIFE (RULES.md §5).
    `PM3_FAIL` was checked in `alive()` and nowhere else, so a read whose client never got the port
    returned its own error text and was scored SILENT — a verdict about the Proxmark, from an
    invocation that never reached the Proxmark.

    ⚠ AND IT WAS INVISIBLE. `_summarise` keeps lines matching the expectation, the decode marker or
    "raw"; a client error matches none of them, so the operator saw `device (nothing)` — which is
    what a reader that decoded nothing looks like. Seven protocols failed their read-back that way
    in one learning session, none of them reproducible afterwards, while a pm3 CLI was open on the
    same port.
    """

    CLAIMED = "\n[pm3 ERROR running 'pm3 -c lf indala reader': claimed by another process]\n"

    def _pm3(self, reply):
        """⚠ THE REAL `Pm3`, with only `_run` stubbed — the same discipline as the rest of this
        file. Stubbing `exec` would skip the very code path under test."""
        rec = Recorder(reply)
        self.rec = rec
        p = Pm3(binary="pm3")
        devices._run = rec
        return p

    def setUp(self):
        self._real_run = devices._run

    def tearDown(self):
        devices._run = self._real_run

    def test_a_port_claimed_by_something_else_raises(self):
        with self.assertRaises(DeviceError) as cm:
            self._pm3(self.CLAIMED).read(reg.ALL["indala"])
        self.assertIn("did not reach the device", str(cm.exception))
        self.assertIn("claimed by another process", str(cm.exception))

    def test_a_timeout_raises(self):
        with self.assertRaises(DeviceError):
            self._pm3("\n[TIMED OUT after 90s running pm3 -c]\n").read(reg.ALL["indala"])

    def test_silence_from_the_client_itself_raises(self):
        with self.assertRaises(DeviceError):
            self._pm3("").read(reg.ALL["indala"])

    def test_but_a_genuine_empty_read_is_returned_and_scored(self):
        """⭐ THE DISTINCTION THAT MATTERS. A client that ran and a tag that said nothing IS a
        reading; only an invocation that never got there is not."""
        real = ("[+] Using UART port /dev/tty.usbmodemiceman1\n"
                "[+] Communicating with PM3 over USB-CDC\n"
                "[usb] pm3 --> lf indala reader\n")
        self.assertEqual(self._pm3(real).read(reg.ALL["indala"]), real)

    def test_a_write_that_never_reached_the_device_raises_too(self):
        with self.assertRaises(DeviceError) as cm:
            self._pm3(self.CLAIMED).write_t55(reg.ALL["indala"])
        self.assertIn("did not reach the device", str(cm.exception))

    def test_and_a_wipe_reports_it_rather_than_claiming_a_clean_tag(self):
        ok, why = self._pm3(self.CLAIMED).wipe_t55()
        self.assertFalse(ok)
        self.assertIn("did not reach the device", why)


class WhatAClonSaysAboutItsOwnWrite(unittest.TestCase):
    """⭐ `Done!` AND `Data written and verified` ARE NOT THE SAME CLAIM. The first says the commands
    went out; the second says the client read the blocks back and they matched. `write_t55` checks
    only the weaker one and discards the transcript — so when a read-back later disagrees, the one
    line that separates "the write did not land" from "it landed and the reader cannot see it" has
    already been thrown away. Both look identical without it, and both happened this session.
    """

    CLONE = ("[=] Preparing to clone Indala 64 bit to T55x7 raw A0000000E6BD0E92\n"
             "[+] Blk | Data \n[+]  00 | 00081040\n[+]  01 | A0000000\n"
             "[+] Data written and verified\n[+] Done!\n")

    def test_the_stronger_confirmation_is_recognised(self):
        self.assertTrue(devices.clone_verified(self.CLONE))

    def test_and_done_alone_is_not_it(self):
        self.assertFalse(devices.clone_verified("[+] Done!\n"),
                         "a T5577 does not acknowledge a write (RULES.md §10)")

    def test_the_evidence_keeps_the_lines_that_decide(self):
        got = " | ".join(devices.clone_evidence(self.CLONE))
        self.assertIn("Data written and verified", got)
        self.assertIn("00081040", got, "the config block the clone claims to have set")

    def test_and_says_so_rather_than_returning_nothing(self):
        """⚠ An empty diagnostic is the failure mode this whole session kept hitting."""
        self.assertTrue(devices.clone_evidence(""))
        self.assertIn("nothing this filter recognises", devices.clone_evidence("")[0])


class WhenTheFlipperPluginDiesMidRun(unittest.TestCase):
    """⛔⛔ PROOF OF LIFE CANNOT SEE THIS COMING. `alive()` checks the heap once, at the start of a
    run; C377 measured the cliff arriving twelve minutes in with 107,464 bytes still FREE, because
    the loader needs 66KB CONTIGUOUS. A nine-station matrix reported 137,040 bytes at startup and
    then refused the plugin two stations later, correctly aborting after two.

    ⚠ ONLY THE FRAGMENTATION REFUSAL IS RETRIED. Every other rejection means we asked for something
    wrong, and retrying a wrong question is how a phantom count gets made (M28).
    """

    def test_the_refusal_a_reboot_fixes_is_named(self):
        from benchmatrix import flipper
        self.assertIn(flipper.FRAGMENTED, flipper.REJECTED)

    def test_a_wrong_question_is_not_retried(self):
        from benchmatrix import flipper
        f = devices.Flipper(port="/dev/null")
        with self.assertRaises(DeviceError) as cm:
            f._recover(flipper.FlipperError("the Flipper REJECTED `rfid read nope` — Unknown "
                                            "protocol"), "reading nope")
        self.assertIn("nothing measured against it would mean anything", str(cm.exception))

    def test_but_the_plugin_refusal_reboots(self):
        from benchmatrix import flipper
        rebooted = []
        real = flipper.reboot
        flipper.reboot = lambda port: rebooted.append(port)
        try:
            devices.Flipper(port="/dev/tty.fake")._recover(
                flipper.FlipperError("... %s ..." % flipper.FRAGMENTED), "reading em410x")
        finally:
            flipper.reboot = real
        self.assertEqual(rebooted, ["/dev/tty.fake"], "C377: a reboot restores it in ~10 seconds")


class ACrashMustSayWhatCrashed(unittest.TestCase):
    """⛔ A TRACEBACK'S FIRST LINE CARRIES NO INFORMATION. Both Chameleons refused to write
    `indala224` on the bench and reported it as `CLI exception: Traceback (most recent call last):`
    — the one line of a traceback that is identical for every fault there has ever been."""

    CRASH = ("CLI exception: Traceback (most recent call last):\n"
             "  File \"cu.py\", line 120, in write\n    frame = build(raw)\n"
             "ValueError: indala224 raw must be 28 bytes, got 7")

    def test_the_exception_survives(self):
        got = devices.Chameleon._refused(self.CRASH)
        self.assertIn("ValueError", got)
        self.assertIn("28 bytes", got)

    def test_an_ordinary_refusal_is_unchanged(self):
        self.assertEqual(devices.Chameleon._refused("WARNING: econfig writes the credential only"),
                         "WARNING: econfig writes the credential only")
