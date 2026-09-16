"""The campaign: set a station up, run its routine hands-off, bracket it with controls.

Per station:

    move cue -> operator confirms -> RADIO IDENTITY CHECK -> null sweep BEFORE
             -> the routine, with no further operator involvement
             -> null sweep AFTER -> A/B/A comparison

⛔⛔ FOUR THINGS ABORT OR VOID RATHER THAN DEGRADE:
  1. A DEAD INSTRUMENT ABORTS THE RUN (RULES.md §5). A silent reader and a silent emitter produce
     identical numbers.
  2. A WRONG DEVICE ABORTS THE RUN (RULES.md §4). Everything at that station would be attributed to
     the wrong Chameleon, and the null arms cannot catch it.
  3. A DISAGREEING A/B/A VOIDS THE STATION and revokes any licence it issued, wherever the rows it
     licensed were measured (RULES.md §3).
  4. A FAILED WRITE-VERIFY SKIPS THE REST OF THAT WRITE. If the writer cannot read back what it just
     put on the tag, the tag does not hold what the plan thinks, and every other read taken against
     it would be filed under the wrong protocol.

⚠ AND TWO THINGS ARE DELIBERATELY NOT ABORTS:
  • A calibration row that comes back SILENT **in an isolated pair** is a result: "this reader
    cannot judge this protocol on this bench". The run carries on.
  • A non-EXACT reading in a crowded stack is not a result at all. It is screened, it queues an
    isolated re-measurement, and only that re-measurement may call it SILENT or WRONG (RULES.md §7).
"""

from __future__ import annotations

import datetime as _dt
import os as _os
from dataclasses import dataclass, field

from . import cues, identity, ui
from .devices import DeviceError, WrongDevice
from .identity import IdentityFault, NullSweep, null_sweep, sweeps_agree
from .outcomes import (Calibration, CalibrationRefused, Cell, Outcome, grade, observe, screened,
                       ungraded)
from .plan import Block, Op, RunPlan
from .stations import (CU1, CU2, FLIPPER, GOLD_SOURCES, HUMAN, PM3, READERS, TAG_SOURCES, T5577,
                       null_station, plan_move)


class RunAborted(Exception):
    """The run stopped because it could no longer measure anything. Never produces a grid.

    ⚠ IT CARRIES WHAT WAS MEASURED. Losing forty completed readings because the forty-first could
    not be trusted helps nobody — the caller can file them, clearly marked, so the operator can see
    how far the session got. What it must never do is produce something that looks like a grid.
    """

    def __init__(self, why: str, result=None):
        super().__init__(why)
        self.result = result


@dataclass
class TagState:
    """What the tag is believed to hold, and whether anything has actually seen it.

    ⛔⛔ THIS OUTLIVES THE STATION IT WAS WRITTEN AT (RULES.md §10). A credential is written at one
    station and may not be read until the next one — the whole point of carrying a tag. So whether a
    write was ever witnessed is a property of the TAG, not of the block that issued it: verifying at
    the write station and then reading somewhere else must count as verified, or every carried tag
    would look like a write that never landed.
    """

    protocol: object | None = None
    writer: str | None = None
    verified: bool = False
    tag: int = 0
    #: Was the tag put into a state known to DIFFER from this credential before it was written?
    #: Without that, a byte-exact read cannot tell a successful write from no write at all, because
    #: every writer in the registry writes the same credential for a given protocol.
    parked: bool = True
    #: Devices that have read the CURRENT credential back byte-exact. A wipe is confirmed by one of
    #: them then hearing nothing: silence from a reader that was speaking a moment ago is evidence,
    #: where silence from a reader that has never spoken is not.
    witnesses: set = field(default_factory=set)
    #: Set by a `blank` read that came back silent on a witness. Clears on the next write.
    cleared: bool = False
    #: Was the tag, immediately before this write, in a state known to DIFFER from what was written?
    #: Either it had just been cleared, or it held a different protocol. When it was, a DECODE — not
    #: only a byte-exact one — proves the write landed, because a reader asked for P cannot decode a
    #: credential that is not there. That is what turns a registry mismatch from an ambiguous "no
    #: reader saw it" into an informative WRONG.
    distinct: bool = False


@dataclass
class BlockReport:
    block: Block
    identity: object | None = None
    before: NullSweep | None = None
    after: NullSweep | None = None
    void: bool = False
    void_why: str = ""


