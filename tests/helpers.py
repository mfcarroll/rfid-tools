"""Shared fixtures. Everything here runs on `Scripted` devices — no hardware, no noise."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmatrix import cues, plan as planning, registry as reg, runner  # noqa: E402
from benchmatrix.devices import Air, Scripted, obedient_operator          # noqa: E402
from benchmatrix.stations import Bench                                    # noqa: E402

cues.silence()

#: A pm3 read that decodes the registry credential byte-exact, per protocol.
def pm3_exact(p: reg.Protocol) -> str:
    stem = {"em410x": "EM 410x ID", "viking": "Viking - Card", "jablotron": "Jablotron - Card:",
            "pac": "PAC/Stanley - Card:", "hidprox": "raw: 2006ec0c86aabbccddeeff00",
            "ioprox": "IO Prox - ", "awid": "AWID - len: 26", "indala": "Indala (len 64)",
            "keri": "KERI - Internal ID:", "nexwatch": "NexWatch raw id : 0x1",
            "idteck": "IDTECK Tag Found: Card ID", "gallagher": "GALLAGHER - Region:",
            "securakey": "Securakey - len: 26", "noralsy": "Noralsy - Card:",
            "gproxii": "G-Prox-II - Len: 26", "fdxb": "FDX-B / ISO 11784/5 Animal Tag ID Found"}[p.key]
    return "[+] %s %s\n" % (stem, p.expect)


def pm3_wrong(p: reg.Protocol) -> str:
    """A decode happened, but of something else. Never merged with silence."""
    return pm3_exact(p).replace(p.expect, "deadbeefdeadbeef").replace(
        "FC: 123  CN: 4567", "FC: 999  CN: 1")


def make_devices(answers=None, pm3_answers=None, flip_answers=None, cu1_answers=None,
                 cu2_answers=None, alive=True, air=None, operator=None):
    """All four devices share one Air, so an emitter armed on one is heard by the reader.

    `answers` goes to EVERY reader, which is what a real bench looks like: a tag that will not read
    will not read for anyone. The per-device overrides model a DECODER GAP — one reader missing what
    the others can see — which is a different thing entirely from a write that never landed, and the
    two must be scripted differently or the test is not about what it says it is.

    `operator` defaults to someone who builds every stack exactly as cued. Pass a callable of your
    own to model an operator who does something else — which is the only way to test that the
    identity check catches it.
    """
    air = air or Air()
    shared = dict(answers or {})
    d = runner.Devices(
        pm3=Scripted(id="pm3", role="pm3", answers={**shared, **(pm3_answers or {})},
                     alive_ok=alive, air=air),
        flipper=Scripted(id="flipper", role="flipper", answers={**shared, **(flip_answers or {})},
                         alive_ok=alive, air=air),
        cu1=Scripted(id="cu1", role="cu1", answers={**shared, **(cu1_answers or {})}, air=air),
        cu2=Scripted(id="cu2", role="cu2", answers={**shared, **(cu2_answers or {})}, air=air),
    )
    d.air = air
    d.operator = operator or obedient_operator(air)
    return d


#: The things that can actually emit. The pm3 is a reader and a writer, never a source.
EMITTERS = ("t5577", "cu1", "cu2", "flipper")


def answers_all_exact(protocols, emitters=EMITTERS) -> dict:
    """Every (protocol, emitting device) answers byte-exact. The best case a run can have."""
    return {(p.key, e): pm3_exact(p) for p in protocols for e in emitters}


def answers_silent(protocols, emitters=EMITTERS) -> dict:
    """Every decoder deaf to every emitter — but NOT to the identity probe, which has its own key.

    ⚠ THE PROBE IS DELIBERATELY LEFT AUDIBLE. A reader that cannot even hear a unique EM410X id
    cannot say which device is on its pad, and the run aborts at the identity check before a single
    cell is measured — a different and stronger outcome than grading everything UNGRADED. To test
    the UNGRADED path you need a reader that can see the bench and still decode nothing.
    """
    return {(p.key, e): "" for p in protocols for e in emitters}


def tiny_plan(keys=("em410x", "viking"), sources=("t55.pm3", "emu.cu1"), readers=("rd.pm3",),
              bench=None) -> planning.RunPlan:
    return planning.build(reg.resolve(list(keys)), list(sources), list(readers), bench or Bench())


def quiet(*a, **k):
    """Swallow runner output in tests."""
