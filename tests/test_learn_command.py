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
        # ⛔ AND IT MUST NOT CLAIM A FINDING. The Proxmark is in the stack loading the tag, so the
        # three live possibilities are a deaf reader, a wrong marker, and the crowding.
        self.assertNotIn("FINDING", self.printed)
        self.assertIn("RULES.md §7", self.printed, "the operator is told which kinds of nothing")

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


class TheDeviceLearnedFromMustBeTheDeviceNAMED(unittest.TestCase):
    """⛔⛔ THE WORST FAILURE THIS BENCH HAS, AND LEARNING IS THE WORST PLACE FOR IT. A wrong
    Chameleon answers confidently, with no error and no wrong exit code. A RUN that misattributes a
    device loses one grid; a LEARNING session that misattributes one records Chameleon 2's rendering
    as Chameleon 1's expectation, and every later run is graded against it.

    ⚠ FOUND ON A REAL LEARNING SESSION, from the harness's own warning: "no chip id recorded, so
    nothing checks that commands reach this device rather than the other one". `bench learn` had
    been given its own Chameleon-building shortcut that read `CU1_PORT` and set no `expect_chipid`,
    so the check that guards every run was absent from the one place it cannot be undone.
    """

    def setUp(self):
        # ⛔ NO BUS SCAN FROM A UNIT TEST. `_chameleons` re-resolves a port by chip id whenever one
        # is configured, which probes real serial devices — it did, and re-resolved the operator's
        # actual CU1 mid-suite. What is under test is whether the chip id reaches the channel, not
        # the resolver.
        self._resolve = cli.setup.resolve_chameleons
        cli.setup.resolve_chameleons = lambda known: {}

    def tearDown(self):
        cli.setup.resolve_chameleons = self._resolve

    def _args(self):
        return cli.build_parser().parse_args(["learn", "-r", "rd.cu1"])

    def test_the_chip_id_reaches_the_channel(self):
        import os
        was = {k: os.environ.get(k) for k in ("CU1_PORT", "CU1_CHIPID")}
        os.environ["CU1_PORT"], os.environ["CU1_CHIPID"] = "/dev/null", "31AFE73F8B158D64"
        try:
            dev = cli._learn_device(self._args(), "rd.cu1")
            self.assertEqual(dev.expect_chipid, "31AFE73F8B158D64",
                             "without this nothing proves the commands reached cu1")
            self.assertEqual(dev.name, "cu1")
            self.assertEqual(dev.id, "rd.cu1", "the reader id its expectations are keyed under")
        finally:
            for k, v in was.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_and_an_unconfigured_chameleon_stops_rather_than_guesses(self):
        """⚠ Not a default port. A guess here is a device misattribution with a transcript that
        looks completely normal."""
        import os
        was = {k: os.environ.pop(k, None) for k in ("CU1_PORT", "CU1_CHIPID")}
        try:
            with self.assertRaises(SystemExit) as cm:
                cli._learn_device(self._args(), "rd.cu1")
            self.assertIn("bench setup", str(cm.exception))
        finally:
            for k, v in was.items():
                if v is not None:
                    os.environ[k] = v


