"""The terminal the operator has to answer a prompt on.

⛔⛔ A PROMPT THAT CANNOT BE ANSWERED LOOKS EXACTLY LIKE A PROMPT NOBODY HAS ANSWERED YET. Enter
arrives as a literal `^M`, the line never terminates, and the only way out of a run is Ctrl-C —
which aborts it. Observed twice at the first station of a real run.

⛔ AND IT CANNOT BE PREVENTED FROM HERE. `stdin=DEVNULL` on every child was not enough: a readline
or prompt_toolkit client opens `/dev/tty` directly and gets the controlling terminal whatever its
stdin is. The Proxmark client and the Chameleon CLI are both in that family. So the repair is
applied after every client and again before every prompt, and it SETS the flags a prompt needs
rather than restoring a snapshot — a snapshot is only as good as the moment it was taken, and
restoring a bad one fails silently and identically.
"""

import os
import pty
import sys
import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import cues

try:
    import termios
except ImportError:                                        # pragma: no cover
    termios = None


@unittest.skipIf(termios is None, "no termios on this platform")
class RepairingTheTerminal(unittest.TestCase):

    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.real, sys.stdin = sys.stdin, os.fdopen(self.slave, "r")

    def tearDown(self):
        sys.stdin.close()
        sys.stdin = self.real
        os.close(self.master)

    def _flags(self):
        a = termios.tcgetattr(self.slave)
        return (bool(a[0] & termios.ICRNL), bool(a[3] & termios.ICANON),
                bool(a[3] & termios.ECHO))

    def _break_it(self):
        """Exactly what a readline client leaves behind."""
        a = termios.tcgetattr(self.slave)
        a[0] &= ~termios.ICRNL
        a[3] &= ~(termios.ICANON | termios.ECHO)
        termios.tcsetattr(self.slave, termios.TCSANOW, a)

    def test_a_fresh_terminal_is_already_usable(self):
        self.assertEqual(self._flags(), (True, True, True))
        self.assertTrue(cues.is_canonical())

    def test_the_symptom_is_detected_not_merely_endured(self):
        self._break_it()
        self.assertFalse(cues.is_canonical(),
                         "a terminal a prompt cannot be answered on must be recognisable as one")

    def test_the_repair_restores_every_flag_a_prompt_needs(self):
        self._break_it()
        cues._sane()
        self.assertEqual(self._flags(), (True, True, True))
        self.assertTrue(cues.is_canonical())

    def test_the_repair_sets_rather_than_restores(self):
        """⚠ There is no snapshot to be wrong. Breaking the terminal BEFORE the module was ever
        asked about it must still be repairable — a snapshot taken at import would have captured
        whatever state happened to exist and could reproduce the fault exactly."""
        self._break_it()
        cues._sane()
        cues._sane()
        self.assertTrue(cues.is_canonical())

    def test_it_is_harmless_when_stdin_is_not_a_terminal(self):
        sys.stdin.close()
        sys.stdin = open(os.devnull)
        cues._sane()
        self.assertTrue(cues.is_canonical(), "a pipe is not a terminal and needs no repair")


if __name__ == "__main__":
    unittest.main()
