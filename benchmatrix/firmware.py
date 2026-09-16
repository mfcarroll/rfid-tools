"""Building and flashing firmware — `bench build` and `bench flash`.

⭐ The flashing half stands on `enterdfu.py` by Matthew Carroll (ChameleonUltra,
`research/indala-psk-read/enterdfu.py`) — see `dfu.py`, which is the port. The build environment
recorded in `firmware.toml` is his too: which three pieces the ChameleonUltra build needs and why,
and that the closing `mergehex` step fails harmlessly after the zips are already written.

⭐ THE SAME DISCIPLINE AS THE REST OF THE HARNESS, POINTED AT A DIFFERENT PROBLEM. Flashing has the
identical failure shape to measuring: the tool returns cheerfully, nothing says whether it worked,
and the only way to know is to ask something that observed the effect.

  • **The artifacts are the success criterion, not the exit code** (RULES.md §10). A build whose last
    step fails harmlessly after writing the zips is a good build; a build that returns zero and
    wrote nothing is not.
  • **Quiet output is not success.** Captured non-interactively, `nrfutil` prints only an unrelated
    JLink warning — which is exactly what a flash that never happened prints too. `--json` gives a
    record per progress step, and that is the evidence (RULES.md §5).
  • **The device that comes back must be the device that went in** (RULES.md §4). The chip id is
    read before and after; a flash that returns a different chip is a flash onto the wrong unit.
  • **A version string cannot tell two builds apart when the tree was dirty.** So the version is
    recorded before and after and *compared*, and when it has not changed this says so plainly
    rather than calling the flash confirmed. The functional check is the matrix, not a string.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import tomllib
from dataclasses import dataclass, field

from .devices import Chameleon, DEFAULT_CU_PY

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
CONFIG = os.path.join(ROOT, "firmware.toml")


class FirmwareError(Exception):
    pass


@dataclass(frozen=True)
class Target:
    name: str
    description: str
    build: dict = field(default_factory=dict)
    flash: dict = field(default_factory=dict)

    def path(self, rel: str) -> str:
        return os.path.normpath(os.path.join(ROOT, rel))

    def build_dir(self) -> str:
        return self.path(self.build.get("cwd", "."))

    def artifact(self, which: str | None = None) -> str:
        rel = which or self.flash.get("artifact") or (self.build.get("artifacts") or [None])[0]
        if rel is None:
            raise FirmwareError("%s: no artifact configured" % self.name)
        return os.path.join(self.build_dir(), rel)


def load(path: str = CONFIG) -> dict[str, Target]:
    if not os.path.exists(path):
        raise FirmwareError("no firmware config at %s" % path)
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    out = {}
    for name, spec in (raw.get("targets") or {}).items():
        out[name] = Target(name=name, description=spec.get("description", ""),
                           build=spec.get("build", {}), flash=spec.get("flash", {}))
    if not out:
        raise FirmwareError("%s defines no targets" % path)
    return out


# ------------------------------------------------------------------ build

def build_env(target: Target, out=print) -> dict:
    """The environment the build needs, with `!command` values resolved.

    ⛔ A BUILD THAT PICKS UP THE WRONG TOOLCHAIN FAILS IN WAYS THAT LOOK LIKE SOURCE PROBLEMS. The
    ChameleonUltra's `Makefile.posix` hardcodes `/usr/bin` for the ARM toolchain, which is wrong on
    a Homebrew machine, and nrfutil is not on the default PATH. Both are configuration, not
    something to remember at the prompt.
    """
    env = dict(os.environ)
    for key, value in (target.build.get("env") or {}).items():
        if isinstance(value, str) and value.startswith("!"):
            cmd = value[1:].strip()
            try:
                r = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=30,
                                   stdin=subprocess.DEVNULL)
                value = (r.stdout or "").strip()
            except Exception as e:                         # noqa: BLE001
                raise FirmwareError("%s: could not resolve env %s from `%s`: %s"
                                    % (target.name, key, cmd, e)) from e
            if not value:
                raise FirmwareError("%s: `%s` produced nothing, so %s would be empty"
                                    % (target.name, cmd, key))
        env[key] = str(value)
    prepend = [target.path(p) for p in (target.build.get("path_prepend") or [])]
    missing = [p for p in prepend if not os.path.isdir(p)]
    if missing:
        raise FirmwareError("%s: PATH entries do not exist: %s" % (target.name, ", ".join(missing)))
    if prepend:
        env["PATH"] = os.pathsep.join(prepend + [env.get("PATH", "")])
    return env


@dataclass
class BuildResult:
    target: str
    ok: bool
    exit_code: int
    artifacts: dict = field(default_factory=dict)      # path -> fresh?
    note: str = ""


def build(target: Target, docker: bool = False, out=print) -> BuildResult:
    """Run the build and judge it by what it produced.

    ⛔⛔ THE EXIT CODE IS REPORTED BUT DOES NOT DECIDE. `build.sh` ends with a `mergehex` step that
    produces the SWD artifact and fails harmlessly on this bench, *after* the DFU zips are written —
    so a non-zero exit with fresh zips is a good build. The reverse also happens: a tool that returns
    zero having produced nothing. Freshness of the artifacts is the evidence either way.

    ⚠ FRESH, NOT MERELY PRESENT. `build.sh` opens with `rm -rf objects`, so a build that dies midway
    leaves no zip rather than a stale one — but that is a property of one build script, not a thing
    to rely on. The check is that each artifact is newer than the moment this build started.
    """
    spec = target.build.get("docker") if docker else target.build
    if not spec or not spec.get("command"):
        raise FirmwareError("%s: no %sbuild command configured"
                            % (target.name, "docker " if docker else ""))
    cwd = target.build_dir()
    if not os.path.isdir(cwd):
        raise FirmwareError("%s: build directory does not exist: %s" % (target.name, cwd))
    env = dict(os.environ) if docker else build_env(target, out)
    argv = list(spec["command"])

    out("  building %s in %s" % (target.name, cwd))
    out("    %s" % " ".join(shlex.quote(a) for a in argv))
    started = time.time()
    r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                       errors="replace", stdin=subprocess.DEVNULL)
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    for line in tail[-4:]:
        out("    | %s" % line[:120])

    artifacts, fresh = {}, True
    for rel in (target.build.get("artifacts") or []):
        full = os.path.join(cwd, rel)
        good = os.path.exists(full) and os.path.getmtime(full) >= started - 1
        artifacts[full] = good
        fresh = fresh and good
        out("    %s %s%s" % ("✓" if good else "⛔", rel,
                             "" if good else (" — not rebuilt" if os.path.exists(full)
                                              else " — not produced")))
    note = ""
    if fresh and r.returncode != 0:
        note = ("the build exited %d but every artifact is fresh. That is the expected shape here: "
                "the last step produces the SWD artifact and fails harmlessly after the DFU zips "
                "are already written." % r.returncode)
        out("    ⚠ %s" % note)
    elif not fresh and r.returncode == 0:
        note = "the build exited 0 but produced nothing fresh — the exit code is not the evidence."
    return BuildResult(target.name, fresh, r.returncode, artifacts, note)


# ------------------------------------------------------------------ flash

@dataclass
class FlashResult:
    target: str
    device: str
    ok: bool
    before: str = ""
    after: str = ""
    chip_before: str = ""
    chip_after: str = ""
    steps: list = field(default_factory=list)
    note: str = ""

    @property
    def version_changed(self) -> bool:
        return bool(self.before) and bool(self.after) and self.before != self.after


def flash(target: Target, port: str, name: str, artifact: str | None = None,
          expect_chipid: str = "", out=print) -> FlashResult:
    """Flash one named device, and record everything that could say whether it took."""
    spec = target.flash or {}
    if spec.get("method") != "nrf-dfu":
        raise FirmwareError("%s: unsupported flash method %r" % (target.name, spec.get("method")))
    zip_path = artifact or target.artifact()
    if not os.path.exists(zip_path):
        raise FirmwareError("no firmware at %s — run `bench build %s` first"
                            % (zip_path, target.name))

    cham = Chameleon(port=port, name=name, expect_chipid=expect_chipid)
    res = FlashResult(target.name, name, False)
    ok, why = cham.alive()
    out("    %s %s" % ("✓" if ok else "⛔", why))
    if not ok:
        res.note = why
        return res
    res.before, res.chip_before = cham.reported, (cham.chipid() or "")
    out("    firmware before: %s" % (res.before or "unknown"))

    cfg = {"port": port, "zip": zip_path, "nrfutil": target.path(spec["nrfutil"])}
    for key in ("app_usb", "dfu_usb", "trigger", "wait", "back_wait", "options"):
        if key in spec:
            cfg[key] = spec[key]
    python = target.path(spec.get("python", "")) if spec.get("python") else _serial_python()
    argv = [python, os.path.join(HERE, "dfu.py"), json.dumps(cfg)]

    proc = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                          stdin=subprocess.DEVNULL)
    for line in (proc.stdout or "").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        res.steps.append(rec)
        out("    %s %-10s %s" % ("✓" if rec.get("ok") else "⛔", rec.get("step", "?"),
                                 rec.get("detail", "")[:110]))
    if not res.steps:
        res.note = ("the flasher produced no records at all%s"
                    % ((": " + (proc.stderr or "").strip()[-160:]) if proc.stderr else ""))
        out("    ⛔ %s" % res.note)
        return res
    if not all(r.get("ok") for r in res.steps):
        res.note = next(r.get("detail", "") for r in res.steps if not r.get("ok"))
        return res

    # ⛔⛔ THE DEVICE THAT CAME BACK MUST BE THE ONE THAT WENT IN (RULES.md §4). A flash that returns
    # a different chip id is a flash onto the wrong unit, and with two identical devices on the
    # bench nothing else would notice.
    ok, why = cham.alive()
    res.after, res.chip_after = (cham.reported if ok else ""), (cham.chipid() or "")
    if res.chip_before and res.chip_after and res.chip_before != res.chip_after:
        res.note = ("⛔ the device that came back is chip %s, not the %s that went in. Something "
                    "was flashed, but not what you asked for." % (res.chip_after, res.chip_before))
        out("    %s" % res.note)
        return res
    if not ok:
        res.note = "the device is back but will not answer `hw version`: %s" % why
        out("    ⛔ %s" % res.note)
        return res

    res.ok = True
    out("    firmware after:  %s" % (res.after or "unknown"))
    # ⛔⛔ A VERSION STRING CANNOT TELL TWO BUILDS APART WHEN THE TREE WAS DIRTY. Saying "flashed"
    # because a string changed would be as wrong as saying it because nrfutil exited zero.
    if not res.version_changed:
        res.note = ("the reported version is unchanged. That is expected when the build is the same "
                    "one already on the device, or when the tree was dirty and the string cannot "
                    "distinguish two builds — it does NOT confirm the flash. Verify functionally.")
    else:
        res.note = ("the reported version changed, which is consistent with the flash but is not "
                    "proof of WHICH build landed when the tree was dirty. Verify functionally.")
    out("    ⚠ %s" % res.note)
    return res


def _serial_python() -> str:
    """An interpreter with pyserial. The virtualenv beside `cu.py` has one; this one may not."""
    cand = os.path.join(os.path.dirname(os.path.abspath(DEFAULT_CU_PY)), ".venv", "bin", "python")
    return cand if os.path.exists(cand) else "python3"
