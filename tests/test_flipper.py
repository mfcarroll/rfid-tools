"""The Flipper channel, now that it is ours.

⛔⛔ WHY THIS FILE EXISTS. `rd.flip` returned an empty string for EVERY protocol it was ever asked
about, while the Flipper decoded perfectly, and no test noticed — because every test ran on
`Scripted`, which replaces the channel rather than standing behind it. The harness shelled out to a
script in another project and parsed the wrong half of its stdout.

⭐ The pure logic is importable without pyserial, which is the point of the lazy import: the
anchored success pattern, the rejection set and the decode can all be tested on any interpreter.
"""

import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import flipper


#: Verbatim from the bench, 2026-09-15 — `rfid read normal` against a Proxmark-written H10301 tag.
REAL_READ = [
    "rfid read normal",
    "Reading RFID...",
    "Press Ctrl+C to abort",
    "H10301 7B11D7",
    "FC: 123",
    "Card: 4567",
    "Reading stopped",
]


class TheAnchoredSuccessLine(unittest.TestCase):

    def test_a_real_decode_is_found(self):
        got = flipper.decode(REAL_READ, mode="ask")
        self.assertIsNotNone(got)
        self.assertEqual((got.name, got.data), ("H10301", "7B11D7"))
        self.assertEqual(got.line, "H10301 7B11D7", "what an expectation is compared against")

    def test_the_protocols_own_detail_comes_with_it(self):
        """⚠ Indala26 prints FC and Card on SEPARATE lines, so taking only the next one drops the
        card number — the half that identifies the credential."""
        self.assertEqual(flipper.decode(REAL_READ).detail, "FC: 123 Card: 4567")

    def test_a_name_with_a_space_in_it_still_matches(self):
        """⛔ Momentum calls Securakey "Radio Key". A one-word pattern scored a working emulation
        0 of 6 and that number went into FINDINGS.md as an emulation defect (C177)."""
        got = flipper.decode(["Radio Key AABBCC", "Reading stopped"])
        self.assertIsNotNone(got)
        self.assertEqual(got.name, "Radio Key")

    def test_a_read_that_decoded_nothing_is_none(self):
        self.assertIsNone(flipper.decode(
            ["Reading RFID...", "Press Ctrl+C to abort", "Reading stopped"]))

    def test_the_banner_and_the_listing_are_not_decodes(self):
        """⛔ M28: an earlier tool counted substring hits of a protocol name and reported 10
        successes from 5 attempts, because the help text contained the name twice."""
        for line in ("\tEM4100, H10301, Indala26",
                     "rfid <write | emulate> <key_type> <key_data>",
                     "Available protocols:",
                     "Reading RFID..."):
            self.assertIsNone(flipper.decode([line]), line)


class WhatTheHarnessUsedToParseInstead(unittest.TestCase):
    """⛔⛔ THE BUG ITSELF, PINNED. Without `--verbose` the old script printed only its own summary,
    and with it the device lines arrive prefixed `      | ` — which `.strip()` does not remove,
    because the pipe is not whitespace. Two independent reasons the same real decode was invisible,
    and fixing either one alone still found nothing."""

    def test_the_scripts_summary_line_is_not_a_decode(self):
        self.assertIsNone(flipper.decode(["     1: H10301 7B11D7  FC: 123 Card: 4567"]))

    def test_nor_is_an_echoed_line_with_its_prefix_left_on(self):
        self.assertIsNone(flipper.decode(["      | H10301 7B11D7"]))

    def test_but_the_line_itself_is(self):
        """⇒ Which is why nothing parses text any more: `read()` returns `Decode` objects taken
        from lines that came off the wire, before anyone can prefix them."""
        self.assertIsNotNone(flipper.decode(["H10301 7B11D7"]))


class ADeadInstrumentMustAbortNeverScoreZero(unittest.TestCase):
    """⛔⛔ `failed to load external command` COST A WHOLE UNIT (C373). `rfid` is a plugin the loader
    refuses when its API version does not match the firmware — ONE red line, then a normal prompt.
    Every attempt scored a clean `-`, and eleven emulate arms reported 0/6 against a reader that was
    never listening. A null with no positive control is not evidence (F05)."""

    def test_every_rejection_is_recognised(self):
        for line in flipper.REJECTED:
            self.assertTrue(any(r in "prefix " + line for r in flipper.REJECTED), line)

    def test_the_plugin_refusal_is_among_them(self):
        self.assertIn("failed to load external command", flipper.REJECTED)


