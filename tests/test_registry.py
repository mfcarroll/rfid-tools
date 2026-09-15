"""The registry has to be fit to grade with, and its three trust classes must stay apart."""

import re
import unittest

from tests.helpers import pm3_exact, pm3_wrong, reg
from benchmatrix.devices import FLIP_SUCCESS
from benchmatrix.outcomes import Outcome, observe


class ItValidates(unittest.TestCase):

    def test_tier0_is_complete_and_valid(self):
        reg.validate()
        self.assertEqual(len(reg.TIER0), 16)
        self.assertEqual(set(reg.TIER0), set(reg.TIER0_ORDER))

    def test_a_missing_decode_marker_is_a_hard_error(self):
        """⛔ Without one, WRONG and SILENT are indistinguishable — the merge RULES.md §1 forbids."""
        broken = dict(reg.TIER0)
        broken["pac"] = reg.Protocol(**{**reg.TIER0["pac"].__dict__, "pm3_decode_marker": ""})
        with self.assertRaises(reg.RegistryError) as cm:
            reg.validate(broken)
        self.assertIn("WRONG and SILENT", str(cm.exception))

    def test_every_decode_marker_compiles_and_fires_on_a_real_decode(self):
        for p in reg.TIER0.values():
            with self.subTest(p.key):
                rx = re.compile(p.pm3_decode_marker, re.IGNORECASE | re.MULTILINE)
                self.assertTrue(rx.search(pm3_exact(p)), "marker misses its own success line")
                self.assertFalse(rx.search("[!] no tag found\n"), "marker fires on silence")

    def test_unknown_protocol_names_are_an_error_not_a_silent_skip(self):
        with self.assertRaises(reg.RegistryError):
            reg.resolve(["em410x", "not-a-protocol"])


class TheThreeTrustClassesStayApart(unittest.TestCase):

    def test_ten_flipper_expectations_are_honestly_absent(self):
        """⛔ `None` means "not known", never "approximate". Filling these in by deriving them from
        each protocol's encoder would be guessing at an answer the bench can be asked for."""
        unknown = {p.key for p in reg.TIER0.values() if p.flip_expect is None}
        self.assertEqual(len(unknown), 10)
        self.assertNotIn("em410x", unknown, "the one protocol every channel spells the same")

    def test_known_flipper_expectations_match_the_armed_credential_width(self):
        """The six we claim to know are exactly those where the Chameleon arms the same bytes."""
        for p in reg.TIER0.values():
            if p.flip_expect is None:
                continue
            with self.subTest(p.key):
                armed = re.search(r"--(?:id|raw)\s+([0-9a-fA-F]+)", p.cu_emulate)
                self.assertIsNotNone(armed, "a known expectation needs a hex arm to have come from")
                self.assertEqual(p.flip_expect.lower(), armed.group(1).lower())

    def test_the_flipper_success_line_tolerates_a_name_with_a_space(self):
        """⛔ "Radio Key". A one-word pattern scored a working Securakey emulation 0 of 6, and that
        number reached FINDINGS.md as an emulation defect."""
        m = FLIP_SUCCESS.match("Radio Key 7FCB400001ADEA53")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Radio Key")

    def test_securakey_is_registered_under_the_flipper_name_not_the_protocol_name(self):
        self.assertEqual(reg.TIER0["securakey"].flip_key, "Radio Key")

    def test_hidprox_is_the_flippers_h10301_not_its_hidprox(self):
        """⚠ The Flipper has both, and they are different protocols — HIDProx is the generic arm
        SCOPE.md puts in tier 2."""
        self.assertEqual(reg.TIER0["hidprox"].flip_key, "H10301")
        self.assertEqual(reg.TIER0["hidprox"].cu_type, "HIDProx")


class WrongIsNeverMergedWithSilence(unittest.TestCase):

    def test_the_three_read_shapes_are_told_apart(self):
        for p in reg.TIER0.values():
            with self.subTest(p.key):
                mk = p.pm3_decode_marker
                exact = observe(p.key, "t55.pm3", "rd.pm3", pm3_exact(p), p.expect, mk)
                wrong = observe(p.key, "t55.pm3", "rd.pm3", pm3_wrong(p), p.expect, mk)
                silent = observe(p.key, "t55.pm3", "rd.pm3", "", p.expect, mk)
                self.assertIs(exact.outcome_if_licensed, Outcome.EXACT)
                self.assertIs(wrong.outcome_if_licensed, Outcome.WRONG)
                self.assertIs(silent.outcome_if_licensed, Outcome.SILENT)

    def test_ansi_colour_codes_do_not_hide_a_match(self):
        """pm3 wraps decoded values in `_GREEN_(...)`; a token with a space in it straddles them."""
        p = reg.TIER0["hidprox"]
        coloured = "[+] raw: 2006ec0c86aabbccddeeff00\n[+] FC: \x1b[32m123\x1b[0m  CN: \x1b[32m4567\x1b[0m\n"
        got = observe(p.key, "t55.pm3", "rd.pm3", coloured, p.expect, p.pm3_decode_marker)
        self.assertIs(got.outcome_if_licensed, Outcome.EXACT)

    def test_a_match_always_implies_a_decode(self):
        """An Observation that matched but decoded nothing is impossible; a bad marker must not
        be able to manufacture one."""
        p = reg.TIER0["pac"]
        got = observe(p.key, "t55.pm3", "rd.pm3", "PAC/Stanley - Card: CARD0042", p.expect,
                      r"this-marker-never-matches")
        self.assertTrue(got.decoded)
        self.assertIs(got.outcome_if_licensed, Outcome.EXACT)


if __name__ == "__main__":
    unittest.main()
