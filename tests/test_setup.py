"""Device identity: which physical device is on which port.

⛔ THIS IS THE FOUNDATION THE RADIO IDENTITY CHECK STANDS ON. That check arms `cu1` with a unique id
and asks a reader who is there — but `cu1` means *whatever CU1_PORT points at*. If the ports are
crossed it confirms the lie. The two cover different failure modes and neither substitutes for the
other.
"""

import os
import tempfile
import unittest

import tests.helpers  # noqa: F401  — sets sys.path and silences the cues
from benchmatrix import setup
from benchmatrix.devices import Chameleon, WrongDevice


class TheEnvFile(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), ".env")

    def test_round_trip(self):
        setup.write_env({"PM3": "/x/pm3", "CU1_PORT": "/dev/a", "CU1_CHIPID": "ABCD"}, self.path)
        got = setup.load_env(self.path)
        self.assertEqual(got["PM3"], "/x/pm3")
        self.assertEqual(got["CU1_CHIPID"], "ABCD")

    def test_comments_and_blanks_are_ignored(self):
        with open(self.path, "w") as fh:
            fh.write("# a comment\n\nCU1_PORT=/dev/a\nnot-a-pair\n")
        self.assertEqual(setup.load_env(self.path), {"CU1_PORT": "/dev/a"})

    def test_a_missing_file_is_not_an_error(self):
        self.assertEqual(setup.load_env(os.path.join(self.path, "nope")), {})

    def test_an_explicit_value_always_wins(self):
        """⚠ Otherwise `CU1_PORT=... ./bench run` does the opposite of what it looks like."""
        setup.write_env({"CU1_PORT": "/dev/from-file"}, self.path)
        os.environ["CU1_PORT"] = "/dev/explicit"
        try:
            setup.apply_env(self.path)
            self.assertEqual(os.environ["CU1_PORT"], "/dev/explicit")
        finally:
            del os.environ["CU1_PORT"]


class Classification(unittest.TestCase):

    def test_the_named_devices_are_separated_from_the_anonymous_ones(self):
        """The Proxmark and the Flipper say what they are in their product string. The Chameleons
        enumerate as a bare serial number, which is the whole problem."""
        flip, pm3, rest = setup.classify([
            "/dev/tty.usbmodemflip_Matthew1", "/dev/tty.usbmodemiceman1",
            "/dev/tty.usbmodemC3A1656543DE1", "/dev/tty.usbmodemF429364E46961"])
        self.assertEqual(flip, ["/dev/tty.usbmodemflip_Matthew1"])
        self.assertEqual(pm3, ["/dev/tty.usbmodemiceman1"])
        self.assertEqual(len(rest), 2)


