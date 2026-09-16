"""The registry has to be fit to grade with, and its three trust classes must stay apart."""

import re
import unittest

from tests.helpers import pm3_exact, pm3_wrong, reg
from benchmatrix.devices import FLIP_SUCCESS
from benchmatrix.outcomes import Outcome, observe


class ItValidates(unittest.TestCase):

    def test_tier0_is_complete_and_valid(self):
        """⭐ EIGHTEEN, NOT SIXTEEN. The firmware dispatches 18 emulate types (`lf_tag_em.c`); the
        first count came off `pm3grade.sh`'s arm list, which is a TEST SCRIPT and describes what has
        been run, not what exists."""
        reg.validate()
        self.assertEqual(len(reg.TIER0), 18)
        self.assertEqual(set(reg.TIER0), set(reg.TIER0_ORDER))
        self.assertIn("em410x_electra", reg.TIER0)
        self.assertIn("indala224", reg.TIER0)

    def test_the_read_and_clone_only_protocols_are_registered_as_such(self):
        """⛔ A DIFFERENT ROW SHAPE, NOT A MISSING PROTOCOL."""
        for key in ("fdxa", "paradox", "pyramid", "instafob"):
            with self.subTest(key):
                p = reg.ALL[key]
                self.assertEqual(p.tier, 1)
                self.assertFalse(p.can("emulate"), "%s has no emitter in the firmware" % key)
                self.assertTrue(p.can("cu_read"), "%s is scannable" % key)
        self.assertFalse(reg.ALL["instafob"].can("cu_write"), "instafob is scan-only")
        self.assertTrue(reg.ALL["paradox"].can("cu_write"))

    def test_electra_can_be_emulated_and_written_but_not_scanned(self):
        p = reg.ALL["em410x_electra"]
        self.assertTrue(p.can("emulate") and p.can("cu_write"))
        self.assertFalse(p.can("cu_read"), "there is no EM410X_ELECTRA_SCAN command")
        self.assertIn("em410x_electra", reg.NO_CU_SCAN)

    def test_a_missing_decode_marker_is_a_hard_error(self):
        """⛔ Without one, WRONG and SILENT are indistinguishable — the merge RULES.md §1 forbids."""
        broken = dict(reg.TIER0)
        broken["pac"] = reg.Protocol(**{**reg.TIER0["pac"].__dict__, "pm3_decode_marker": ""})
        with self.assertRaises(reg.RegistryError) as cm:
            reg.validate(broken)
        self.assertIn("WRONG and SILENT", str(cm.exception))

    def test_every_decode_marker_compiles_and_fires_on_a_real_decode(self):
        for p in reg.ALL.values():
            if not (p.pm3_decode_marker and p.expect):
                continue
            with self.subTest(p.key):
                rx = re.compile(p.pm3_decode_marker, re.IGNORECASE | re.MULTILINE)
                self.assertTrue(rx.search(pm3_exact(p)), "marker misses its own success line")
                self.assertFalse(rx.search("[!] no tag found\n"), "marker fires on silence")

    def test_unknown_protocol_names_are_an_error_not_a_silent_skip(self):
        with self.assertRaises(reg.RegistryError):
            reg.resolve(["em410x", "not-a-protocol"])


class TheThreeTrustClassesStayApart(unittest.TestCase):

    def test_the_unknown_flipper_expectations_are_honestly_absent(self):
        """⛔ `None` means "not known", never "approximate". Filling these in by deriving them from
        each protocol's encoder would be guessing at an answer the bench can be asked for."""
        unknown = {p.key for p in reg.ALL.values() if p.flip_expect is None}
        self.assertGreater(len(unknown), 8)
        self.assertNotIn("em410x", unknown, "the one protocol every channel spells the same")

    def test_known_flipper_expectations_match_the_armed_credential_width(self):
        """The six we claim to know are exactly those where the Chameleon arms the same bytes."""
        for p in reg.ALL.values():
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
        for p in reg.ALL.values():
            if not (p.pm3_decode_marker and p.expect):
                continue
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