class ASilenceFromACrowdedStackIsNotAFinding(_ScriptedLearningBench):
    """⛔⛔ THE GOLD WRITER HAS TO BE IN THE STACK, SO EVERY LEARNING READ IS A CROWDED READ. The
    Proxmark must be present to make the tag, and it then sits directly under that tag, loading it,
    while another device tries to read. `bench learn` inherited none of RULES.md §7 and published
    the resulting silence as a firmware gap.

    ⚠ FOUR FALSE FINDINGS IN A ROW ON REAL HARDWARE — viking, jablotron, pac, hidprox, twelve failed
    reads each at ~50s apiece — and the operator then read the same tag on the same Flipper
    instantly with the Proxmark out of the stack.
    """

    def setUp(self):
        super().setUp()
        self.moves = []
        self._ask = cli.cues.ask
        cli.cues.ask = lambda prompt, spoken="", **kw: self.moves.append(spoken)

    def tearDown(self):
        cli.cues.ask = self._ask
        super().tearDown()

    def _retry(self, second_read):
        """⚠ The real `_isolated_retry`, with only the operator and the radio scripted."""
        import io, contextlib
        from benchmatrix.stations import Bench, PM3, FLIPPER, T5577, build_station
        bench = Bench()
        p = reg.ALL["viking"]
        # ⚠ THE TAG MUST ACTUALLY HOLD IT. `Scripted.read` answers only for a credential an emitter
        # is really carrying, so a fixture that just sets `answers` tests nothing.
        self.dev.pm3.write_t55(p)
        self.dev.flipper.answers[("viking", "t5577")] = second_read
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = cli._isolated_retry(
                self._args_ns(), p, "rd.flip", self.dev.flipper, bench,
                build_station({PM3, T5577, FLIPPER}, bench))
        self.printed = buf.getvalue()
        return got

    def _args_ns(self):
        return cli.build_parser().parse_args(["learn", "-r", "rd.flip"])

    def test_the_operator_is_asked_to_take_the_bystander_out_and_put_it_back(self):
        self._retry("Viking AABBCCDD\n")
        self.assertEqual(self.moves, ["take out the Proxmark", "put the Proxmark underneath"],
                         "the TAG does not move — the credential stays where it was written")

    def test_a_reading_that_appears_once_isolated_is_learned(self):
        text, _, _ = self._retry("Viking AABBCCDD\n")
        self.assertIsNotNone(text)
        self.assertIn("AABBCCDD", text)
        self.assertIn("not a verdict", self.printed)

    def test_and_silence_with_the_stack_cleared_is_entitled_to_be_a_finding(self):
        """⭐ The asymmetry that makes this worth the two moves: only NOW does the silence mean
        something about the reader."""
        text, _, _ = self._retry("")
        self.assertIsNone(text, "nothing is recorded from it")
        self.assertIn("still nothing with the stack cleared", self.printed)
        self.assertIn("entitled to be one", self.printed)


class AndTheLearnLoopActuallyAsksForThatRetry(_ScriptedLearningBench):
    """⚠ TESTING `_isolated_retry` DIRECTLY PROVES NOTHING ABOUT WHETHER IT IS EVER CALLED. Stubbing
    the call site out left the whole suite green, which is the same shape of gap as a rule written
    in a comment and never in the code."""

    def setUp(self):
        super().setUp()
        p = reg.ALL["viking"]
        # The bench answers differently once the operator clears the stack — which is the entire
        # claim being tested, so the fake has to model it rather than be told the answer.
        self.dev.flipper.answers[("viking", "t5577")] = ""
        self._ask = cli.cues.ask

        def move(prompt, spoken="", **kw):
            self.moves.append(spoken)
            if spoken == "take out the Proxmark":
                self.dev.flipper.answers[("viking", "t5577")] = "%s AABBCCDD\n" % p.flip_key
            elif spoken == "put the Proxmark underneath":
                self.dev.flipper.answers[("viking", "t5577")] = ""
        self.moves = []
        cli.cues.ask = move
        # ⛔ AND THE VALUE PROMPT, or the suite blocks on `input()` forever. A prompted run asks the
        # operator which proposal to take; a test that stubs the MOVE cue and not the CHOICE cue
        # hangs with no output, which is how two runs of this suite had to be killed.
        self._choice = cli.cues.ask_choice
        cli.cues.ask_choice = lambda prompt, choices, default, **kw: default

    def tearDown(self):
        cli.cues.ask, cli.cues.ask_choice = self._ask, self._choice
        super().tearDown()

    def _run_prompted(self, *argv):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.cmd_learn(cli.build_parser().parse_args(
                ["learn", "--learned", self.path, "--session", "S1", *argv]))
        self.printed = buf.getvalue()
        return learned.load(self.path)

    def test_a_stacked_silence_triggers_the_isolated_reading(self):
        recs = self._run_prompted("-r", "rd.flip", "-p", "viking")
        self.assertIn("take out the Proxmark", self.moves,
                      "the loop never asked for the bystander to be removed")
        self.assertIn(("viking", "rd.flip"), recs,
                      "the isolated reading is what gets learned")
        self.assertEqual(recs[("viking", "rd.flip")].value, "AABBCCDD")

    def test_and_a_reader_that_works_stacked_is_never_asked_to_move_anything(self):
        """⭐ The whole reason the stack is tried first: the Chameleon reads through it, and paying
        two bench moves per protocol for a reader that does not need them is the waste this
        command was restructured to avoid."""
        recs = self._run_prompted("-r", "rd.cu1", "-p", "hidprox")
        self.assertIn(("hidprox", "rd.cu1"), recs)
        self.assertEqual(self.moves, [self.moves[0]],
                         "one cue to build the station, and nothing after it")


