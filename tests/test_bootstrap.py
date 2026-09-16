"""`./bench` carrying its own environment.

⭐ THIS IS A TOOLING REPO, so it must run on a machine that has only a `python3`. Until the Flipper
moved in, the harness was pure standard library; driving the Flipper's CLI directly needs pyserial,
and a dependency the operator has to notice and install by hand is one that will be missing on the
next bench.
"""

import os
import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import bootstrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TheRequirementsAndTheCodeMustAgree(unittest.TestCase):
    """⛔ TWO LISTS THAT MUST MATCH AND ARE NEVER CHECKED ARE ONE LIST AND A BUG. `REQUIRED` is
    import names and `requirements.txt` is distribution names, so they cannot simply be compared —
    but a requirement appearing in one and not the other is exactly the drift worth catching."""

    #: import name -> the distribution that provides it.
    PROVIDED_BY = {"serial": "pyserial"}

    def test_every_required_module_has_a_line_in_requirements(self):
        text = open(os.path.join(ROOT, "requirements.txt")).read().lower()
        for mod in bootstrap.REQUIRED:
            dist = self.PROVIDED_BY.get(mod, mod)
            self.assertIn(dist, text, "%s is required but nothing installs it" % mod)

    def test_and_every_installed_distribution_is_actually_required(self):
        wanted = {self.PROVIDED_BY.get(m, m) for m in bootstrap.REQUIRED}
        for line in open(os.path.join(ROOT, "requirements.txt")):
            line = line.split("#")[0].strip()
            if not line:
                continue
            name = line.split(">=")[0].split("==")[0].strip().lower()
            self.assertIn(name, wanted, "%s is installed but nothing imports it" % name)


class ItDoesNothingWhenThereIsNothingToDo(unittest.TestCase):
    """⛔ SILENT ON THE HAPPY PATH. A tool that announces its environment every time trains the
    operator to skip the first lines of output, and the first lines are where a proof-of-life
    failure appears."""

    #: ⛔⛔ NEVER CALL `ensure` WITH THE REAL `REQUIRED` FROM A TEST. The suite deliberately runs on
    #: an interpreter with no pyserial — that is what proves the pure logic stays importable — so a
    #: real call re-execs the TEST RUNNER under the venv with the test's own fake argv. It did:
    #: the run vanished mid-suite with `can't open file 'x'`, which is what a replaced process
    #: looks like from outside.
    def setUp(self):
        self._required = bootstrap.REQUIRED
        bootstrap.REQUIRED = ("os",)

    def tearDown(self):
        bootstrap.REQUIRED = self._required

    def test_a_satisfied_interpreter_is_left_alone(self):
        said = []
        bootstrap.ensure(ROOT, argv=["x"], out=said.append)
        self.assertEqual(said, [])

    def test_missing_reports_only_what_cannot_be_imported(self):
        self.assertEqual(bootstrap.missing(("os", "sys")), [])
        self.assertEqual(bootstrap.missing(("os", "definitely_not_a_module")),
                         ["definitely_not_a_module"])

    def test_the_opt_out_is_honoured(self):
        """⚠ An operator managing their own environment must be able to say so."""
        was = os.environ.get(bootstrap.OPT_OUT)
        os.environ[bootstrap.OPT_OUT] = "1"
        bootstrap.REQUIRED = ("definitely_not_a_module",)   # unsatisfiable, so only the opt-out saves us
        try:
            said = []
            bootstrap.ensure(ROOT, argv=["x"], out=said.append)
            self.assertEqual(said, [], "the opt-out must stop it before it builds anything")
        finally:
            bootstrap.REQUIRED = ("os",)
            if was is None:
                os.environ.pop(bootstrap.OPT_OUT, None)


class AndItReExecsAtMostOnce(unittest.TestCase):
    """⛔ A BOOTSTRAP THAT CANNOT SATISFY ITSELF MUST SAY SO, NOT SPAWN ITSELF FOREVER. A fork bomb
    looks exactly like a hang, and this session has already lost two runs to something that looked
    like one."""

    def setUp(self):
        self._required = bootstrap.REQUIRED
        bootstrap.REQUIRED = ("definitely_not_a_module",)
        self._marker = os.environ.get(bootstrap.MARKER)
        os.environ[bootstrap.MARKER] = "1"

    def tearDown(self):
        bootstrap.REQUIRED = self._required
        if self._marker is None:
            os.environ.pop(bootstrap.MARKER, None)

    def test_the_child_reports_instead_of_recursing(self):
        with self.assertRaises(SystemExit) as cm:
            bootstrap.ensure(ROOT, argv=["x"], out=lambda *a: None)
        self.assertIn("definitely_not_a_module", str(cm.exception))
        self.assertIn("still missing", str(cm.exception))


class TheVenvLivesInTheRepoAndIsNotCommitted(unittest.TestCase):

    def test_the_interpreter_path_is_under_the_repo(self):
        got = bootstrap.venv_python(ROOT)
        self.assertTrue(got.startswith(os.path.join(ROOT, ".venv")), got)

    def test_git_ignores_it(self):
        """⛔ Nothing is installed outside this directory, and what is installed is disposable."""
        self.assertIn(".venv/", open(os.path.join(ROOT, ".gitignore")).read())


if __name__ == "__main__":
    unittest.main()
