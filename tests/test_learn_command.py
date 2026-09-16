"""`bench learn`, for every reader rather than only the Flipper.

⛔⛔ WHY THIS COMMAND MATTERS MORE THAN IT LOOKS. It is the only path from "a device printed this on
the bench" into the registry that records a session, a source and a transcript. While it served
`rd.flip` alone, the other three readers were filled in by hand — and a hand-edited constant has no
provenance, nothing to replay it against, and no `check_independence` to refuse it. `fdxb` carried a
decode marker the client never prints AND an expectation taken from the wrong artefact, each hiding
the other, for as long as both existed.
"""

import contextlib
import io
import unittest

from tests.helpers import make_devices, quiet, reg                     # noqa: F401
from benchmatrix import cli, learned, outcomes


class _Args:
    """The real parser's output, so a flag that stops existing breaks this test."""

    def __new__(cls, *argv):
        return cli.build_parser().parse_args(["learn", "--no-prompt", *argv])


class _ScriptedLearningBench(unittest.TestCase):
    """The command builds its own channels, so the test swaps them at the two points it makes them.

    ⚠ NOT A `Scripted` STANDING IN FOR THE WHOLE COMMAND — the command under test is the real one,
    and only the devices are fakes. A test that replaced `cmd_learn` would prove nothing about it.
    """

    #: ⚠ THE FAKE CANNOT INVENT THIS, AND MUST NOT. `Scripted.read` renders the expectation the
    #: registry holds for that reader, and the whole premise here is that there ISN'T one — so an
    #: unscripted Chameleon correctly says nothing. What a reader prints for a credential nobody
    #: has written down is exactly the thing only a device can supply, which is why the command
    #: exists. Shaped like the real `lf hid prox read`, with the registered marker in it.
    CU_HIDPROX = ("[+] HIDProx/H10301\n"
                  "[+] Card number...... 4567\n"
                  "[+] Facility code.... 123\n"
                  "[+] Raw.............. 2006ec0c86\n")

    def setUp(self):
        self.tmp = __import__("tempfile").mkdtemp()
        self.path = __import__("os").path.join(self.tmp, "learned.json")
        self.dev = make_devices()
        self.dev.cu1.answers[("hidprox", "t5577")] = self.CU_HIDPROX
        self._real = (cli.Pm3, cli._learn_device)
        cli.Pm3 = lambda **kw: self.dev.pm3
        cli._learn_device = lambda a, reader: {"rd.cu1": self.dev.cu1,
                                               "rd.flip": self.dev.flipper}[reader]

    def tearDown(self):
        cli.Pm3, cli._learn_device = self._real

    def _run(self, *argv):
        """⚠ STDOUT IS CAPTURED, NOT SUPPRESSED — `self.printed` is asserted on, because half of
        what this command produces IS its output: the proposals and the reasons it declined."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.cmd_learn(_Args("--learned", self.path, "--session", "S1", *argv))
        self.printed = buf.getvalue()
        return code, learned.load(self.path)


class LearningFromAnyReader(_ScriptedLearningBench):

    def test_a_chameleon_expectation_is_learned_and_keyed_to_its_reader(self):
        """⭐ `hidprox` and `ioprox` are the two tier-0 protocols with a Chameleon read arm and no
        expectation — 25 refused cells between them, and the reason the command was generalised."""
        code, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        self.assertEqual(code, 0)
        self.assertIn(("hidprox", "rd.cu1"), recs)
        rec = recs[("hidprox", "rd.cu1")]
        self.assertEqual(rec.reader, "rd.cu1")
        self.assertEqual(rec.source, "t55.pm3", "the gold writer, never an emulation")
        self.assertTrue(rec.evidence, "the transcript is the provenance")
        # ⚠ THE MATCHER'S OWN TEST, not a literal `in`. A credential can span lines — see the
        # joined proposal — and `observe` collapses whitespace to find it.
        self.assertIn(outcomes._flat(rec.value), outcomes._flat(rec.evidence),
                      "a value the matcher could not find could never match")

    def test_it_folds_into_cu_expect_in_a_later_session(self):
        _, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        protos = [p for p in reg.resolve(["hidprox"])]
        self.assertIsNone(protos[0].cu_expect, "the fixture is only interesting while it is unknown")
        out, notes = learned.apply(protos, recs, "A LATER SESSION")
        self.assertIsNotNone(out[0].cu_expect)
        self.assertEqual(out[0].expect_for("rd.cu1"), out[0].cu_expect)
        self.assertTrue(any("rd.cu1 expects" in n for n in notes), notes)

    def test_but_not_in_the_session_that_learned_it(self):
        """⛔ RULES.md §8. Comparing a calibration row against a value taken from that same row
        makes the control unfailable."""
        _, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        out, notes = learned.apply(reg.resolve(["hidprox"]), recs, "S1")
        self.assertIsNone(out[0].cu_expect)
        self.assertTrue(any(n.startswith("⛔") for n in notes), notes)

    def test_a_registered_value_is_never_overridden(self):
        """⚠ Learning fills a hole. If it could displace a corrected entry, a stale record would
        quietly undo the correction and the grid would not say so."""
        _, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        fixed = [reg.Protocol(**{**p.__dict__, "cu_expect": "SET BY HAND"})
                 for p in reg.resolve(["hidprox"])]
        out, notes = learned.apply(fixed, recs, "A LATER SESSION")
        self.assertEqual(out[0].cu_expect, "SET BY HAND")
        self.assertEqual(notes, [])


class WhatItRefusesToLearnFrom(_ScriptedLearningBench):
    def test_an_unconfirmed_wipe_records_nothing(self):
        """⛔ A read is attributable to the write only because the tag demonstrably held nothing a
        moment before (RULES.md §10). Without that, the value could be the previous credential."""
        self.dev.pm3.wipe_works = False
        _, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        self.assertEqual(recs, {})

    def test_a_write_the_proxmark_cannot_read_back_records_nothing(self):
        """⚠ The Proxmark checks its own work where a registered expectation lets it. A reader's
        rendering of a credential the tag does not carry is noise recorded forever."""
        self.dev.pm3.write_works = False
        _, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        self.assertEqual(recs, {})

    def test_a_reader_that_does_not_decode_records_nothing(self):
        """⛔ THAT IS A FINDING, NOT A VALUE. An expectation taken from output the decode marker
        never matched would license a reader that decoded nothing."""
        self.dev.cu1.answers[("hidprox", "t5577")] = "[+] nothing here at all"
        _, recs = self._run("-r", "rd.cu1", "-p", "hidprox")
        self.assertEqual(recs, {})
        self.assertIn("decode marker", self.printed)
        self.assertIn("FINDING", self.printed, "and the operator is told which kind of nothing")

    def test_the_flipper_still_uses_its_anchored_line(self):
        """⛔ RULES.md §6. The Flipper's success line has a shape worth pinning to, and matching on
        the protocol name alone once reported 10 successes out of 5 attempts."""
        p = reg.ALL["hidprox"]
        self.dev.flipper.answers[("hidprox", "t5577")] = "%s AABBCC\n" % p.flip_key
        _, recs = self._run("-r", "rd.flip", "-p", "hidprox")
        self.assertEqual(recs[("hidprox", "rd.flip")].value, "AABBCC",
                         "the bare hex, which flip_line() composes an expectation from")

    def test_and_records_nothing_when_that_line_is_absent(self):
        self.dev.flipper.answers[("hidprox", "t5577")] = "[+] Radio Key 112233\n"
        _, recs = self._run("-r", "rd.flip", "-p", "hidprox")
        self.assertEqual(recs, {}, "a different protocol's line is not this protocol's expectation")


if __name__ == "__main__":
    unittest.main()


class WhatItProposes(unittest.TestCase):
    """⛔ THE PROPOSAL IS A SUGGESTION WITH A PERSON BEHIND IT, but a bad default is still bad —
    `--no-prompt` takes the first, and the operator reading a list reads the top of it hardest."""

    PM3_FDXB = ("[+] FDX-B / ISO 11784/5 Animal\n"
                "[+] Animal ID......... 999-000000001337\n"
                "[+] Animal bit set?... False\n"
                "[+] Raw............... 9C A0 00 00 03 9F 00 00 DB 59 00 00 00\n")
    CU_HIDPROX = ("[+] HIDProx/H10301\n[+] Card number...... 4567\n"
                  "[+] Facility code.... 123\n[+] Raw.............. 2006ec0c86\n")

    #: What the Chameleon really printed at the learning prompt, 2026-09-15 — banner, mode switch,
    #: our own research-build commentary, and the credential split across two lines.
    CU_REAL = ("{ Chameleon Ultra connected: v2.2 }\n"
               "Switch to {  Tag Reader  } mode successfully.\n"
               "HIDProx/HID H10301 26-bit\n"
               "1 other layout also fits: Indala 26-bit — the Proxmark prints them all.\n"
               "⚠ no format pinned — this is the FIRST layout that fits, not the only one.\n"
               "FC: 123\nCN: 4567\n")

    def test_every_proposal_can_actually_match(self):
        """⛔ A proposal validated by a different rule than the one that grades it is a bug offered
        as a choice — so this asks the matcher, not a literal `in`."""
        for text in (self.PM3_FDXB, self.CU_HIDPROX, self.CU_REAL):
            for c in learned.candidates(None, text):
                self.assertIn(outcomes._flat(c), outcomes._flat(text))

    def test_a_short_token_does_not_outrank_a_long_one(self):
        """⚠ `4567` was the top proposal for hidprox. Matching is a substring test, so four digits
        are satisfied by a raw frame, a timestamp or a facility code that happens to contain them."""
        got = learned.candidates(None, self.CU_HIDPROX)
        self.assertLess(got.index("2006ec0c86"), got.index("4567"))

    def test_a_credential_split_across_lines_is_offered_whole(self):
        """⛔⛔ FC AND CN TOGETHER ARE THE CARD. Every single-line proposal pins half of it and lets
        the other half be anything: `4567` reads EXACT off a tag with a different facility code,
        which merges WRONG into EXACT. Operator, at the prompt: "1 and 2 together are what define
        the credential"."""
        self.assertEqual(learned.candidates(None, self.CU_REAL)[0], "FC: 123 CN: 4567")

    def test_the_connection_banner_is_never_a_proposal(self):
        """⛔ `v2.2 }` WAS PROPOSAL 4. As an expectation it is satisfied by the Chameleon being
        plugged in, with no tag on the pad at all — a licence for an empty bench."""
        got = learned.candidates(None, self.CU_REAL)
        for bad in ("v2.2 }", "{ Chameleon Ultra connected: v2.2 }",
                    "Switch to {  Tag Reader  } mode successfully."):
            self.assertNotIn(bad, got)

    def test_nor_is_our_own_commentary_about_the_reading(self):
        """⚠ The research build annotates a decode. An annotation explains a reading; it is not
        one, and `no format pinned` is a warning about the very ambiguity being pinned here."""
        self.assertFalse([c for c in learned.candidates(None, self.CU_REAL)
                          if "format pinned" in c or "layout also fits" in c])

    def test_a_word_from_the_banner_is_not_proposed_first(self):
        """⚠ "Animal" — the last word of the FDX-B header — was once the top proposal: a real
        substring of real device output, and meaningless."""
        self.assertNotEqual(learned.candidates(None, self.PM3_FDXB)[0], "Animal")

    def test_a_flag_rendered_as_a_word_is_never_proposed(self):
        self.assertNotIn("False", learned.candidates(None, self.PM3_FDXB))

    def test_the_whole_labelled_line_is_offered_too(self):
        """⭐ Often the better answer: it pins the field the value came from, so the same digits
        turning up in a raw frame cannot satisfy it."""
        self.assertIn("Animal ID......... 999-000000001337",
                      learned.candidates(None, self.PM3_FDXB))

    def test_the_line_selector_keeps_what_the_evidence_summary_drops(self):
        """⛔ `outcomes._summarise` anchors on the expectation, which is the unknown here — asked to
        learn fdxb it returned the banner and the raw and threw away the answer."""
        lines = learned.value_lines(self.PM3_FDXB)
        self.assertTrue(any("Animal ID" in l for l in lines))
        self.assertFalse(any("Session log" in l for l in lines))


