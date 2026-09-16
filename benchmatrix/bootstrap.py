"""Make `./bench` self-sufficient: find or build an interpreter that has what this repo needs.

⭐ THIS IS A TOOLING REPO, SO IT CARRIES ITS OWN ENVIRONMENT. Until the Flipper moved in, the whole
harness was pure standard library and shelled out to everything, so any `python3` would do. Driving
the Flipper's CLI directly needs pyserial — worth it, because parsing another tool's stdout is
exactly how `rd.flip` came to return nothing for every protocol while the device decoded perfectly
(see `flipper.py`) — and a dependency that the operator has to notice and install by hand is a
dependency that will be missing on the next machine.

⛔ IT DOES NOT TOUCH THE SYSTEM INTERPRETER. Everything lands in `.venv/` beside this repo, which is
gitignored and can be deleted without consequence. Nothing is installed anywhere else, and nothing
happens at all when the current interpreter already has what is needed — which is the common case
after the first run.

⚠ AND IT RE-EXECS AT MOST ONCE. `BENCH_BOOTSTRAPPED` marks the child, so a venv that somehow still
lacks the requirement reports that plainly instead of spawning itself forever.
"""

from __future__ import annotations

import os
import subprocess
import sys

#: What the harness cannot run without. Kept in step with `requirements.txt` by `test_bootstrap.py`
#: rather than by memory — two lists that must agree and are never checked are one list and a bug.
REQUIRED = ("serial",)

MARKER = "BENCH_BOOTSTRAPPED"
OPT_OUT = "BENCH_NO_BOOTSTRAP"


def missing(modules=None) -> list[str]:
    """Which required modules this interpreter cannot import. ⚠ Import, not `pip show`: what
    matters is whether the code about to run can use them.

    ⛔ `REQUIRED` IS READ AT CALL TIME. `modules=REQUIRED` binds the tuple when the function is
    DEFINED, so nothing can override it afterwards — the same trap that made `write_env`'s ENV_PATH
    unoverridable and let a test overwrite the operator's real `.env`. Here it was worse: a test
    that pointed `REQUIRED` at something importable still saw the real list, decided the
    interpreter was short, and RE-EXECED THE TEST RUNNER. Twice in one session, in two modules,
    one of them written after the first was fixed.
    """
    import importlib.util
    modules = REQUIRED if modules is None else modules
    return [m for m in modules if importlib.util.find_spec(m) is None]


def venv_python(root: str) -> str:
    sub = "Scripts" if os.name == "nt" else "bin"
    return os.path.join(root, ".venv", sub, "python.exe" if os.name == "nt" else "python")


def ensure(root: str, argv=None, out=print) -> None:
    """Re-exec under `.venv` if this interpreter is short of a requirement. Returns if it is not.

    ⛔ SILENT ON THE HAPPY PATH. A tool that announces its environment on every invocation trains
    the operator to skip the first lines of output, and the first lines are where a proof-of-life
    failure appears.
    """
    if os.environ.get(OPT_OUT):
        return
    if not missing():
        return
    if os.environ.get(MARKER):
        # ⚠ WE ARE ALREADY THE CHILD. Saying so is the whole point — the alternative is a fork bomb
        # that looks like a hang.
        raise SystemExit(
            "  ⛔ %s is still missing inside %s.\n"
            "     Delete %s and re-run, or install it by hand."
            % (", ".join(missing()), sys.executable, os.path.join(root, ".venv")))

    py = venv_python(root)
    if not os.path.exists(py):
        out("  ⧗ first run: building %s (this repo carries its own environment)"
            % os.path.join(root, ".venv"))
        _run([sys.executable, "-m", "venv", os.path.join(root, ".venv")],
             "could not create a virtual environment")
    if missing_in(py):
        out("  ⧗ installing %s" % ", ".join(missing()))
        _run([py, "-m", "pip", "install", "--quiet", "-r",
              os.path.join(root, "requirements.txt")], "could not install the requirements")

    os.environ[MARKER] = "1"
    os.execv(py, [py] + list(argv if argv is not None else sys.argv))


def missing_in(python: str, modules=None) -> list[str]:
    """Which required modules ANOTHER interpreter cannot import."""
    modules = REQUIRED if modules is None else modules
    code = ("import importlib.util,sys;"
            "print(' '.join(m for m in %r if importlib.util.find_spec(m) is None))" % (modules,))
    try:
        r = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return list(modules)
    return r.stdout.split()


def _run(argv, why: str) -> None:
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("  ⛔ %s:\n%s" % (why, (r.stderr or r.stdout).strip()[-800:]))