class MarkersMatchWhatTheDevicesActuallyPrint(unittest.TestCase):
    """⛔ A marker derived from a FORMAT STRING in the source is a guess at how the value renders.
    `EM410X\\s*:` never fired, because the device prints `EM410X/64:` — and nothing noticed, because
    a byte-exact hit forces `decoded` True and so a CORRECT read masked it. A read that decoded the
    wrong value would have been reported SILENT, which is the merge the four outcomes forbid."""

    #: Lines captured from the bench, 2026-09-15.
    OBSERVED = {("em410x", "cu"): "EM410X/64: 2244668800",
                ("em410x", "pm3"): "[+] EM 410x ID 2244668800"}

    def test_each_observed_line_fires_its_marker(self):
        for (key, which), line in self.OBSERVED.items():
            with self.subTest(key=key, which=which):
                p = reg.ALL[key]
                marker = p.cu_decode_marker if which == "cu" else p.pm3_decode_marker
                self.assertTrue(re.search(marker, line, re.IGNORECASE | re.MULTILINE),
                                "%s marker %r does not match %r" % (which, marker, line))

    def test_the_marker_is_independent_of_the_value(self):
        """It has to fire on a decode of the WRONG credential — that is its entire purpose."""
        p = reg.ALL["em410x"]
        self.assertTrue(re.search(p.cu_decode_marker, "EM410X/64: deadbeefff", re.IGNORECASE))
        self.assertTrue(re.search(p.cu_decode_marker, "EM410X/16: 1122334455", re.IGNORECASE))


class ABadMarkerReportsItselfOnAGoodRun(unittest.TestCase):
    """⛔ A marker that never matches is invisible for as long as the reads keep being correct,
    because a byte-exact hit stands in for it. The day it matters is the day that reader decodes the
    WRONG value and the harness says SILENT. A good read is the only chance to catch it."""

    def test_the_raw_marker_result_is_recorded_separately_from_the_match(self):
        from benchmatrix.outcomes import observe
        p = reg.ALL["em410x"]
        got = observe("em410x", "t55.pm3", "rd.cu1", "EM410X/64: 2244668800",
                      p.cu_expect, r"THIS-NEVER-MATCHES")
        self.assertTrue(got.matched)
        self.assertTrue(got.decoded, "a match must still imply a decode happened")
        self.assertFalse(got.marker_fired, "but the marker's own answer is kept")

    def test_a_run_flags_it_without_failing_the_cell(self):
        from tests.helpers import EMITTERS, answers_all_exact, make_devices, quiet, runner
        from benchmatrix import plan as planning
        from benchmatrix.stations import Bench
        from benchmatrix.outcomes import Outcome
        broken = reg.Protocol(**{**reg.ALL["em410x"].__dict__,
                                 "cu_decode_marker": r"EM410X\s*:"})
        ans = {("em410x", e): "EM410X/64: 2244668800" for e in EMITTERS}
        plan = planning.build([broken], ["t55.pm3"], ["rd.cu1"], Bench())
        res = runner.run(plan, make_devices(answers=ans), interactive=False, session="S", out=quiet)
        self.assertTrue(all(c.outcome is Outcome.EXACT for c in res.cells),
                        "the cells are correct — it is the registry that is wrong")
        self.assertIn(("em410x", "rd.cu1"), res.bad_markers)
        self.assertIn("EM410X/64", res.bad_markers[("em410x", "rd.cu1")],
                      "it must quote what the device actually printed")

    def test_a_correct_marker_raises_no_complaint(self):
        from tests.helpers import EMITTERS, make_devices, quiet, runner
        from benchmatrix import plan as planning
        from benchmatrix.stations import Bench
        ans = {("em410x", e): "EM410X/64: 2244668800" for e in EMITTERS}
        plan = planning.build(reg.resolve(["em410x"]), ["t55.pm3"], ["rd.cu1"], Bench())
        res = runner.run(plan, make_devices(answers=ans), interactive=False, session="S", out=quiet)
        self.assertEqual(res.bad_markers, {})