@dataclass
class RunResult:
    session: str
    started: str
    plan: RunPlan
    cells: list[Cell] = field(default_factory=list)
    licences: dict = field(default_factory=dict)
    refusals: dict = field(default_factory=dict)
    #: (protocol, reader) pairs where that reader has decoded that protocol at least once in this
    #: session, from ANY source. ⛔ This is the only thing that makes a later SILENCE from the same
    #: reader mean anything — see `_settle`. It is deliberately weaker than a licence: a licence
    #: needs a GOLD source, while "can this reader see this protocol at all" is answered by any
    #: source that worked.
    decoded_by: set = field(default_factory=set)
    #: Cells holding a silence nothing could attribute when it was taken. ⭐ THE READING IS FIXED;
    #: THE INTERPRETATION IS NOT. A reader that decodes this protocol later in the run — from any
    #: source — retrospectively licenses these, so they are revisited once the corpus is complete.
    unattributed: list = field(default_factory=list)
    #: (protocol, reader) pairs whose decode marker did not fire on a byte-exact read. The cell is
    #: still correct; the REGISTRY is not, and would misreport a wrong decode as silence.
    bad_markers: dict = field(default_factory=dict)
    #: Pairs whose calibration row was screened rather than decided. Their dependent cells are still
    #: measured — see `_routine`.
    screened_pairs: set = field(default_factory=set)
    blocks: list[BlockReport] = field(default_factory=list)
    aborted: str = ""
    finished: str = ""
    provenance: str = "bench"
    #: device id -> what that device says it is running. Recorded at proof of life, published in
    #: the grid and the JSON: a cell is a claim about a firmware, not about a device in general.
    firmware: dict = field(default_factory=dict)
    #: The harness's own commit, so a grid says which version of these rules produced it.
    harness: str = ""

    @property
    def void_blocks(self) -> list[BlockReport]:
        return [b for b in self.blocks if b.void]

    @property
    def to_isolate(self) -> list[Cell]:
        """Screened non-EXACT readings, in the order they were taken. The phase-2 work list."""
        return [c for c in self.cells if c.crowding and c.outcome is Outcome.UNGRADED
                and c.observation is not None]


@dataclass
class Devices:
    pm3: object | None = None
    flipper: object | None = None
    cu1: object | None = None
    cu2: object | None = None
    #: On a real bench the operator performs the move and the harness cannot; this is None. The
    #: tests and dry runs supply a callable that rearranges the scripted bench.
    operator: object | None = None

    def by_dev(self, dev: str):
        got = {PM3: self.pm3, FLIPPER: self.flipper, CU1: self.cu1, CU2: self.cu2}.get(dev)
        if got is None:
            raise RunAborted("the plan needs %s and this run has no channel for it" % HUMAN[dev])
        return got

    def chameleons(self) -> dict:
        return {d: c for d, c in ((CU1, self.cu1), (CU2, self.cu2)) if c is not None}

    def present(self, station) -> list:
        return [self.by_dev(d) for d in station.stack if d not in (T5577, "oemtag")]

    def all(self) -> list:
        return [d for d in (self.pm3, self.flipper, self.cu1, self.cu2) if d is not None]


_HARNESS_VERSION = None


def _announce_refusals(plan: RunPlan, out) -> None:
    """Say what is NOT being measured, BEFORE measuring anything.

    ⛔ A PROTOCOL THAT NEVER APPEARS IN THE OUTPUT CANNOT BE TOLD FROM ONE THAT WAS FORGOTTEN. A
    plan-time refusal produces no ops, so the operator watches seventeen protocols scroll past and
    has no way to know the eighteenth was deliberate — the reason is in the written grid, at the
    bottom, after the run is over. Naming them up front is also the last chance to notice that a
    protocol you meant to measure has quietly dropped out of the plan.
    """
    if not plan.exclusions:
        return
    protocols = {}
    for e in plan.exclusions:
        protocols.setdefault(e.protocol, set()).add(e.rule)
    whole = sorted(p for p in protocols
                   if not any(c.protocol.key == p for c in plan.cells))
    partial = sorted(set(protocols) - set(whole))
    if whole:
        out("    %s not measured at all: %s"
            % (ui.mark("skip"), ", ".join("%s (%s)" % (p, ", ".join(sorted(protocols[p])))
                                          for p in whole)))
    if partial:
        out("    %s partly refused: %s"
            % (ui.mark("note"), ", ".join("%s (%s)" % (p, ", ".join(sorted(protocols[p])))
                                          for p in partial)))
    out("    %s   see \"refused at plan time\" in the grid for why, and what would change it"
        % ui.mark("note"))


def _harness_version() -> str:
    """The commit this harness is running from. A grid should say which rules produced it.

    ⚠ Worked out once per process. It shells out to git, and a run asks for it at every station.
    """
    global _HARNESS_VERSION
    if _HARNESS_VERSION is None:
        import subprocess
        here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        try:
            r = subprocess.run(["git", "-C", here, "describe", "--always", "--dirty", "--tags"],
                               capture_output=True, text=True, timeout=10,
                               stdin=subprocess.DEVNULL)
            _HARNESS_VERSION = (r.stdout or "").strip() or "unknown"
        except Exception:                                  # noqa: BLE001
            _HARNESS_VERSION = "unknown"
    return _HARNESS_VERSION