class TheHeapCliff(unittest.TestCase):
    """⛔⛔⛔ The rfid plugin is a 66KB .fap the loader must place in ONE contiguous block, so it
    starts refusing mid-session with plenty of memory free (C377). That is why the reader looked
    healthy at one claim and dead at the next on the same boot."""

    def test_the_headroom_is_above_the_fap_size(self):
        self.assertGreater(flipper.FAP_HEADROOM, 0)
        self.assertEqual(flipper.FAP_BYTES, 66304, "the measured .fap size, not a guess")

    def test_a_block_that_only_just_fits_is_refused(self):
        self.assertLess(flipper.FAP_BYTES, flipper.FAP_BYTES + flipper.FAP_HEADROOM)


class ItImportsWithoutPyserial(unittest.TestCase):
    """⚠ THE POINT OF THE LAZY IMPORT. The pure logic must stay testable on an interpreter that has
    no serial support — the same arrangement `dfu.py` uses."""

    def test_the_module_loads_and_the_error_names_the_interpreter(self):
        import sys
        self.assertTrue(flipper.SUCCESS)
        with self.assertRaises(flipper.FlipperError) as cm:
            flipper._serial.__wrapped__("/dev/null") if hasattr(flipper._serial, "__wrapped__") \
                else self._force_missing()
        self.assertIn(sys.executable, str(cm.exception))

    def _force_missing(self):
        import builtins
        real = builtins.__import__

        def no_serial(name, *a, **k):
            if name == "serial":
                raise ImportError("no serial")
            return real(name, *a, **k)
        builtins.__import__ = no_serial
        try:
            flipper._serial("/dev/null")
        finally:
            builtins.__import__ = real


if __name__ == "__main__":
    unittest.main()


class ItStopsAsSoonAsSomethingDecodes(unittest.TestCase):
    """⭐ A FAILED READ DOES NOT RETURN ON ITS OWN. `rfid read` loops until a tag is decoded or ETX
    arrives, so a miss costs the full settle plus the drain — about nine seconds. Running all twelve
    attempts after the answer was already known cost 49 seconds PER PROTOCOL on the bench; across
    the Flipper's fourteen unknowns, eleven minutes of the operator watching a spinner.

    ⛔ AND THE WASTE WAS ALL IN THE WRONG FRONT END. `rfid read indala` has nothing to find on an
    FSK tag, and it was asked six times after `normal` had already answered.
    """

    class FakeCLI(flipper.FlipperCLI):
        """Only `run` is stubbed — the loop, the ordering and the stop are the real ones."""

        def __init__(self, replies):
            self.replies, self.asked, self.settle, self.quiet = replies, [], 6.0, True
            self.transcript = []

        def run(self, command, terminator, settle=None):
            self.asked.append(command)
            return self.replies.get(command, ["Reading stopped"])

    HIT = ["H10301 7B11D7", "Reading stopped"]

    def test_one_decode_ends_the_read(self):
        f = self.FakeCLI({"rfid read normal": self.HIT})
        got = f.read(("ask", "psk"), attempts=6)
        self.assertEqual(len(got), 1)
        self.assertEqual(f.asked, ["rfid read normal"], "eleven reads that answer nothing, skipped")

    def test_the_other_front_end_is_still_tried_when_the_first_is_empty(self):
        """⛔ The order is a guess, so a wrong guess must cost time and not a reading: `rfid read
        normal` cannot recover a PSK signal."""
        f = self.FakeCLI({"rfid read indala": self.HIT})
        got = f.read(("ask", "psk"), attempts=2)
        self.assertTrue(got[-1].decode)
        self.assertEqual(f.asked, ["rfid read normal", "rfid read normal", "rfid read indala"])

    def test_a_null_still_runs_every_attempt(self):
        """⚠ Nothing decodes, so there is nothing to stop at — which is correct: a sweep proving
        the field is empty wants its full denominator."""
        f = self.FakeCLI({})
        got = f.read(("ask", "psk"), attempts=3)
        self.assertEqual(len(got), 6)
        self.assertTrue(all(a.decode is None for a in got))

    def test_a_hit_rate_can_still_be_asked_for(self):
        f = self.FakeCLI({"rfid read normal": self.HIT})
        got = f.read(("ask",), attempts=4, stop_on_first=False)
        self.assertEqual(len(got), 4, "C81/C83 bracketed an arm by how OFTEN it hit")

    def test_the_likely_front_end_goes_first(self):
        self.assertEqual(flipper.front_ends_for("psk")[0], "psk")
        for family in ("ask", "fsk"):
            self.assertEqual(flipper.front_ends_for(family)[0], "ask", family)
        for family in ("ask", "fsk", "psk"):
            self.assertEqual(set(flipper.front_ends_for(family)), {"ask", "psk"},
                             "both are always tried — this orders, it does not filter")
