"""The campaign: moves, controls, reads, and the grading that refuses to happen without a licence.

Run shape, per block:

    move cue  ->  operator confirms  ->  RADIO IDENTITY CHECK  ->  null sweep BEFORE
              ->  the block's writes and reads  ->  null sweep AFTER  ->  A/B/A comparison

⛔⛔ THREE THINGS ABORT OR VOID RATHER THAN DEGRADE, AND EACH ONE COST A SESSION TO LEARN:
  1. A DEAD INSTRUMENT ABORTS THE RUN. A silent reader and a silent emulator produce identical
     numbers — eleven arms were once read as "the emulator is silent" when the truth was
     "the reader was never listening", and it stood as a firmware unit until something contradicted
     it. Proof of life is taken before anything is measured and again whenever a channel raises.
  2. A WRONG DEVICE ABORTS THE RUN. Not "warns" — everything under that topology would be
     attributed to the wrong Chameleon, and the null arms cannot catch it (RULES.md §4).
  3. A DISAGREEING A/B/A VOIDS THE BLOCK AND REVOKES ANY LICENCE IT ISSUED. A licence is a claim
     about a bench that was stable while the control was taken; if the block turns out not to have
     been stable, the claim goes with it — including for rows in LATER blocks that it licensed.

⚠ AND ONE THING IS DELIBERATELY NOT AN ABORT. A calibration row that comes back SILENT is a RESULT:
"reader R cannot judge P on this bench". The run carries on to the next pair, and every emulated row
for that pair is UNGRADED without being measured — there is no point spending bench time on reads
nothing can license.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import cues, identity, registry as reg
from .devices import DeviceError
from .identity import IdentityFault, NullSweep, null_sweep, sweeps_agree
from .outcomes import (Calibration, CalibrationRefused, Cell, Outcome, grade, observe, ungraded)
from .plan import Block, PlannedCell, RunPlan, Step
from .topology import (CU1, CU2, FLIPPER, HUMAN, PM3, REAL_SOURCES, SOURCES,
                       null_topology, plan_move)


class RunAborted(Exception):
    """The run stopped because it could no longer measure anything. Never produces a grid."""


@dataclass
class BlockReport:
    block: Block
    identity: identity.IdentityResult | None = None
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
    licences: dict = field(default_factory=dict)          # (proto, reader) -> Calibration
    refusals: dict = field(default_factory=dict)          # (proto, reader) -> str
    blocks: list[BlockReport] = field(default_factory=list)
    aborted: str = ""
    finished: str = ""
    #: ⛔⛔ WHAT PRODUCED THESE NUMBERS. A grid from `Scripted` devices is indistinguishable from a
    #: bench grid once it is a table of ticks — and this project exists because a grid that looked
    #: like a result was not one. Every render and every JSON dump carries this, and a dry run says
    #: so in its first line rather than in a footnote.
    provenance: str = "bench"

    @property
    def void_blocks(self) -> list[BlockReport]:
        return [b for b in self.blocks if b.void]

    @property
    def usable(self) -> bool:
        return not self.aborted


@dataclass
class Devices:
    """Whatever this run has to talk to. Readers and emitters are looked up by device id."""

    pm3: object | None = None
    flipper: object | None = None
    cu1: object | None = None
    cu2: object | None = None
    #: ⭐ THE SEAM THAT MAKES A HEADLESS RUN HONEST. On a real bench the operator performs the move
    #: and the harness has no way to do it for them, so this is None. The tests supply a callable
    #: that rearranges the scripted bench — an operator who always does exactly what was asked —
    #: which is what lets the identity check and the null sweeps be exercised without hardware
    #: instead of being stubbed out, which would test nothing.
    operator: object | None = None

    def by_dev(self, dev: str):
        got = {PM3: self.pm3, FLIPPER: self.flipper, CU1: self.cu1, CU2: self.cu2}.get(dev)
        if got is None:
            raise RunAborted("the plan needs %s and this run has no channel for it" % HUMAN[dev])
        return got

    def chameleons(self) -> dict:
        return {d: c for d, c in ((CU1, self.cu1), (CU2, self.cu2)) if c is not None}

    def all(self) -> list:
        return [d for d in (self.pm3, self.flipper, self.cu1, self.cu2) if d is not None]


def session_id() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def run(plan: RunPlan, devices: Devices, *, interactive: bool = True,
        session: str | None = None, out=print) -> RunResult:
    session = session or session_id()
    scripted = any(type(d).__name__ == "Scripted" for d in devices.all())
    res = RunResult(session=session, started=_dt.datetime.now().isoformat(timespec="seconds"),
                    plan=plan, provenance="dry-run (scripted devices)" if scripted else "bench")

    # ---------------------------------------------------------------- proof of life, before anything
    out("\n  run %s — %d cells, %d blocks, %d exclusions"
        % (session, len(plan.cells), len(plan.blocks), len(plan.exclusions)))
    for dev in devices.all():
        ok, why = dev.alive()
        out("    %s %s" % ("✓" if ok else "⛔", why))
        if not ok:
            res.aborted = why
            cues.cue_fault("instrument not alive. aborting.")
            raise RunAborted(why)

    prev_topology = None
    for report in (BlockReport(b) for b in plan.blocks):
        b = report.block
        res.blocks.append(report)
        reader = devices.by_dev(b.topology.reader_dev)
        # ⚠ THE PAD IS PER-READER AND CONSTANT FOR THE SESSION. "Same pad, same antenna position"
        # (RULES.md §1) is a claim about the READER not having been repositioned — the tag and
        # the Chameleons coming and going is the experiment, not a change of pad. Start a new
        # session id if a reader is physically moved mid-run; that is what invalidates a licence.
        pad = "%s@%s" % (b.topology.reader_dev, plan.bench.pad)

        _move(report, prev_topology, interactive, out)
        if devices.operator is not None:
            devices.operator(b.topology)
        prev_topology = b.topology

        block_protocols = _block_protocols(b)
        emitters = [devices.by_dev(d) for d in b.topology.on_pad if d in (CU1, CU2, FLIPPER)]

        # ------------------------------------------------------------ identity, then null BEFORE
        if any(d in (CU1, CU2) for d in b.topology.on_pad):
            cues.cue_check("identity check")
            try:
                report.identity = identity.check(b.topology, reader, devices.chameleons())
            except (IdentityFault, DeviceError) as e:
                res.aborted = str(e)
                cues.cue_fault("identity check failed. aborting.")
                raise RunAborted(str(e)) from e
            out("    %s %s" % ("✓" if report.identity.ok else "⛔", identity.explain(report.identity)))
            if not report.identity.ok:
                res.aborted = identity.explain(report.identity)
                cues.cue_fault("wrong device on the pad. aborting.")
                raise RunAborted(res.aborted)

        report.before = _sweep("NULL BEFORE", reader, block_protocols, emitters, out,
                               b.topology, devices, interactive)
        if not report.before.clean:
            res.aborted = ("ambient contamination in %s before anything was armed: %s"
                           % (b.topology.name, ", ".join(sorted(report.before.hits))))
            cues.cue_fault("the field is not clean. aborting.")
            raise RunAborted(res.aborted)

        # ------------------------------------------------------------ the block's own work
        issued: list[tuple[str, str]] = []
        for step in b.steps:
            if step.kind == "write":
                _write(step, devices, out)
                continue
            cell = step.cell
            assert cell is not None
            pair = (cell.protocol.key, cell.reader)
            if not cell.is_calibration and pair not in res.licences:
                why = res.refusals.get(pair, "no calibration row has passed for this pair")
                res.cells.append(ungraded(cell.protocol.key, cell.source, cell.reader, why))
                out("      ▒ %-10s %-9s UNGRADED — not measured: %s"
                    % (cell.protocol.key, cell.source, why[:64]))
                continue
            obs = _read(cell, devices, reader, pad, session, out)
            if obs is None:                      # the channel is dead; _read already aborted
                continue
            if cell.is_calibration:
                try:
                    lic = Calibration.from_row(obs, REAL_SOURCES)
                except CalibrationRefused as e:
                    res.refusals[pair] = str(e)
                    res.cells.append(grade(obs, None, note=str(e)))
                    out("      ▒ %-10s %-9s %s" % (cell.protocol.key, cell.source,
                                                   "CALIBRATION REFUSED"))
                    out("          %s" % str(e))
                    continue
                res.licences[pair] = lic
                issued.append(pair)
            graded = grade(obs, res.licences.get(pair))
            res.cells.append(graded)
            out("      %s %-10s %-9s %s" % (graded.glyph, cell.protocol.key, cell.source,
                                            graded.outcome))

        # ------------------------------------------------------------ null AFTER, and A/B/A
        report.after = _sweep("NULL AFTER", reader, block_protocols, emitters, out,
                              b.topology, devices, interactive)
        agree, why = sweeps_agree(report.before, report.after)
        out("    %s %s" % ("✓" if agree else "⛔", why))
        if not agree:
            report.void, report.void_why = True, why
            _void_block(res, report, issued, out)

    res.finished = _dt.datetime.now().isoformat(timespec="seconds")
    return res


# ------------------------------------------------------------------ pieces

def _block_protocols(b: Block) -> list[reg.Protocol]:
    seen, out = set(), []
    for s in b.steps:
        if s.protocol.key not in seen:
            seen.add(s.protocol.key)
            out.append(s.protocol)
    return out


def _move(report: BlockReport, prev, interactive: bool, out) -> None:
    move = plan_move(prev, report.block.topology)
    out("\n  ── %s ──  %s" % (report.block.topology.name, move.text()))
    if move.is_noop:
        return
    if interactive:
        cues.ask("     press Enter when the bench is as described: ", spoken=move.spoken())
    else:
        cues.cue_move(move.spoken())


def _sweep(label, reader, protocols, emitters, out, topology, devices, interactive) -> NullSweep:
    """⛔⛔ A PASSIVE TAG HAS NO IDLE STATE, SO A NULL SWEEP HAS TO PHYSICALLY REMOVE IT.

    Disarming the emitters is enough for a Chameleon or a Flipper — reader mode puts nothing on the
    air. A T5577 is not like that: it answers the reader's field whenever it is in one, so a sweep
    taken with the tag still on the pad reports the credential the block just wrote and declares the
    bench contaminated. The first version of this runner did exactly that and voided its own opening
    block, which is the correct behaviour for the sweep it actually took and the wrong sweep to have
    taken. `topology.null_topology()` already said so; this is the runner honouring it.

    ⚠ The move back is cued too. Leaving the operator holding the tag and carrying on would measure
    the next step with an empty pad.
    """
    null_t = null_topology(topology)
    moved = set(null_t.on_pad) != set(topology.on_pad)
    if moved:
        away = [d for d in topology.on_pad if d not in null_t.on_pad]
        _reposition("%s: take %s off the pad" % (label.lower(), ", ".join(HUMAN[d] for d in away)),
                    null_t, devices, interactive, out)
    cues.cue_check(label.lower())
    sw = null_sweep(label, reader, protocols, emitters)
    out("    %s %s — %d decoders asked, %s"
        % ("✓" if sw.clean else "⛔", label, len(protocols),
           "no hits" if sw.clean else "HITS: " + ", ".join(sorted(sw.hits))))
    if moved:
        back = [d for d in topology.on_pad if d not in null_t.on_pad]
        _reposition("put %s back on %s" % (", ".join(HUMAN[d] for d in back),
                                           HUMAN[topology.reader_dev]),
                    topology, devices, interactive, out)
    return sw


def _reposition(instruction: str, topology, devices, interactive: bool, out) -> None:
    out("      ↔ %s" % instruction)
    if interactive:
        cues.ask("       press Enter when done: ", spoken=instruction)
    else:
        cues.cue_move(instruction)
    if devices.operator is not None:
        devices.operator(topology)


def _write(step: Step, devices: Devices, out) -> None:
    writer = devices.by_dev(PM3 if step.writer == "pm3" else FLIPPER)
    try:
        writer.write_t55(step.protocol)
        out("      ✎ wrote %s to the T5577 with %s" % (step.protocol.key, step.writer))
    except DeviceError as e:
        # ⚠ A REFUSED WRITE IS NOT AN ABORT. It is a registered firmware gap (the gap register) or a new
        # one; either way the rows that depend on it become UNGRADED through the ordinary path,
        # because the tag will not hold what they expect and the calibration will say so.
        out("      ⛔ write refused for %s — %s" % (step.protocol.key, e))


def _read(cell: PlannedCell, devices: Devices, reader, pad: str, session: str, out):
    """Arm the source if it is an emitter, take the read, and turn it into an Observation."""
    src_dev = SOURCES[cell.source][0]
    emitter = None
    if src_dev in (CU1, CU2, FLIPPER):
        emitter = devices.by_dev(src_dev)
        try:
            emitter.arm(cell.protocol)
        except DeviceError as e:
            out("      ⛔ %-10s %-9s could not be armed — %s" % (cell.protocol.key, cell.source, e))
            return None
    try:
        text = reader.read(cell.protocol)
    except DeviceError as e:
        cues.cue_fault("reader failed. aborting.")
        raise RunAborted("reader %s failed mid-block: %s" % (cell.reader, e)) from e
    finally:
        if emitter is not None:
            emitter.disarm()
    return observe(cell.protocol.key, cell.source, cell.reader, text, cell.protocol.expect,
                   reader.decode_marker(cell.protocol), session=session, pad=pad)


def _void_block(res: RunResult, report: BlockReport, issued, out) -> None:
    """⛔ A VOID BLOCK TAKES ITS LICENCES WITH IT, INCLUDING ROWS IN LATER BLOCKS.

    A licence is a claim that the bench was stable while the control was taken. If the block the
    control came from turns out not to have been stable, the claim does not survive — and neither
    does anything it licensed, wherever that was measured. Revoking only the block's own cells would
    leave licensed rows standing on a control that has just been withdrawn.
    """
    names = {c.protocol.key for c in report.block.cells}
    for i, cell in enumerate(res.cells):
        if cell.protocol in names and cell.observation is not None:
            res.cells[i] = ungraded(cell.protocol, cell.source, cell.reader,
                                    "block %s is VOID: %s" % (report.block.topology.name,
                                                              report.void_why))
    for pair in issued:
        res.licences.pop(pair, None)
        res.refusals[pair] = ("the calibration row was taken in block %s, which is VOID: %s"
                              % (report.block.topology.name, report.void_why))
    for i, cell in enumerate(res.cells):
        if (cell.protocol, cell.reader) in issued and cell.outcome is not Outcome.UNGRADED:
            res.cells[i] = ungraded(cell.protocol, cell.source, cell.reader,
                                    res.refusals[(cell.protocol, cell.reader)])
    out("    ▒ %d cells in this block, and every row licensed by it, are now UNGRADED"
        % len(report.block.cells))