def session_id() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def run(plan: RunPlan, devices: Devices, *, interactive: bool = True,
        session: str | None = None, out=print, licences: dict | None = None) -> RunResult:
    """⚠ `licences` CARRIES PHASE 1's CONTROLS INTO PHASE 2. The isolation phase re-measures cells
    whose calibration already passed; making it re-earn those licences would mean re-running the
    gold rows at yet more stations for no additional evidence. A licence that phase 1 revoked is
    simply absent, and the cells it covered stay UNGRADED."""
    session = session or session_id()
    scripted = any(type(d).__name__ == "Scripted" for d in devices.all())
    res = RunResult(session=session, started=_dt.datetime.now().isoformat(timespec="seconds"),
                    plan=plan, provenance="dry-run (scripted devices)" if scripted else "bench")
    if licences:
        res.licences.update(licences)

    out("\n  run %s phase %d — %d cells, %d stations, %d operator interventions"
        % (session, plan.phase, len(plan.cells), len(plan.blocks), plan.interventions))
    _announce_refusals(plan, out)
    try:
        # ⛔ PROOF OF LIFE IS INSIDE THE `finally` TOO. A device can be armed before the run starts —
        # a previous session that ended badly, an `econfig` run by hand — and aborting here without
        # putting it back would leave the bench emulating, with nothing on screen to say so.
        res.harness = _harness_version()
        for dev in devices.all():
            ok, why = dev.alive()
            out("    %s %s" % (ui.mark("ok" if ok else "bad"), why))
            res.firmware[getattr(dev, "name", None) or dev.id] = getattr(
                dev, "reported", "not reported")
            if not ok:
                res.aborted = why
                cues.cue_fault("instrument not alive. aborting.")
                raise RunAborted(why, res)
        _measure(plan, devices, res, interactive, session, out)
    except KeyboardInterrupt:
        # ⛔ Ctrl-C IS AN ABORT LIKE ANY OTHER, not a crash. The operator stopping a run is a normal
        # thing to do — mid-station, hands full, something wrong on the bench — and it must leave a
        # clean message and a safe bench rather than a traceback.
        where = res.blocks[-1].block.station.name if res.blocks else "startup"
        res.aborted = ("interrupted by the operator at %s, after %d cell(s)"
                       % (where, len(res.cells)))
        cues.hush()
        raise RunAborted(res.aborted, res) from None
    except RunAborted as e:
        e.result = res
        raise
    finally:
        _restore(devices, out)
    _reattribute(res, out)
    res.finished = _dt.datetime.now().isoformat(timespec="seconds")
    return res


def _reattribute(res: RunResult, out) -> None:
    """Re-read the run's silences now that the whole corpus is in.

    ⭐⭐ SILENCE IS A RESULT WHEN, AND ONLY WHEN, SOMETHING BACKS IT UP — and what backs it up may
    arrive AFTER it. A reader that says nothing about a protocol at step three is uninterpretable
    there; if the same reader decodes that protocol at step forty, from any source, the step-three
    silence becomes a statement about that tag. The reading never changes. Its interpretation does,
    and it does so as the corpus grows.

    ⚠ THIS IS A WITHIN-RUN PASS ONLY. The same logic holds across runs — a reader shown to decode a
    protocol last week can license a silence recorded today — but only while that reader is running
    the same firmware, since a cell is a claim about a firmware and not about a device (RULES.md
    §11). Persisting the corpus is the natural next step and is deliberately not half-built here.
    """
    promoted = 0
    for index, protocol, reader, state in res.unattributed:
        if (protocol, reader) not in res.decoded_by:
            continue
        cell = res.cells[index]
        res.cells[index] = ungraded(
            cell.protocol, cell.source, cell.reader,
            "the write was issued and %s read nothing back. %s decoded %s later in this run, so it "
            "CAN see this protocol and its silence here is about the tag: the credential is not on "
            "it. (Read as unattributable when taken; licensed retrospectively by a later decode.)"
            % (reader, reader, protocol),
            crowding=cell.crowding)
        promoted += 1
    if promoted:
        out("\n    %s %d silence(s) became attributable once the whole run was in — a reader that "
            "said nothing early decoded that protocol later, from another source."
            % (ui.mark("ok"), promoted))


def _restore(devices: Devices, out) -> None:
    """Leave the bench idle: nothing emulating, every Chameleon back in reader mode.

    ⛔ A DEVICE LEFT EMULATING IS A CONTAMINATED BENCH FOR WHATEVER RUNS NEXT, and the operator has
    no way to see it — the giveaway is a null sweep failing at the start of a session for no visible
    reason. Runs abort; this is the one thing that must happen anyway, so it is in a `finally` and it
    swallows its own errors rather than masking the fault that got us here.
    """
    for dev in devices.all():
        try:
            dev.disarm()
        except Exception:                                  # noqa: BLE001 — never mask the real fault
            pass
    cues.hush()