class IdentifyingChameleons(unittest.TestCase):

    def setUp(self):
        self.asked = []
        self.blinked = []
        self._chip, self._blink = setup.chip_id, setup.blink
        setup.blink = lambda port, cli=None, reads=0: self.blinked.append(port)

    def tearDown(self):
        setup.chip_id, setup.blink = self._chip, self._blink

    def _chips(self, mapping):
        setup.chip_id = lambda port, cli=None, timeout=0: mapping.get(port)

    def _ask(self, answers):
        def ask(port, cid):
            self.asked.append(port)
            return answers.pop(0)
        return ask

    def test_a_known_chip_is_assigned_without_asking(self):
        """⭐ The blink dance is a one-time cost, not a per-session ritual to click through."""
        self._chips({"/dev/a": "A1B2C3D4", "/dev/b": "E5F60718"})
        found = setup.identify_chameleons(
            ["/dev/a", "/dev/b"], {"CU1_CHIPID": "A1B2C3D4", "CU2_CHIPID": "E5F60718"},
            ask=self._ask([]), out=lambda *a: None)
        self.assertEqual(found["cu1"], "/dev/a")
        self.assertEqual(found["cu2"], "/dev/b")
        self.assertEqual(self.asked, [], "nothing should have been asked")
        self.assertEqual(self.blinked, [], "nothing should have blinked")

    def test_an_unknown_chip_blinks_and_is_asked_about(self):
        self._chips({"/dev/a": "A1B2C3D4"})
        found = setup.identify_chameleons(["/dev/a"], {}, ask=self._ask(["cu2"]),
                                          out=lambda *a: None)
        self.assertEqual(found["cu2"], "/dev/a")
        self.assertEqual(found["cu2_chipid"], "A1B2C3D4")
        self.assertEqual(self.blinked, ["/dev/a"])

    def test_the_mapping_survives_the_ports_being_swapped(self):
        """⭐ THE POINT OF KEYING ON SILICON. The same two devices on each other's ports map the
        same way, with no operator involvement and no chance of a silent cross."""
        self._chips({"/dev/a": "E5F60718", "/dev/b": "A1B2C3D4"})     # swapped since last session
        found = setup.identify_chameleons(
            ["/dev/a", "/dev/b"], {"CU1_CHIPID": "A1B2C3D4", "CU2_CHIPID": "E5F60718"},
            ask=self._ask([]), out=lambda *a: None)
        self.assertEqual(found["cu1"], "/dev/b")
        self.assertEqual(found["cu2"], "/dev/a")
        self.assertEqual(self.asked, [])

    def test_two_devices_cannot_both_be_chameleon_one(self):
        self._chips({"/dev/a": "A1B2C3D4", "/dev/b": "E5F60718"})
        found = setup.identify_chameleons(["/dev/a", "/dev/b"], {},
                                          ask=self._ask(["cu1", "cu1"]), out=lambda *a: None)
        self.assertEqual(found, {}, "an impossible mapping is refused, not written")

    def test_a_port_that_is_not_a_chameleon_is_skipped(self):
        self._chips({"/dev/a": None, "/dev/b": "E5F60718"})
        found = setup.identify_chameleons(["/dev/a", "/dev/b"], {},
                                          ask=self._ask(["cu2"]), out=lambda *a: None)
        self.assertEqual(found["cu2"], "/dev/b")
        self.assertEqual(self.blinked, ["/dev/b"], "a non-Chameleon is never blinked at")


class PortsResolveThemselves(unittest.TestCase):
    """⭐ The identity is the silicon; the port is where it happens to be reachable today."""

    def setUp(self):
        self._chip, self._ports = setup.chip_id, setup.serial_ports
        self.path = os.path.join(tempfile.mkdtemp(), ".env")

    def tearDown(self):
        setup.chip_id, setup.serial_ports = self._chip, self._ports

    def _bus(self, mapping):
        setup.serial_ports = lambda: sorted(mapping)
        setup.chip_id = lambda port, cli=None, timeout=0: mapping.get(port)

    def test_the_cached_port_is_used_when_it_still_holds_the_right_device(self):
        self._bus({"/dev/a": "A1B2C3D4", "/dev/b": "E5F60718"})
        found = setup.resolve_chameleons(
            {"CU1_CHIPID": "A1B2C3D4", "CU1_PORT": "/dev/a",
             "CU2_CHIPID": "E5F60718", "CU2_PORT": "/dev/b"}, out=lambda *a: None,
            write_back=False)
        self.assertEqual(found, {"cu1": "/dev/a", "cu2": "/dev/b"})

    def test_a_replug_is_a_non_event(self):
        """⭐ The two devices swapped cables. Nothing is asked, nothing aborts — the labels follow
        their silicon."""
        self._bus({"/dev/a": "E5F60718", "/dev/b": "A1B2C3D4"})
        said = []
        found = setup.resolve_chameleons(
            {"CU1_CHIPID": "A1B2C3D4", "CU1_PORT": "/dev/a",
             "CU2_CHIPID": "E5F60718", "CU2_PORT": "/dev/b"}, out=said.append, write_back=False)
        self.assertEqual(found, {"cu1": "/dev/b", "cu2": "/dev/a"})
        self.assertTrue(any("re-resolved" in m for m in said))

    def test_a_device_that_is_not_on_the_bus_is_reported_not_guessed(self):
        self._bus({"/dev/a": "A1B2C3D4"})
        said = []
        found = setup.resolve_chameleons(
            {"CU1_CHIPID": "A1B2C3D4", "CU2_CHIPID": "E5F60718", "CU2_PORT": "/dev/b"},
            out=said.append, write_back=False)
        self.assertEqual(found, {"cu1": "/dev/a"})
        self.assertTrue(any("not on the bus" in m for m in said))