class TheRecordKeepsWhatADiagnosisNeeds(unittest.TestCase):
    """⛔ A FIXED-LENGTH SLICE OF A TRANSCRIPT RECORDS THE BANNER. The Proxmark prints six lines
    before it says anything about the tag, so `text[:400]` preserved the session log path and cut
    off the `Raw:` value — which is exactly what is needed to correct a registry fault. Found while
    trying to fix four of them from the run record and being unable to."""

    REAL = ("[+] loaded `/Users/x/.proxmark3/preferences.json`\n"
            "[+] execute command from commandline: lf viking reader\n"
            "[=] Session log /Users/x/.proxmark3/logs/log_20260916.txt\n"
            "[+] Using UART port /dev/tty.usbmodemiceman1\n"
            "[+] Communicating with PM3 over USB-CDC\n"
            "[+] Max frame size: 624 bytes\n"
            "[+] Viking - Card 001A3371, Raw: F2001A3371000095")

    def test_the_decode_survives_and_the_banner_does_not(self):
        from benchmatrix.outcomes import _summarise
        kept = _summarise(self.REAL, "1A337195", r"Viking - Card")
        self.assertEqual(len(kept), 1)
        self.assertIn("Raw: F2001A3371000095", kept[0])
        joined = " ".join(kept)
        for noise in ("Session log", "UART port", "Max frame size", "preferences.json"):
            self.assertNotIn(noise, joined)

    def test_a_raw_line_is_kept_even_when_nothing_matched(self):
        """The failing case is the one that needs the evidence most."""
        from benchmatrix.outcomes import _summarise
        kept = _summarise(self.REAL, "DEADBEEF", r"NOTHING")
        self.assertTrue(any("Raw:" in k for k in kept))

    def test_the_observation_carries_it(self):
        from benchmatrix.outcomes import observe
        got = observe("viking", "t55.pm3", "rd.pm3", self.REAL, "1A337195", r"Viking - Card")
        self.assertTrue(got.summary)
        self.assertIn("Raw", got.summary[0])


class BenchDerivedValuesArePinned(unittest.TestCase):
    """⭐ These four came off the bench on 2026-09-15 (run 20260915_191849) after the gold column
    found that `pm3.write` and `expect` disagreed for each. They are the only entries in the
    registry promoted from "read out of the client's usage text" to "observed on hardware", and a
    silent edit back to a plausible-looking guess would cost another bench session to find."""

    OBSERVED = {
        # protocol      what the Proxmark actually wrote and read back
        "viking":    "1A337102",                    # Raw: F20000001A337102
        "jablotron": "0899AABBCC",                  # Raw: FFFF0899AABBCCE8
        "awid":      "011d87dd148e281111111111",
        "noralsy":   "BB0214FF0110002233070000",
    }

    def test_each_is_what_the_proxmark_produced(self):
        for key, value in self.OBSERVED.items():
            with self.subTest(key):
                self.assertEqual(reg.ALL[key].expect, value)

    def test_every_writer_puts_the_same_credential_on_the_tag(self):
        """⛔ THE FAULT THE GOLD COLUMN FOUND. `expect` came from the Chameleon's arm while
        `pm3.write` wrote something else, so the gold row could never match. Aligning only the
        expectation would fix the gold row and break `t55.cu*` instead."""
        for key in self.OBSERVED:
            with self.subTest(key):
                p = reg.ALL[key]
                self.assertEqual(p.expect.lower(), p.cu_expect.lower())
                self.assertIn(p.cu_expect.lower(), p.cu_write.lower())
                self.assertIn(p.cu_expect.lower(), p.cu_emulate.lower())

    def test_a_flipper_expectation_derived_from_the_old_credential_is_withdrawn(self):
        """⚠ viking and jablotron had one, derived from the credential that turned out to be wrong.
        It cannot be right for the new one, and a stale expectation is worse than none."""
        for key in ("viking", "jablotron"):
            with self.subTest(key):
                self.assertIsNone(reg.ALL[key].flip_expect)