def _measure(plan: RunPlan, devices: Devices, res: RunResult, interactive: bool, session: str,
             out) -> None:
    """Walk the stations, bracketing each routine with its controls.

    ⭐⭐ THE ORDER IS BUILT AROUND THE SWEEP, NOT AROUND THE STACK. A null sweep has to be taken with
    no passive tag in the field, so the tag is the LAST thing to go on and the FIRST thing to come
    off. Building the whole station and then immediately asking for the tag back out — which is what
    an earlier version did — is three instructions where one will do, and the middle one contradicts
    the one before it. An operator who is told to undo what they were just told to do stops trusting
    the cues, and the cues are the only thing keeping the bench and the plan in step.

    So each station is: arrange it empty, take the controls, add the tag, work, take the tag out,
    close the controls. The tag never goes on before it is wanted.
    """
    prev = None
    tag_state = TagState()
    for report in (BlockReport(b) for b in plan.blocks):
        b = report.block
        res.blocks.append(report)
        pad = plan.bench.pad
        empty = null_station(b.station)

        out("\n  %s  %s" % (ui.banner(b.station.name), ui.paint(b.station.describe(), "dim")))
        _goto(prev, empty, interactive, devices, out, plan.bench)
        prev = empty

        if identity.identifiable(empty):
            _identity(report, devices, res, out, empty)
        elif any(d in (CU1, CU2) for d in empty.stack):
            out("    %s no radio identity check here" if False else "    · no radio identity check here — the only Chameleon in the stack is the one "
                "reading, and its port already says which device that is")

        report.before = _sweep("NULL BEFORE", empty, b, devices, out)
        if not report.before.clean:
            res.aborted = ("ambient contamination at %s before anything was armed: %s"
                           % (b.station.name, ", ".join(sorted(report.before.hits))))
            cues.cue_fault("the field is not clean. aborting.")
            raise RunAborted(res.aborted, res)

        if empty != b.station:
            _goto(prev, b.station, interactive, devices, out, plan.bench)
            prev = b.station

        try:
            issued = _routine(report, devices, res, session, pad, out, tag_state)
        except WrongDevice as e:
            # ⛔ Caught at the exact action it would have corrupted. Everything measured at this
            # station is about to be attributed to a device we can no longer vouch for.
            res.aborted = str(e)
            cues.cue_fault("wrong device answered. aborting.")
            raise RunAborted(str(e), res) from e

        if empty != b.station:
            _goto(prev, empty, interactive, devices, out, plan.bench)
            prev = empty

        report.after = _sweep("NULL AFTER", empty, b, devices, out)
        agree, why = sweeps_agree(report.before, report.after)
        out("    %s %s" % (ui.mark("ok" if agree else "bad"), why))
        if not agree:
            report.void, report.void_why = True, why
            _void(res, report, issued, out)


# ------------------------------------------------------------------ the routine

def _routine(report: BlockReport, devices: Devices, res: RunResult, session: str, pad: str,
             out, tag_state: TagState) -> list:
    """Run one station's routine. Everything here is hands-off except a phase-2 tag swap.

    ⭐⭐ A WRITE IS NOT DONE BECAUSE IT RETURNED. `Done!` from the Proxmark means the commands went
    out on the air; a T5577 does not acknowledge a write, so nothing in that reply says the
    credential landed. The only thing that can say so is something reading it back. So the reads
    that follow a write are BUFFERED and settled together, once the tag's state is finished with —
    see `_settle`.
    """
    b = report.block
    issued: list = []
    armed_ok = True                     # did the last write or arm even get issued?
    current_tag = tag_state.tag
    pending: list = []                  # (op, observation) for the tag state being read now
    state = ((tag_state.protocol, tag_state.writer) if tag_state.protocol else None)

    def settle():
        nonlocal pending
        if pending:
            _settle(pending, state, tag_state, report, devices, res, out, issued)
            pending = []

    for op in b.ops:
        if b.station.has_tag and op.tag != current_tag:
            # ⚠ A TAG SWAP IS AN OPERATOR INTERVENTION LIKE ANY OTHER and is cued as one. It only
            # happens in the isolation phase, where writing a batch at one station and reading it at
            # the next is cheaper than rearranging the bench per protocol.
            settle()
            if current_tag is not None:
                cues.ask("      swap to tag %d and press Enter: " % (op.tag + 1),
                         spoken="swap to tag %d" % (op.tag + 1))
            current_tag = op.tag
            tag_state.tag = op.tag
            tag_state.verified = False

        if op.kind == "wipe":
            settle()
            _wipe(op, devices, out, tag_state)
            state = None
            continue
        if op.kind == "write":
            settle()
            # ⚠ `settle()` has just decided whether the PARKING write took. Read that before it is
            # overwritten by this write's own state.
            parked = tag_state.cleared if op.after_park else True
            prev = tag_state.protocol
            distinct = tag_state.cleared or (prev is not None and prev.key != op.protocol.key)
            armed_ok = _write(op, devices, out)
            state = (op.protocol, op.device)
            tag_state.protocol, tag_state.writer = op.protocol, op.device
            tag_state.verified = False          # a fresh credential has been witnessed by nothing
            tag_state.witnesses = set()
            tag_state.cleared = False
            tag_state.parked = parked
            tag_state.distinct = distinct
            continue
        if op.kind == "arm":
            settle()
            armed_ok = _arm(op, devices, out)
            state = None
            continue
        if op.kind == "disarm":
            settle()
            devices.by_dev(op.device).disarm()
            continue
        if op.kind == "place":
            settle()
            cues.ask("      place the %s OEM card and press Enter: " % op.protocol.key,
                     spoken="place the %s card" % op.protocol.key)
            armed_ok = True
            state = (op.protocol, None)
            continue

        if op.kind == "verify":
            # ⭐ A read that produces no cell. Its only job is to witness that the write landed.
            if armed_ok:
                obs = _read(op, devices, session, pad, out, protocol=op.protocol,
                            source=_source_of(state), reader=_reader_id(op.device))
                if obs is not None:
                    pending.append((op, obs))
            continue

        cell = op.cell
        assert cell is not None
        if not armed_ok:
            # The command was refused outright, so nothing was put anywhere. Different from a write
            # that was issued and may or may not have landed — that one is settled below.
            res.cells.append(ungraded(cell.protocol.key, cell.source, cell.reader,
                                      "the source was never armed — the command was refused",
                                      crowding=op.crowding))
            out("      %s %-10s %-9s %-7s not measured: source not armed"
                % (ui.mark("skip"), cell.protocol.key, cell.source, cell.reader))
            continue

        obs = _read(op, devices, session, pad, out)
        if obs is None:
            continue
        _check_marker(obs, res, out)
        if cell.source in TAG_SOURCES:
            pending.append((op, obs))          # graded once the whole tag state has been read
        else:
            _grade_one(op, obs, report, res, out, issued)
    settle()
    return issued


