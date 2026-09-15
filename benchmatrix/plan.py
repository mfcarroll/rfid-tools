"""The run plan: which cells get measured, which are refused, and in what physical order.

⛔⛔ THE CALIBRATION ROW IS INJECTED HERE, BY THE PLANNER, AND THERE IS NO WAY TO ASK IT NOT TO.
DESIGN.md §2.1: for every reader R and protocol P in a run, the plan MUST contain a real-tag row
(t55.pm3, R) for P. That is not checked at the end and it is not a warning — a (P, R) pair with no
licensable source is REMOVED FROM THE PLAN, with the reason printed, because a block that cannot be
graded should not consume bench time pretending it might be.

⭐ THE THREE REFUSALS, ALL AT PLAN TIME RATHER THAN AS FAILED CELLS:
  • M52 — `(emu.*, rd.cu)` for a subcarrier protocol. DESIGN.md §5 says the harness must REFUSE
    these "rather than record them as failures", and a refusal that happens after the read has been
    taken is not a refusal, it is a deletion.
  • no known expectation — `rd.flip` for a protocol whose Flipper hex we have never seen. There is
    no pass condition to compare against, so there is nothing to measure. `bench learn` fixes it.
  • no licensable source — P cannot go on a T5577 and no OEM card is owned, so no row can ever
    license R for P. The pair is dropped rather than run and marked UNGRADED sixteen times.

⚠ AN EXCLUSION IS A PUBLISHED RESULT, NOT A SILENT SKIP. Every one is carried into the grid with
its rule and its reason. "We did not test this" is a different statement from "this failed", and
the grid has to be able to say which.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import registry as reg
from .topology import (Bench, EMULATED_SOURCES, SOURCES, READERS, Topology,
                       TopologyError, plan_move, topology_for)


@dataclass(frozen=True)
class PlannedCell:
    protocol: reg.Protocol
    source: str
    reader: str
    topology: Topology
    is_calibration: bool = False

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.protocol.key, self.source, self.reader)


@dataclass(frozen=True)
class Exclusion:
    protocol: str
    source: str
    reader: str
    rule: str
    why: str


#: Sources that are a physical tag on the pad, and who has to write them.
TAG_SOURCES = {"t55.pm3": "pm3", "t55.flip": "flipper", "oem": None}


@dataclass(frozen=True)
class Step:
    """One thing the harness does while the bench is in one arrangement.

    ⛔⛔ `write` IS A STEP, NOT A DETAIL OF `read`. There is ONE T5577 and sixteen credentials, so a
    `t55.pm3` row measured on any reader other than the Proxmark means physically carrying the tag
    back to be rewritten between protocols. Modelling the write as part of the read hides that: the
    run would read whatever the tag still held from the PREVIOUS protocol and file it as SILENT for
    this one — a wrong cell with a plausible-looking cause, which is the worst kind.
    """

    kind: str                       # write | read
    topology: Topology
    protocol: reg.Protocol
    writer: str = ""                # pm3 | flipper, for kind == write
    cell: PlannedCell | None = None  # for kind == read


@dataclass
class Block:
    """Consecutive steps that share one arrangement. One move gets you into it."""

    topology: Topology
    steps: list[Step] = field(default_factory=list)

    @property
    def cells(self) -> list[PlannedCell]:
        return [s.cell for s in self.steps if s.kind == "read" and s.cell is not None]

    @property
    def writes(self) -> list[reg.Protocol]:
        return [s.protocol for s in self.steps if s.kind == "write"]


@dataclass
class RunPlan:
    bench: Bench
    blocks: list[Block]
    exclusions: list[Exclusion]

    @property
    def cells(self) -> list[PlannedCell]:
        return [c for b in self.blocks for c in b.cells]

    @property
    def pairs(self) -> set[tuple[str, str]]:
        return {(c.protocol.key, c.reader) for c in self.cells}

    def calibration_for(self, protocol: str, reader: str) -> PlannedCell | None:
        for c in self.cells:
            if c.is_calibration and c.protocol.key == protocol and c.reader == reader:
                return c
        return None

    def moves(self):
        prev = None
        for b in self.blocks:
            yield plan_move(prev, b.topology), b
            prev = b.topology

    def audit(self) -> list[str]:
        """⛔ THE INVARIANT, RE-CHECKED AFTER CONSTRUCTION.

        `build()` is supposed to make all three of these impossible; they are asserted anyway,
        because the cost of the builder and the invariant disagreeing is a grid that looks licensed
        and is not.
        """
        bad = []
        for p, r in sorted(self.pairs):
            if self.calibration_for(p, r) is None:
                bad.append("(%s, %s) is in the plan with no calibration row" % (p, r))
        # Every read of a tag source must be preceded, in step order, by a write of THAT protocol —
        # except `oem`, which the operator supplies and nothing writes.
        held: str | None = None
        for b in self.blocks:
            for s in b.steps:
                if s.kind == "write":
                    held = s.protocol.key
                elif s.cell is not None and s.cell.source in TAG_SOURCES:
                    if s.cell.source == "oem":
                        continue
                    if held != s.protocol.key:
                        bad.append("(%s, %s, %s) reads the tag while it holds %r"
                                   % (s.protocol.key, s.cell.source, s.cell.reader, held))
        # A calibration row must come before the rows it licenses, in the order the bench runs them.
        seen_cal: set[tuple[str, str]] = set()
        for b in self.blocks:
            for s in b.steps:
                if s.cell is None:
                    continue
                pair = (s.cell.protocol.key, s.cell.reader)
                if s.cell.is_calibration:
                    seen_cal.add(pair)
                elif pair not in seen_cal:
                    bad.append("(%s, %s, %s) is measured BEFORE its calibration row"
                               % (pair[0], s.cell.source, pair[1]))
        return bad


def _sequence(cells: list[PlannedCell], bench: Bench) -> list[Step]:
    """Order the cells into steps, cheapest in bench moves.

    ⭐ THE ORDER IS CHOSEN TO KEEP EACH READER'S WORK IN ONE VISIT, because a licence is only good
    for the pad it was taken on and a reader that gets picked up and put down is a different pad.
    Within a reader: the tag rows first (they carry the licence), then each emulator in turn.

    ⚠ THE TAG ROWS ARE WHERE THE MOVES ARE. On the Proxmark the write and the read happen in one
    arrangement, so sixteen protocols cost one move. On any other reader each protocol costs two,
    and there is no way around it with one T5577 — so the planner does not pretend otherwise, it
    just makes the trips explicit and lets the run-length estimate tell the operator the truth.
    """
    steps: list[Step] = []
    reader_order = ["rd.pm3", "rd.flip", "rd.cu"]
    by_reader: dict[str, list[PlannedCell]] = {}
    for c in cells:
        by_reader.setdefault(c.reader, []).append(c)

    for reader in sorted(by_reader, key=lambda r: reader_order.index(r)):
        group = by_reader[reader]
        tag_cells = [c for c in group if c.source in TAG_SOURCES]
        emu_cells = [c for c in group if c.source not in TAG_SOURCES]

        # --- tag rows, grouped by which source (and therefore which writer)
        for source in ("t55.pm3", "t55.flip", "oem"):
            here = [c for c in tag_cells if c.source == source]
            if not here:
                continue
            here.sort(key=lambda c: _rank(c.protocol.key))
            writer = TAG_SOURCES[source]
            for c in here:
                if writer is not None:
                    wdev = {"pm3": "pm3", "flipper": "flipper"}[writer]
                    steps.append(Step("write", Topology(_wname(wdev), wdev, ("t5577",)),
                                      c.protocol, writer=writer))
                steps.append(Step("read", c.topology, c.protocol, cell=c))

        # --- emulator rows, grouped by emitter so each is armed once and read through
        emu_cells.sort(key=lambda c: (c.source, _rank(c.protocol.key)))
        for c in emu_cells:
            steps.append(Step("read", c.topology, c.protocol, cell=c))
    return steps


def _rank(key: str) -> int:
    """Registry order where we have one, and after it otherwise — a tier-1 protocol added later
    must not crash the sequencer just because `TIER0_ORDER` has never heard of it."""
    return reg.TIER0_ORDER.index(key) if key in reg.TIER0_ORDER else len(reg.TIER0_ORDER)


def _wname(dev: str) -> str:
    return {"pm3": "PM3_T55", "flipper": "FLIP_T55"}[dev]


def _blocks(steps: list[Step]) -> list[Block]:
    """Collapse consecutive same-topology steps into one block — one move each."""
    out: list[Block] = []
    for s in steps:
        if not out or out[-1].topology.name != s.topology.name:
            out.append(Block(s.topology))
        out[-1].steps.append(s)
    return out


def licensing_source(p: reg.Protocol, bench: Bench) -> str | None:
    """The real-tag source that can license this protocol on this bench, or None.

    DESIGN.md §2.1: `t55.pm3`, "or `oem` where a T5577 cannot hold P".
    """
    if p.t55_capable:
        return "t55.pm3"
    return "oem" if p.key in bench.has_oem else None


def _refuse(p: reg.Protocol, source: str, reader: str, bench: Bench) -> Exclusion | None:
    """Every reason a cell must not be planned. Order matters only for which reason is reported."""
    # M52 — DESIGN.md §5.
    if p.m52 and source in EMULATED_SOURCES and reader == "rd.cu":
        return Exclusion(p.key, source, reader, "M52",
                         "subcarrier-dependent: the PSK/subcarrier family needs a subcarrier "
                         "phase-locked to the reader's carrier, which only a real tag has. A SAADC "
                         "read arm tested against an emulation measures the bench, not the arm.")
    if reader == "rd.cu" and p.cu_read is None:
        return Exclusion(p.key, source, reader, "no-read-arm",
                         "no Chameleon read command is registered for %s. `rd.cu` is the arm under "
                         "test, not a general-purpose judge, and grading against a channel that "
                         "raises is not the same as measuring one that is silent." % p.key)
    # A device cannot judge itself.
    try:
        topology_for(source, reader, bench)
    except TopologyError as e:
        return Exclusion(p.key, source, reader, "self-judging", str(e))
    # No pass condition on the Flipper.
    if reader == "rd.flip" and p.flip_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "the Flipper's decoded hex for %s has never been observed, so there is no "
                         "byte-exact token to compare against. Matching on the protocol NAME alone "
                         "is the M28 trap. Run `bench learn --protocol %s` from a real tag."
                         % (p.key, p.key))
    if source == "emu.flip" and p.flip_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "`rfid emulate` needs the Flipper's own hex for %s, which is unknown."
                         % p.key)
    if source == "t55.flip" and not p.flip_write:
        return Exclusion(p.key, source, reader, "gap:flipper-write",
                         "the Flipper cannot write %s to a T5577 that the pm3 writes fine "
                         "(DESIGN.md §4). This source does not exist for this protocol." % p.key)
    if source == "t55.flip" and p.flip_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "`rfid write` needs the Flipper's own hex for %s, which is unknown." % p.key)
    if source == "oem" and p.key not in bench.has_oem:
        return Exclusion(p.key, source, reader, "no-card",
                         "no genuine %s credential is owned on this bench." % p.key)
    if source in ("emu.cu2",) and not bench.has_cu2:
        return Exclusion(p.key, source, reader, "no-device", "Chameleon #2 is not on this bench.")
    if (source == "emu.flip" or reader == "rd.flip") and not bench.has_flipper:
        return Exclusion(p.key, source, reader, "no-device", "no Flipper on this bench.")
    return None


def build(protocols: list[reg.Protocol], sources: list[str], readers: list[str],
          bench: Bench) -> RunPlan:
    """Expand a request into a plan, injecting the calibration rows it needs to be gradeable."""
    for s in sources:
        if s not in SOURCES:
            raise ValueError("unknown source %r (known: %s)" % (s, ", ".join(SOURCES)))
    for r in readers:
        if r not in READERS:
            raise ValueError("unknown reader %r (known: %s)" % (r, ", ".join(READERS)))

    wanted: dict[tuple[str, str, str], PlannedCell] = {}
    exclusions: list[Exclusion] = []

    def consider(p: reg.Protocol, source: str, reader: str, is_cal: bool) -> bool:
        why = _refuse(p, source, reader, bench)
        if why is not None:
            exclusions.append(why)
            return False
        cell = PlannedCell(p, source, reader, topology_for(source, reader, bench), is_cal)
        prev = wanted.get(cell.key)
        # A cell that is both requested and needed as a calibration row is ONE cell, marked as the
        # calibration — it is measured once and does both jobs.
        if prev is None or (is_cal and not prev.is_calibration):
            wanted[cell.key] = cell
        return True

    for p in protocols:
        for reader in readers:
            requested = [s for s in sources if s != licensing_source(p, bench)]
            # ⛔ THE CALIBRATION ROW FIRST, AND THE PAIR IS DROPPED IF IT CANNOT BE PLANNED.
            lic = licensing_source(p, bench)
            if lic is None:
                exclusions.append(Exclusion(
                    p.key, "-", reader, "unlicensable",
                    "%s cannot be held by a T5577 and no OEM card is owned, so no row can license "
                    "%s for it. DESIGN.md §2.1 leaves no third option, so the pair is not planned "
                    "rather than run and reported UNGRADED." % (p.key, reader)))
                continue
            if not consider(p, lic, reader, True):
                # The licensing row itself is refused, so nothing else for this pair can be graded.
                # ⛔ BUT A CELL'S OWN REFUSAL IS REPORTED IN PREFERENCE TO "no-calibration", because
                # the two have different lifetimes. M52 is a statement about physics and will still
                # hold when the Chameleon has read arms; a missing licence is a fact about today's
                # bench. Reporting the temporary reason and hiding the permanent one told the
                # operator that registering a read command would open up five cells that the design
                # refuses on purpose.
                # ⚠ `no-calibration` is a FALLBACK and is currently unreachable: every rule in
                # force refuses a (protocol, reader) pair regardless of source, so a cell whose
                # licence is refused is refused for the same reason itself. It is kept for a rule
                # that refuses only the licensing source — and if one is ever added, this is where
                # it lands rather than silently producing a plan with an unlicensed pair in it.
                for src in requested:
                    own = _refuse(p, src, reader, bench)
                    exclusions.append(own or Exclusion(
                        p.key, src, reader, "no-calibration",
                        "the licensing row (%s, %s) is itself refused, so this cell could only ever "
                        "be UNGRADED." % (lic, reader)))
                continue
            for s in requested:
                consider(p, s, reader, False)

    # ⛔ CALIBRATION ROWS FIRST WITHIN EACH READER. A block whose licence fails should spend no
    # further bench time, and a row measured before its licence cannot be licensed by it at all —
    # `audit()` refuses a plan where that happened.
    cells = sorted(wanted.values(),
                   key=lambda c: (not c.is_calibration, _rank(c.protocol.key)))
    blocks = _blocks(_sequence(cells, bench))
    plan = RunPlan(bench=bench, blocks=blocks, exclusions=exclusions)
    bad = plan.audit()
    if bad:
        raise AssertionError("plan.build produced an ungradeable plan:\n  " + "\n  ".join(bad))
    return plan
