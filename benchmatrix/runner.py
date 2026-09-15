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
from dataclasses import dataclass, field

from . import cues, identity
from .devices import DeviceError, WrongDevice
from .identity import IdentityFault, NullSweep, null_sweep, sweeps_agree
from .outcomes import (Calibration, CalibrationRefused, Cell, Outcome, grade, observe, screened,
                       ungraded)
from .plan import Block, Op, RunPlan
from .stations import (CU1, CU2, FLIPPER, GOLD_SOURCES, HUMAN, PM3, READERS, T5577,
                       null_station, plan_move)


class RunAborted(Exception):
    """The run stopped because it could no longer measure anything. Never produces a grid."""


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
    #: Pairs whose calibration row was screened rather than decided. Their dependent cells are still
    #: measured — see `_routine`.
    screened_pairs: set = field(default_factory=set)
    blocks: list[BlockReport] = field(default_factory=list)
    aborted: str = ""
    finished: str = ""
    provenance: str = "bench"

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
    for dev in devices.all():
        ok, why = dev.alive()
        out("    %s %s" % ("✓" if ok else "⛔", why))
        if not ok:
            res.aborted = why
            cues.cue_fault("instrument not alive. aborting.")
            raise RunAborted(why)

    prev = None
    for report in (BlockReport(b) for b in plan.blocks):
        b = report.block
        res.blocks.append(report)
        pad = plan.bench.pad
        _move(report, prev, interactive, devices, out)
        prev = b.station

        if identity.identifiable(b.station):
            _identity(report, devices, res, out)
        elif any(d in (CU1, CU2) for d in b.station.stack):
            out("    · no radio identity check here — the only Chameleon in the stack is the one "
                "reading, and its port already says which device that is")
        report.before = _sweep("NULL BEFORE", b, devices, out, interactive)
        if not report.before.clean:
            res.aborted = ("ambient contamination at %s before anything was armed: %s"
                           % (b.station.name, ", ".join(sorted(report.before.hits))))
            cues.cue_fault("the field is not clean. aborting.")
            raise RunAborted(res.aborted)

        try:
            issued = _routine(report, devices, res, session, pad, out)
        except WrongDevice as e:
            # ⛔ Caught at the exact action it would have corrupted. Everything measured at this
            # station is about to be attributed to a device we can no longer vouch for.
            res.aborted = str(e)
            cues.cue_fault("wrong device answered. aborting.")
            raise RunAborted(str(e)) from e

        report.after = _sweep("NULL AFTER", b, devices, out, interactive)
        agree, why = sweeps_agree(report.before, report.after)
        out("    %s %s" % ("✓" if agree else "⛔", why))
        if not agree:
            report.void, report.void_why = True, why
            _void(res, report, issued, out)

    res.finished = _dt.datetime.now().isoformat(timespec="seconds")
    return res


# ------------------------------------------------------------------ the routine