def _settle(pending: list, state, tag_state: TagState, report: BlockReport, devices: Devices,
            res: RunResult, out, issued: list) -> None:
    """Decide what a tag's reads are worth, now that every reader has had its turn at it.

    ⛔⛔ THE VERIFICATION RULE (RULES.md §10). A write is certain only once something has observed
    its effect. If NO reader read back what was written, the tag is not known to hold it, and none
    of those reads may be attributed to their readers — a silence there is as likely to be a write
    that never landed as a decoder that cannot see it.

    ⭐ AND ANY ONE BYTE-EXACT READ SETTLES IT FOR ALL OF THEM. A credential we chose cannot be
    conjured out of a tag that does not hold it, so one reader seeing it proves the write landed —
    which turns every OTHER reader's silence on the same tag from an ambiguity into a genuine
    finding about that reader. Two readers at a station are worth far more than twice one.
    """
    # ⚠ STICKY ACROSS STATIONS. Once anything has read this credential back, it stays verified for
    # as long as the tag holds it — including at the next station, which is where a carried tag is
    # usually read.
    for op, obs in pending:
        if obs is None:
            continue
        if obs.decoded:
            res.decoded_by.add((obs.protocol, obs.reader))
        if obs.matched:
            tag_state.verified = True
            tag_state.witnesses.add(op.device)
        elif obs.decoded and tag_state.distinct:
            # ⭐ A DECODE IS EVIDENCE THE WRITE LANDED, EVEN A WRONG ONE. The tag held something
            # else a moment ago, and a reader asked for this protocol cannot decode a credential
            # that is not there — so the write took, and what came back is a genuine WRONG rather
            # than a silence nobody can attribute. This is what makes a registry mismatch legible
            # on a single-reader station instead of ambiguous.
            tag_state.verified = True
    verified = tag_state.verified
    graded = [(op, obs) for op, obs in pending if op.cell is not None]

    # ⛔⛔ A BYTE-EXACT READ AFTER AN UNPARKED WRITE PROVES NOTHING ABOUT THE WRITER. Every writer in
    # the registry puts the same credential on the tag for a given protocol, so if the tag was not
    # first put into a state known to differ, what comes back is exactly what a write that did
    # nothing would have left behind — the gold writer's work, credited to the device under test.
    if graded and not tag_state.parked:
        why = ("the tag was not first put into a state differing from this credential, so a "
               "byte-exact read here cannot tell a successful write from no write at all — the "
               "parking write did not take (RULES.md §10).")
        out("      %s %-10s UNPARKED — %s"
            % (ui.mark("skip"), state[0].key if state else "?", why[:90]))
        for op, obs in graded:
            c = op.cell
            res.cells.append(ungraded(c.protocol.key, c.source, c.reader, why,
                                      crowding=op.crowding))
        return
    if verified:
        for op, obs in graded:
            _grade_one(op, obs, report, res, out, issued)
        return
    if not graded:
        what = state[0].key if state else "?"
        out("      %s %s: the write was issued and the writer could not read it back"
            % (ui.mark("skip"), "the parking credential" if what.startswith("__") else what))
        return

    protocol = state[0].key if state else pending[0][0].protocol.key
    readers = sorted({op.cell.reader if op.cell else _reader_id(op.device) for op, _ in pending})

    # ⛔⛔ SILENCE FROM A READER THAT HAS NEVER SPOKEN ABOUT THIS PROTOCOL SAYS NOTHING, AND THAT IS
    # TRUE HOWEVER MANY SUCH READERS THERE ARE. The previous wording concluded "none of them read it
    # back, so the credential is not on the tag — this is a WRITE failure", which is a confident
    # verdict drawn from collective ignorance: every reader present may simply be unable to decode
    # the protocol. You can prove a write LANDED; you cannot prove it did not, without a reader
    # already shown to see that protocol (RULES.md §10).
    proven = sorted(r for r in readers if (protocol, r) in res.decoded_by)
    if proven:
        why = ("the write was issued and nothing read it back — and %s %s decoded %s earlier in "
               "this session, so %s silence now is about the TAG. The credential is not on it."
               % (", ".join(proven), "has" if len(proven) == 1 else "have", protocol,
                  "its" if len(proven) == 1 else "their"))
    else:
        alt = _other_sources(protocol, state, devices)
        why = ("the write was issued and nothing decoded anything at all. No reader present has "
               "been shown to decode %s at all this session, so this cannot be told apart from "
               "every one of them being unable to — adding readers does not help unless one of "
               "them speaks. What settles it is the same protocol from a DIFFERENT source%s — and "
               "if one arrives later in THIS run it is revisited; if it arrives in a later run, "
               "this cell is published as outstanding so that run can settle it (RULES.md §10)."
               % (protocol, (": try " + ", ".join(alt)) if alt else ""))
    out("      %s %-10s write NOT VERIFIED — %s" % (ui.mark("skip"), protocol, why))
    for op, obs in graded:
        c = op.cell
        res.cells.append(ungraded(c.protocol.key, c.source, c.reader, why, crowding=op.crowding))
        if not proven:
            # Revisited at the end of the run: another source may yet license this reader.
            res.unattributed.append((len(res.cells) - 1, c.protocol.key, c.reader, state))


