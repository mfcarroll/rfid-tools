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
    #: Only a device that can pretend to BE a card. The Proxmark never does in this harness.
    EMITTERS = {Chameleon, Flipper}

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

    def test_the_proxmark_is_deliberately_not_an_emitter(self):
        """There is no `emu.pm3` source, and adding `arm()` here would invite one."""
        self.assertFalse(hasattr(Pm3, "arm"))


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