def _routine(report: BlockReport, devices: Devices, res: RunResult, session: str, pad: str,
             out) -> list:
    """Run one station's routine. Everything here is hands-off except a phase-2 tag swap."""
    b = report.block
    issued: list = []
    tag_ok = True                       # did the last write read back?
    current_tag = None
    for op in b.ops:
        if b.station.has_tag and op.tag != current_tag:
            # ⚠ A TAG SWAP IS AN OPERATOR INTERVENTION LIKE ANY OTHER and is cued as one. It only
            # happens in the isolation phase, where writing a batch at one station and reading it at
            # the next is cheaper than rearranging the bench per protocol.
            if current_tag is not None:
                cues.ask("      swap to tag %d and press Enter: " % (op.tag + 1),
                         spoken="swap to tag %d" % (op.tag + 1))
            current_tag = op.tag
        if op.kind == "write":
            tag_ok = _write(op, devices, out)
            continue
        if op.kind == "arm":
            tag_ok = _arm(op, devices, out)
            continue
        if op.kind == "disarm":
            devices.by_dev(op.device).disarm()
            continue
        if op.kind == "place":
            cues.ask("      place the %s OEM card and press Enter: " % op.protocol.key,
                     spoken="place the %s card" % op.protocol.key)
            tag_ok = True
            continue

        cell = op.cell
        assert cell is not None
        if not tag_ok:
            # ⛔ RULE 4. The credential is not on the tag (or the emitter refused to arm), so this
            # read is not about this protocol at all.
            res.cells.append(ungraded(cell.protocol.key, cell.source, cell.reader,
                                      "the source was not armed — nothing to read",
                                      crowding=op.crowding))
            out("      ▒ %-10s %-9s %-7s not measured: source not armed"
                % (cell.protocol.key, cell.source, cell.reader))
            continue
        if not cell.is_calibration and cell.pair not in res.licences:
            # ⭐ A PAIR WHOSE CALIBRATION WAS ONLY *SCREENED* IS UNDECIDED, NOT REFUSED, so its
            # dependent cells are still measured. The reads are hands-off and cost nothing, and
            # skipping them would mean phase 2 rescues the calibration only to find the cells it
            # licenses were never read — which needs a third phase to fix.
            if cell.pair not in res.screened_pairs:
                why = res.refusals.get(cell.pair, "no calibration row has passed for this pair")
                res.cells.append(ungraded(cell.protocol.key, cell.source, cell.reader, why,
                                          crowding=op.crowding))
                out("      ▒ %-10s %-9s %-7s UNGRADED: %s"
                    % (cell.protocol.key, cell.source, cell.reader, why[:52]))
                continue

        obs = _read(op, devices, session, pad, out)
        if obs is None:
            continue

        if cell.is_calibration:
            if obs.outcome_if_licensed is Outcome.EXACT:
                res.licences[cell.pair] = Calibration.from_row(obs, GOLD_SOURCES)
                issued.append(cell.pair)
            elif op.crowded:
                # ⛔ A CROWDED CALIBRATION FAILURE IS NOT "THIS READER CANNOT JUDGE". It is unknown
                # until the pair is isolated, and saying otherwise would publish the crowding as a
                # finding about the reader.
                res.cells.append(screened(obs, op.crowding, report.block.station.name))
                res.screened_pairs.add(cell.pair)
                res.refusals[cell.pair] = ("the calibration row was screened %s in a crowded stack "
                                           "and awaits isolation"
                                           % obs.outcome_if_licensed.value)
                out("      ◌ %-10s %-9s %-7s screened %s — queued for isolation"
                    % (cell.protocol.key, cell.source, cell.reader,
                       obs.outcome_if_licensed.value))
                continue
            else:
                try:
                    Calibration.from_row(obs, GOLD_SOURCES)
                except CalibrationRefused as e:
                    res.refusals[cell.pair] = str(e)
                    res.cells.append(grade(obs, None, note=str(e)))
                    out("      ▒ %-10s %-9s %-7s CALIBRATION REFUSED"
                        % (cell.protocol.key, cell.source, cell.reader))
                    out("          %s" % str(e))
                    continue

        licence = res.licences.get(cell.pair)
        if op.crowded and (obs.outcome_if_licensed is not Outcome.EXACT or licence is None):
            graded = screened(obs, op.crowding, report.block.station.name)
            out("      ◌ %-10s %-9s %-7s screened %s — queued for isolation"
                % (cell.protocol.key, cell.source, cell.reader, obs.outcome_if_licensed.value))
        else:
            graded = grade(obs, licence, crowding=op.crowding)
            out("      %s %-10s %-9s %-7s %s" % (graded.glyph, cell.protocol.key, cell.source,
                                                 cell.reader, graded.outcome))
        res.cells.append(graded)
    return issued


def _write(op: Op, devices: Devices, out) -> bool:
    writer = devices.by_dev(op.device)
    try:
        writer.write_t55(op.protocol)
        return True
    except DeviceError as e:
        # A refused write is a registered or new firmware gap, not an abort. The reads that depended
        # on it are skipped rather than filed as the readers' failures.
        out("      ⛔ %s could not write %s — %s" % (HUMAN[op.device], op.protocol.key, e))
        return False