def _grade_one(op: Op, obs, report: BlockReport, res: RunResult, out, issued: list) -> None:
    """Score one observation, now that the tag state behind it is known to be real."""
    cell = op.cell
    if not cell.is_calibration and cell.pair not in res.licences:
        # ⭐ A PAIR WHOSE CALIBRATION WAS ONLY *SCREENED* IS UNDECIDED, NOT REFUSED, so its dependent
        # cells are still graded from the reading already taken.
        if cell.pair not in res.screened_pairs:
            why = res.refusals.get(cell.pair, "no calibration row has passed for this pair")
            res.cells.append(ungraded(cell.protocol.key, cell.source, cell.reader, why,
                                      crowding=op.crowding))
            out("      %s %-10s %-9s %-7s UNGRADED: %s"
                % (ui.mark("skip"), cell.protocol.key, cell.source, cell.reader, why[:52]))
            return

    if cell.is_calibration:
        if obs.outcome_if_licensed is Outcome.EXACT:
            res.licences[cell.pair] = Calibration.from_row(obs, GOLD_SOURCES)
            issued.append(cell.pair)
        elif op.crowded:
            # ⛔ A CROWDED CALIBRATION FAILURE IS NOT "THIS READER CANNOT JUDGE". It is unknown until
            # the pair is isolated, and saying otherwise publishes the crowding as a finding.
            res.cells.append(screened(obs, op.crowding, report.block.station.name))
            res.screened_pairs.add(cell.pair)
            res.refusals[cell.pair] = ("the calibration row was screened %s in a crowded stack and "
                                       "awaits isolation" % obs.outcome_if_licensed.value)
            out("      %s %-10s %-9s %-7s screened %s — queued for isolation"
                % (ui.mark("screen"), cell.protocol.key, cell.source, cell.reader,
                   obs.outcome_if_licensed.value))
            return
        else:
            try:
                Calibration.from_row(obs, GOLD_SOURCES)
            except CalibrationRefused as e:
                res.refusals[cell.pair] = str(e)
                res.cells.append(grade(obs, None, note=str(e)))
                out("      %s %-10s %-9s %-7s CALIBRATION REFUSED"
                    % (ui.mark("bad"), cell.protocol.key, cell.source, cell.reader))
                out("          %s" % str(e))
                # ⭐ SHOW BOTH SIDES OF THE DISAGREEMENT, HERE. A registry fault is corrected by
                # comparing what was expected against what came back; sending the operator to find
                # the transcript turns a five-minute fix into a session.
                out("          expected  %s" % (cell.protocol.expect_for(cell.reader)
                                                or cell.protocol.expect))
                for line in obs.summary:
                    out("          device    %s" % line[:110])
                return

    licence = res.licences.get(cell.pair)
    if op.crowded and (obs.outcome_if_licensed is not Outcome.EXACT or licence is None):
        graded = screened(obs, op.crowding, report.block.station.name)
        out("      %s %-10s %-9s %-7s screened %s — queued for isolation"
            % (ui.mark("screen"), cell.protocol.key, cell.source, cell.reader,
               obs.outcome_if_licensed.value))
    else:
        graded = grade(obs, licence, crowding=op.crowding)
        out("      %s %-10s %-9s %-7s %s" % (graded.glyph, cell.protocol.key, cell.source,
                                             cell.reader, graded.outcome))
    res.cells.append(graded)


