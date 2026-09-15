"""Operator audio. One voice at a time, and one utterance per prompt.

⛔ Two `say` processes started within a few hundred milliseconds talk over each other and the
operator hears neither clearly — which is worse than silence, because it still sounds like a working
cue. Device-observed during `bench setup`, where a chime-then-ask pair spoke its question twice.
"""

import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import cues, setup


class OneVoiceAtATime(unittest.TestCase):

    def setUp(self):
        self.started = []
        self.killed = []
        self._popen, self._run, self._speak, self._sound = (
            cues.subprocess.Popen, cues.subprocess.run, cues.SPEAK, cues.SOUND)
        cues.SPEAK, cues.SOUND = True, False
        cues._TALKING = None
        outer = self

        class FakeProc:
            def __init__(self, argv):
                self.argv = argv
                self.done = False

            def poll(self):
                return 0 if self.done else None

            def terminate(self):
                outer.killed.append(self.argv)
                self.done = True

        def popen(argv, **kw):
            proc = FakeProc(argv)
            outer.started.append(argv)
            return proc

        cues.subprocess.Popen = popen
        cues.subprocess.run = lambda argv, **kw: outer.started.append(argv)

    def tearDown(self):
        cues.subprocess.Popen, cues.subprocess.run = self._popen, self._run
        cues.SPEAK, cues.SOUND = self._speak, self._sound
        cues._TALKING = None

    def _spoken(self):
        return [" ".join(a[3:]) for a in self.started if a and a[0] == "say"]

    def test_a_second_utterance_stops_the_first(self):
        cues._say("the first thing")
        cues._say("the second thing")
        self.assertEqual(len(self.killed), 1, "the first utterance must be cut off")
        self.assertIn("the first thing", " ".join(self.killed[0]))

    def test_nothing_is_killed_when_nothing_is_talking(self):
        cues._say("only thing")
        self.assertEqual(self.killed, [])

    def test_a_finished_utterance_is_not_terminated(self):
        cues._say("first")
        cues._TALKING.done = True
        cues._say("second")
        self.assertEqual(self.killed, [])

    def test_the_blink_prompt_speaks_exactly_once(self):
        """The reported bug: a chime-then-ask pair issued two overlapping utterances, and what the
        operator heard was a garbled first half and a clean second."""
        import builtins
        orig = builtins.input
        builtins.input = lambda *a: "1"
        try:
            self.assertEqual(setup._ask_label("/dev/a", "ABCD1234"), "cu1")
        finally:
            builtins.input = orig
        self.assertEqual(len(self._spoken()), 1,
                         "one prompt, one utterance — got %r" % self._spoken())
        self.assertEqual(self.killed, [], "nothing should have needed cutting off")


if __name__ == "__main__":
    unittest.main()