def _arm(op: Op, devices: Devices, out) -> bool:
    try:
        devices.by_dev(op.device).arm(op.protocol)
        return True
    except DeviceError as e:
        out("      ⛔ %s could not emulate %s — %s" % (HUMAN[op.device], op.protocol.key, e))
        return False


def _read(op: Op, devices: Devices, session: str, pad: str, out):
    cell = op.cell
    reader = devices.by_dev(op.device)
    try:
        text = reader.read(cell.protocol)
    except DeviceError as e:
        cues.cue_fault("reader failed. aborting.")
        raise RunAborted("reader %s failed mid-routine: %s" % (cell.reader, e)) from e
    return observe(cell.protocol.key, cell.source, cell.reader, text,
                   cell.protocol.expect_for(cell.reader) or cell.protocol.expect,
                   reader.decode_marker(cell.protocol), session=session, pad=pad)


# ------------------------------------------------------------------ controls

def _move(report: BlockReport, prev, interactive: bool, devices: Devices, out) -> None:
    move = plan_move(prev, report.block.station)
    out("\n  ══ %s ══  %s" % (report.block.station.name, move.text()))
    if not move.is_noop:
        if interactive:
            cues.ask("     press Enter when the stack is as described: ", spoken=move.spoken())
        else:
            cues.cue_move(move.spoken())
    if devices.operator is not None:
        devices.operator(report.block.station)


def _identity(report: BlockReport, devices: Devices, res: RunResult, out) -> None:
    cues.cue_check("identity check")
    try:
        report.identity = identity.check(report.block.station, devices, devices.chameleons())
    except (IdentityFault, DeviceError) as e:
        res.aborted = str(e)
        cues.cue_fault("identity check failed. aborting.")
        raise RunAborted(str(e)) from e
    ok = report.identity.ok
    out("    %s %s" % ("✓" if ok else "⛔", identity.explain(report.identity)))
    if not ok:
        res.aborted = identity.explain(report.identity)
        cues.cue_fault("wrong device in the stack. aborting.")
        raise RunAborted(res.aborted)


def _sweep(label: str, b: Block, devices: Devices, out, interactive: bool) -> NullSweep:
    """⛔ A PASSIVE TAG HAS NO IDLE STATE, so a null sweep physically removes it and puts it back.

    Disarming is enough for a Chameleon or a Flipper — reader mode puts nothing on the air. A T5577
    answers any field it is in, so a sweep taken with it still in the stack reports the credential
    the routine just wrote and declares the bench contaminated (RULES.md §3).
    """
    null = null_station(b.station)
    moved = null.devices != b.station.devices
    gone = [d for d in b.station.stack if d not in null.devices]
    if moved:
        _reposition("%s: take %s out" % (label.lower(), ", ".join(HUMAN[d] for d in gone)),
                    null, devices, interactive, out)
    cues.cue_check(label.lower())
    readers = [devices.by_dev(READERS[r]) for r in b.station.readers()]
    emitters = devices.present(b.station)
    sw = null_sweep(label, readers, b.protocols, emitters)
    out("    %s %s — %d reader(s) x %d decoders, %s"
        % ("✓" if sw.clean else "⛔", label, len(readers), len(b.protocols),
           "no hits" if sw.clean else "HITS: " + ", ".join(sorted(sw.hits))))
    if moved:
        _reposition("put %s back" % ", ".join(HUMAN[d] for d in gone),
                    b.station, devices, interactive, out)
    return sw


def _reposition(instruction: str, station, devices: Devices, interactive: bool, out) -> None:
    out("      ↔ %s" % instruction)
    if interactive:
        cues.ask("       press Enter when done: ", spoken=instruction)
    else:
        cues.cue_move(instruction)
    if devices.operator is not None:
        devices.operator(station)


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