def _wipe(op: Op, devices: Devices, out, tag_state: TagState) -> None:
    """Clear the tag, restore its default config, and make it prove both.

    ⛔⛔ CONFIRMED BY `detect`, NOT BY SILENCE AND NOT BY THE WIPE'S OWN REPLY. The wipe lists the
    blocks it sent; that is what was transmitted, not what the tag now holds. And a silent protocol
    decoder afterwards would be weak evidence at best — a wiped tag, a tag that is not on the pad
    and a field that is off all look the same. `lf t55xx detect` answers positively: a chip replied,
    and what it is putting on the air is the wiped configuration.

    ⚠ `detect` IS NOT A BLOCK READ. It works the modulation and bit rate out from the signal, and
    the block 0 it reports is interpreted from that — which is exactly the right thing here, because
    what matters is the configuration the tag is actually transmitting.
    """
    try:
        ok, detail = devices.by_dev(op.device).wipe_t55()
    except DeviceError as e:
        ok, detail = False, str(e)
    tag_state.protocol, tag_state.writer = None, None
    tag_state.verified, tag_state.witnesses = False, set()
    tag_state.cleared = bool(ok)
    out("      %s tag wiped — %s" % (ui.mark("wipe" if ok else "bad"), detail))


def _write(op: Op, devices: Devices, out) -> bool:
    writer = devices.by_dev(op.device)
    try:
        writer.write_t55(op.protocol)
        return True
    except DeviceError as e:
        # A refused write is a registered or new firmware gap, not an abort. The reads that depended
        # on it are skipped rather than filed as the readers' failures.
        out("      %s %s could not write %s — %s"
            % (ui.mark("bad"), HUMAN[op.device], op.protocol.key, e))
        return False


def _arm(op: Op, devices: Devices, out) -> bool:
    try:
        devices.by_dev(op.device).arm(op.protocol)
        return True
    except DeviceError as e:
        out("      %s %s could not emulate %s — %s"
            % (ui.mark("bad"), HUMAN[op.device], op.protocol.key, e))
        return False


def _source_of(state) -> str:
    from .stations import WRITER_SOURCE_BY_DEV
    return WRITER_SOURCE_BY_DEV.get(state[1], "t55.pm3") if state else "t55.pm3"


def _reader_id(dev: str) -> str:
    return next(r for r, d in READERS.items() if d == dev)


def _read(op: Op, devices: Devices, session: str, pad: str, out, protocol=None, source=None,
          reader=None):
    p = protocol or op.cell.protocol
    src = source or op.cell.source
    rid = reader or op.cell.reader
    dev = devices.by_dev(op.device)
    try:
        text = dev.read(p)
    except DeviceError as e:
        cues.cue_fault("reader failed. aborting.")
        raise RunAborted("reader %s failed mid-routine: %s" % (rid, e)) from e
    return observe(p.key, src, rid, text, p.expect_for(rid) or p.expect,
                   dev.decode_marker(p), session=session, pad=pad)


def _check_marker(obs, res: RunResult, out) -> None:
    """⛔ A GOOD READ IS THE ONLY CHANCE TO CATCH A BAD MARKER. If the expectation matched but the
    marker did not fire, the marker is wrong — and it is invisible for exactly as long as the reads
    keep being correct, because a byte-exact hit stands in for it. The day it matters is the day a
    reader decodes the wrong value and the harness reports SILENT instead of WRONG, which is the
    merge the four outcomes forbid. Caught here, on the run that worked."""
    if obs is None or not obs.matched or obs.marker_fired:
        return
    pair = (obs.protocol, obs.reader)
    if pair in res.bad_markers:
        return
    # The line the operator needs to see is the one carrying the value that matched.
    lines = [l.strip() for l in obs.text.splitlines() if l.strip()]
    line = next((l for l in lines if obs.protocol and _carries_match(l, obs)), lines[-1] if lines
                else "")
    res.bad_markers[pair] = line
    out("      %s %-10s %-7s DECODE MARKER DID NOT FIRE on a byte-exact read — it would report a "
        "wrong decode as SILENT. Device said: %r"
        % (ui.mark("warn"), obs.protocol, obs.reader, line[:70]))


def _other_sources(protocol: str, state, devices: Devices) -> list:
    """Other ways to put this protocol in front of a reader — the only thing that can license one.

    ⭐ A READER IS LICENSED FOR A PROTOCOL BY SEEING IT, and it does not matter who produced it. So
    when a write cannot be attributed, the useful next step is not another reader but another
    WRITER: a tag carrying the same protocol from a different hand. If a reader decodes that, its
    silence about the first tag becomes a statement about that tag.
    """
    from .registry import ALL
    p = ALL.get(protocol)
    if p is None:
        return []
    wrote = state[1] if state else None
    out = []
    for dev, source in (("pm3", "t55.pm3"), ("cu1", "t55.cu1"), ("cu2", "t55.cu2"),
                        ("flipper", "t55.flip")):
        if dev == wrote:
            continue
        if dev == "pm3" and not p.can("pm3_write"):
            continue
        if dev in ("cu1", "cu2") and not p.can("cu_write"):
            continue
        if dev == "flipper" and not (p.flip_write and p.flip_expect):
            continue
        if getattr(devices, dev, None) is None:
            continue
        out.append("-s %s" % source)
    return out


