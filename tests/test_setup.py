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
from benchmatrix.devices import Chameleon


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


class CrossedPortsAreCaughtAtRunTime(unittest.TestCase):

    def test_a_port_holding_the_wrong_silicon_fails_proof_of_life(self):
        """⛔ A replug between setup and run would otherwise attribute every arm to the wrong device
        and the wrong firmware build, and the radio check could not catch it."""
        cham = Chameleon(port="/dev/a", name="cu1", expect_chipid="A1B2C3D4")
        cham.exec = lambda *c, **k: (" - Device chip ID: E5F60718" if c[0] == "hw chipid"
                                     else "Chameleon Ultra, fw v2.2.0")
        ok, why = cham.alive()
        self.assertFalse(ok)
        self.assertIn("IS NOT THE DEVICE", why)
        self.assertIn("bench setup", why)

    def test_the_right_silicon_passes_and_says_so(self):
        cham = Chameleon(port="/dev/a", name="cu1", expect_chipid="A1B2C3D4")
        cham.exec = lambda *c, **k: (" - Device chip ID: a1b2c3d4" if c[0] == "hw chipid"
                                     else "Chameleon Ultra, fw v2.2.0")
        ok, why = cham.alive()
        self.assertTrue(ok, why)
        self.assertIn("confirmed", why)

    def test_no_recorded_chip_id_means_no_check(self):
        """Not every bench has run setup; the check is an upgrade, never a precondition."""
        cham = Chameleon(port="/dev/a", name="cu1")
        cham.exec = lambda *c, **k: "Chameleon Ultra, fw v2.2.0"
        self.assertTrue(cham.alive()[0])


if __name__ == "__main__":
    unittest.main()