class EveryActionProvesItsOwnIdentity(unittest.TestCase):
    """⛔ A wrong-device answer is silent by construction — no error, no wrong exit code, just a
    confident reading from the neighbour. So the check rides along with the work, on every action."""

    def setUp(self):
        import benchmatrix.devices as d
        self.d = d
        self._run = d._run
        self.calls = []

    def tearDown(self):
        self.d._run = self._run

    def _answer(self, text):
        def fake(argv, timeout):
            self.calls.append(argv)
            return text
        self.d._run = fake

    def _cham(self, expect="A1B2C3D4"):
        return Chameleon(port="/dev/a", name="cu1", expect_chipid=expect)

    def test_the_identity_check_is_prepended_to_the_real_command(self):
        self._answer(" - Device chip ID: A1B2C3D4\n[+] EM 410x ID 2244668800\n")
        self._cham().exec("lf em 410x read")
        argv = self.calls[0]
        self.assertIn("hw chipid", argv)
        self.assertLess(argv.index("hw chipid"), argv.index("lf em 410x read"),
                        "identity must be proved before the action, not after")

    def test_one_process_carries_both(self):
        """⭐ Why it can be on every action: cu.py runs a list in ONE session with one connect, so
        the check costs an extra command on an open link, not another process."""
        self._answer(" - Device chip ID: A1B2C3D4\n[+] ok\n")
        self._cham().exec("hw mode -r", "lf keri read")
        self.assertEqual(len(self.calls), 1)

    def test_a_wrong_device_raises_at_the_action(self):
        self._answer(" - Device chip ID: E5F60718\n[+] EM 410x ID 2244668800\n")
        with self.assertRaises(WrongDevice) as cm:
            self._cham().exec("lf em 410x read")
        self.assertIn("IS NOT THE DEVICE", str(cm.exception))
        self.assertIn("A1B2C3D4", str(cm.exception))
        self.assertIn("E5F60718", str(cm.exception))

    def test_silence_about_identity_is_also_refused(self):
        """No answer is not the same as the right answer."""
        self._answer("[+] EM 410x ID 2244668800")
        with self.assertRaises(WrongDevice):
            self._cham().exec("lf em 410x read")

    def test_the_chip_id_line_never_reaches_the_decode_matcher(self):
        """⚠ A hex identifier in front of a reader's output is exactly what a byte-exact search
        trips over."""
        self._answer(" - Device chip ID: A1B2C3D4\n[+] EM 410x ID 2244668800\n")
        out = self._cham().exec("lf em 410x read")
        self.assertNotIn("A1B2C3D4", out)
        self.assertIn("2244668800", out)

    def test_probing_for_a_chip_id_does_not_check_one(self):
        """The bootstrap: you cannot verify identity with the command that discovers it."""
        self._answer(" - Device chip ID: A1B2C3D4\n")
        cham = Chameleon(port="/dev/a", name="cu1", expect_chipid="A1B2C3D4")
        self.assertEqual(cham.chipid(), "A1B2C3D4")
        self.assertEqual(self.calls[0].count("hw chipid"), 1,
                         "the probe must not verify itself against the answer it is fetching")

    def test_no_recorded_chip_id_means_no_check_and_says_so(self):
        """Not every bench has run setup; the check is an upgrade, never a precondition — but the
        absence is stated rather than passing silently."""
        self._answer("Chameleon Ultra, fw v2.2.0")
        ok, why = Chameleon(port="/dev/a", name="cu1").alive()
        self.assertTrue(ok)
        self.assertIn("no chip id recorded", why)


if __name__ == "__main__":
    unittest.main()