def _carries_match(line: str, obs) -> bool:
    """The line the expectation was found on — that is what the marker should have matched."""
    from .registry import ALL
    p = ALL.get(obs.protocol)
    want = (p.expect_for(obs.reader) or p.expect) if p else None
    return bool(want) and want.lower() in line.lower()


# ------------------------------------------------------------------ controls

def _goto(frm, to, interactive: bool, devices: Devices, out, bench=None) -> None:
    """Show the bench as a picture, say the arrangement, wait.

    ⛔ THE PICTURE IS THE INSTRUCTION, and the voice says the same thing in one sentence. A delta
    ("take the tag out, then add Chameleon 1") is only meaningful against a state the operator is
    holding in their head; an arrangement can be checked against the bench in front of them. What
    must NOT be there is named under "set aside", because the forgotten device is the one that
    ruins a run and a removal spoken aloud is the easiest thing to miss.
    """
    move = plan_move(frm, to)
    if move.is_noop:
        return
    idle = sorted(bench.devices - to.devices) if bench is not None else []
    out("")
    for line in ui.diagram([to], idle):
        out(line)
    out("")
    # ⚠ A PURE REMOVAL IS SAID AS A REMOVAL. Describing the arrangement is right when something is
    # being placed, and confusing when the only thing to do is take the tag out of a stack that is
    # otherwise already correct.
    spoken = (ui.spoken_removal(move.remove) if move.remove and not move.place
              else ui.spoken_arrangement([to]))
    if interactive:
        cues.ask("     press Enter when the bench looks like that: ", spoken=spoken)
    else:
        cues.cue_move(spoken)
    if devices.operator is not None:
        devices.operator(to)


def _identity(report: BlockReport, devices: Devices, res: RunResult, out, station) -> None:
    cues.cue_check("identity check")
    try:
        report.identity = identity.check(station, devices, devices.chameleons())
    except (IdentityFault, DeviceError) as e:
        res.aborted = str(e)
        cues.cue_fault("identity check failed. aborting.")
        raise RunAborted(str(e), res) from e
    ok = report.identity.ok
    out("    %s %s" % ("✓" if ok else "⛔", identity.explain(report.identity)))
    if not ok:
        res.aborted = identity.explain(report.identity)
        cues.cue_fault("wrong device in the stack. aborting.")
        raise RunAborted(res.aborted, res)


def _sweep(label: str, empty, b: Block, devices: Devices, out) -> NullSweep:
    """Every decoder in the station, asked by every reader in it, with nothing emitting.

    ⚠ THE STACK IS ALREADY IN ITS NULL ARRANGEMENT when this is called — the caller moved it there,
    because that move is an ordinary bench instruction and not a detour taken in the middle of one.
    All this does is make sure the active devices are idle and then ask.
    """
    cues.cue_check(label)
    readers = [devices.by_dev(READERS[r]) for r in empty.readers()]
    emitters = devices.present(empty)
    sw = null_sweep(label, readers, b.protocols, emitters)
    out("    %s %s — %d reader(s) x %d decoders, %s"
        % (ui.mark("ok" if sw.clean else "bad"), label, len(readers), len(b.protocols),
           "no hits" if sw.clean else "HITS: " + ", ".join(sorted(sw.hits))))
    return sw


def _void(res: RunResult, report: BlockReport, issued, out) -> None:
    """⛔ A VOID STATION TAKES ITS LICENCES WITH IT, including rows measured at later stations."""
    names = {c.protocol.key for c in report.block.cells}
    for i, cell in enumerate(res.cells):
        if cell.protocol in names and cell.observation is not None:
            res.cells[i] = ungraded(cell.protocol, cell.source, cell.reader,
                                    "station %s is VOID: %s" % (report.block.station.name,
                                                                report.void_why),
                                    crowding=cell.crowding)
    for pair in issued:
        res.licences.pop(pair, None)
        res.refusals[pair] = ("the calibration row was taken at %s, which is VOID: %s"
                              % (report.block.station.name, report.void_why))
    for i, cell in enumerate(res.cells):
        if (cell.protocol, cell.reader) in issued and cell.outcome is not Outcome.UNGRADED:
            res.cells[i] = ungraded(cell.protocol, cell.source, cell.reader,
                                    res.refusals[(cell.protocol, cell.reader)],
                                    crowding=cell.crowding)
    out("    ▒ every cell at this station, and every row it licensed, is now UNGRADED")