class TheProxmarkChecksItsOwnWriteOutLoud(_ScriptedLearningBench):
    """⛔ A CHECK THAT DISCARDS ITS EVIDENCE CANNOT BE TOLD APART FROM A CHECK THAT IS WRONG. The
    read-back reported only that it had failed. Three live explanations — the write did not land,
    the registry expectation is wrong, or something in the stack is loading the tag — and they look
    identical without the transcript. That is the same fault that hid the Flipper channel for a
    whole session.

    ⚠ AND WHEN IT PASSES IT MUST SAY SO. Operator, reading `written — not yet verified by anything`
    followed by silence: "is it not verified by the proxmark after writing?" It was; nothing said.
    """

    def _learn_viking(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.cmd_learn(cli.build_parser().parse_args(
                ["learn", "--no-prompt", "-r", "rd.flip", "-p", "viking",
                 "--learned", self.path, "--session", "S1"]))
        return buf.getvalue(), learned.load(self.path)

    def test_a_passing_read_back_is_announced_with_what_it_matched(self):
        self.dev.flipper.answers[("viking", "t5577")] = "Viking AABBCCDD\n"
        out, recs = self._learn_viking()
        self.assertIn("the credential is on the tag", out)
        self.assertIn(repr(reg.ALL["viking"].expect), out)
        self.assertIn(("viking", "rd.flip"), recs)

    def test_the_write_line_does_not_claim_more_than_it_knows(self):
        """⚠ A T5577 does not acknowledge a write, so `Done!` says the commands went out and
        nothing more (RULES.md §10)."""
        self.dev.flipper.answers[("viking", "t5577")] = "Viking AABBCCDD\n"
        out, _ = self._learn_viking()
        self.assertIn("write issued", out)
        self.assertNotIn("not yet verified by anything", out,
                         "the next line verifies it, so this read as if nothing did")

    def test_a_failing_read_back_shows_both_sides(self):
        self.dev.pm3.answers[("viking", "t5577")] = ("[+] Viking - Card: 99999999\n"
                                                     "[+] raw: FFFFFFFFFFFFFFFF")
        out, recs = self._learn_viking()
        self.assertEqual(recs, {}, "nothing is learned from a tag whose credential is unconfirmed")
        self.assertIn("expected", out)
        self.assertIn("1A337102", out, "what the registry says")
        self.assertIn("99999999", out, "and what the device actually printed")

    def test_and_names_the_candidates_rather_than_picking_one(self):
        """⛔ It used to assert "the credential is not what the registry says it is" — one of three
        possibilities, stated as the conclusion."""
        self.dev.pm3.answers[("viking", "t5577")] = "[+] Viking - Card: 99999999"
        out, _ = self._learn_viking()
        self.assertNotIn("the credential is not what the registry says it is", out)
        for candidate in ("write", "registry", "stack"):
            self.assertIn(candidate, out)