class WhatItRefusesToEvenAttempt(_ScriptedLearningBench):
    """⛔ A FIRMWARE FACT IS REFUSED BY NAME, NOT DISCOVERED BY CRASHING. `em410x_electra` has no
    Chameleon scan command — the firmware emulates and clones it and cannot read it, one of the row
    shapes SCOPE.md §B exists to record. Asking the Chameleon to learn it raised a `DeviceError`
    from the middle of a station, after the tag had been wiped and written."""

    def test_a_protocol_the_reader_cannot_read_is_refused_before_the_bench_is_touched(self):
        code, recs = self._run("-r", "rd.cu1", "-p", "em410x_electra")
        self.assertEqual(code, 0, "a firmware fact is not an error exit")
        self.assertEqual(recs, {})
        self.assertIn("no Chameleon read command", self.printed)
        self.assertNotIn("✎", self.printed, "no station was set up and no tag was written")

    def test_and_the_learnable_ones_alongside_it_still_run(self):
        """⚠ One impossible cell must not take the session with it."""
        _, recs = self._run("-r", "rd.cu1", "-p", "em410x_electra", "-p", "hidprox")
        self.assertIn(("hidprox", "rd.cu1"), recs)
        self.assertNotIn(("em410x_electra", "rd.cu1"), recs)
