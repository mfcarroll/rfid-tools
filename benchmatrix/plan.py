"""Turning a request into stations, routines and refusals.

Three stages, in order:

  1. **Cells.** Expand (protocols x sources x readers), refuse what cannot be measured, and inject
     the gold calibration row every (protocol, reader) pair needs. A pair whose calibration cannot
     be planned is dropped entirely rather than run and reported UNGRADED sixteen times.
  2. **Stations.** Cover those cells with as few physical arrangements as possible, because an
     arrangement is what costs operator time. Greedy set cover over device sets, capped at the
     bench's stack limit.
  3. **Routines.** Order each station's work so one setup yields every cell it can: at a tag
     station, write with each writer in turn and read with every reader after each write.

⛔⛔ THE CALIBRATION ROW IS INJECTED HERE AND THERE IS NO WAY TO ASK FOR IT NOT TO BE (RULES.md §1).
`audit()` re-checks the result independently of the builder, because the cost of the two disagreeing
is a grid that looks licensed and is not.

⛔ REFUSALS HAPPEN AT PLAN TIME, NOT AS FAILED CELLS. A refusal taken after the read is a deletion,
not a refusal — and an exclusion is a published result with a reason, which is a different statement
from "this failed".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import registry as reg
from .stations import (Bench, EMULATED_SOURCES, GOLD_SOURCES, HUMAN, READERS, SOURCES, STACK_ORDER,
                       Station, StationError, TAGS, TAG_SOURCES, T5577, build_station,
                       devices_to_measure,
                       devices_to_produce, move_cost, plan_move, station_admits)

#: Writers, in the order a routine should use them. The Proxmark first because its row is the gold
#: reference that licenses everything else measured at that station.
WRITER_ORDER = ("pm3", "flipper", "cu1", "cu2")
WRITER_SOURCE = {"pm3": "t55.pm3", "flipper": "t55.flip", "cu1": "t55.cu1", "cu2": "t55.cu2"}


@dataclass(frozen=True)
class PlannedCell:
    protocol: reg.Protocol
    source: str
    reader: str
    is_calibration: bool = False

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.protocol.key, self.source, self.reader)

    @property
    def pair(self) -> tuple[str, str]:
        return (self.protocol.key, self.reader)


@dataclass(frozen=True)
class Exclusion:
    protocol: str
    source: str
    reader: str
    rule: str
    why: str


@dataclass(frozen=True)
class Op:
    """One automated device action inside a routine. No operator involvement.

    ⭐ `verify` IS A READ THAT PRODUCES NO CELL. Its only job is to witness that a write landed, so
    that the reads which follow can be attributed to their readers instead of being ambiguous
    between "this reader is deaf" and "the credential is not on the tag" (RULES.md §10). It is added
    wherever a writer can read its own work back and no wanted cell already does that.
    """

    kind: str                       # write | arm | disarm | read | verify | place
    device: str
    protocol: reg.Protocol
    cell: PlannedCell | None = None
    crowding: frozenset[str] = frozenset()
    #: Which physical tag this op uses. Only phase 2 uses more than one, and only because writing a
    #: batch of tags at one station and reading the batch at the next is what turns two
    #: interventions per protocol into two per batch.
    tag: int = 0

    @property
    def crowded(self) -> bool:
        return bool(self.crowding)


@dataclass
class Block:
    """One station, and the routine run there. One operator intervention gets you into it."""

    station: Station
    ops: list[Op] = field(default_factory=list)

    @property
    def cells(self) -> list[PlannedCell]:
        return [o.cell for o in self.ops if o.kind == "read" and o.cell is not None]

    @property
    def protocols(self) -> list[reg.Protocol]:
        seen, out = set(), []
        for o in self.ops:
            if o.protocol.key not in seen:
                seen.add(o.protocol.key)
                out.append(o.protocol)
        return out


@dataclass
class RunPlan:
    bench: Bench
    blocks: list[Block]
    exclusions: list[Exclusion]
    phase: int = 1

    @property
    def cells(self) -> list[PlannedCell]:
        return [c for b in self.blocks for c in b.cells]

    @property
    def pairs(self) -> set[tuple[str, str]]:
        return {c.pair for c in self.cells}

    @property
    def interventions(self) -> int:
        """What the run actually costs the operator: one per station, plus the null-sweep round
        trips a station with a tag in it needs."""
        return sum(1 + (2 if b.station.has_tag else 0) for b in self.blocks)

    def calibration_for(self, protocol: str, reader: str) -> PlannedCell | None:
        for c in self.cells:
            if c.is_calibration and c.protocol.key == protocol and c.reader == reader:
                return c
        return None

    def moves(self):
        prev = None
        for b in self.blocks:
            yield plan_move(prev, b.station), b
            prev = b.station

    def audit(self) -> list[str]:
        """The invariants, checked independently of the builder that is meant to guarantee them."""
        bad = []
        for p, r in sorted(self.pairs):
            if self.calibration_for(p, r) is None:
                bad.append("(%s, %s) is in the plan with no calibration row" % (p, r))

        held: tuple[str, str] | None = None          # (protocol, writer) currently on the tag
        armed: dict[str, str] = {}                   # device -> protocol it is emulating
        seen_cal: set[tuple[str, str]] = set()
        for b in self.blocks:
            for o in b.ops:
                if o.kind == "write":
                    held = (o.protocol.key, o.device)
                elif o.kind == "place":
                    held = (o.protocol.key, None)
                elif o.kind == "arm":
                    armed[o.device] = o.protocol.key
                elif o.kind == "disarm":
                    armed.pop(o.device, None)
                elif o.kind in ("read", "verify") and o.cell is not None:
                    c = o.cell
                    if c.source in TAG_SOURCES:
                        writer = SOURCES[c.source][1]
                        want = (c.protocol.key, writer)
                        if held != want:
                            bad.append("(%s) reads the tag while it holds %r"
                                       % (" / ".join(c.key), held))
                    else:
                        dev = SOURCES[c.source][0]
                        if armed.get(dev) != c.protocol.key:
                            bad.append("(%s) reads %s while it emulates %r"
                                       % (" / ".join(c.key), HUMAN[dev], armed.get(dev)))
                    # ⛔ ONE EMITTER. A tag in the stack answers any field it is in, so an emulated
                    # read taken with a tag present cannot say which of the two the reader heard.
                    if c.source in EMULATED_SOURCES and b.station.has_tag:
                        bad.append("(%s) is measured with a tag in the stack" % " / ".join(c.key))
                    if c.is_calibration:
                        seen_cal.add(c.pair)
                    elif c.pair not in seen_cal:
                        bad.append("(%s) is measured BEFORE its calibration row" % " / ".join(c.key))
        return bad


# ------------------------------------------------------------------ stage 1: cells

def licensing_source(p: reg.Protocol, bench: Bench) -> str | None:
    """The gold source that can license this protocol on this bench, or None.

    ⭐ ONLY A PROXMARK-WRITTEN TAG OR A GENUINE CARD. A T5577 written by the Chameleon is a real tag
    too, but it carries a credential produced by the very writer under test — licensing a reader
    with it would let a device vouch for itself one step removed.
    """
    if p.t55_capable and bench.available(T5577):
        return "t55.pm3"
    return "oem" if p.key in bench.has_oem else None


def _refuse(p: reg.Protocol, source: str, reader: str, bench: Bench) -> Exclusion | None:
    """Every reason a cell must not be planned."""
    emitter, writer = SOURCES[source]
    rd = READERS[reader]

    if p.subcarrier and source in EMULATED_SOURCES and rd in ("cu1", "cu2"):
        return Exclusion(p.key, source, reader, "subcarrier",
                         "subcarrier-dependent (RULES.md §2): this family needs a subcarrier "
                         "phase-locked to the reader's carrier, which only a real tag has. A read "
                         "arm tested against an emulation measures the bench, not the arm.")
    if rd in ("cu1", "cu2") and p.cu_read is None:
        return Exclusion(p.key, source, reader, "no-read-arm",
                         "no Chameleon read command is registered for %s." % p.key)
    if rd in ("cu1", "cu2") and p.cu_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "the Chameleon renders %s in its own wording and what a pass looks like "
                         "has never been observed. The Proxmark's expectation is not "
                         "interchangeable — comparing one client's output against another's "
                         "reports a working decoder as silent. Learn it from a real tag first."
                         % p.key)
    try:
        devices_to_measure(source, reader)
    except StationError as e:
        return Exclusion(p.key, source, reader, "self-judging", str(e))

    for dev in devices_to_produce(source, reader):
        if not bench.available(dev):
            return Exclusion(p.key, source, reader, "no-device",
                             "this bench does not have %s." % HUMAN[dev])
    if reader == "rd.flip" and p.flip_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "the Flipper's decoded hex for %s has never been observed, so there is no "
                         "byte-exact token to compare against. Matching on the protocol name alone "
                         "breaks the name-match rule (RULES.md §6). Run `bench learn -p %s`."
                         % (p.key, p.key))
    if source == "emu.flip" and p.flip_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "`rfid emulate` needs the Flipper's own hex for %s, which is unknown."
                         % p.key)
    if source == "t55.flip" and not p.flip_write:
        return Exclusion(p.key, source, reader, "gap:flipper-write",
                         "the Flipper cannot write %s to a T5577 that the Proxmark writes fine "
                         "(a registered gap). This source does not exist for this protocol." % p.key)
    if source == "t55.flip" and p.flip_expect is None:
        return Exclusion(p.key, source, reader, "no-expectation",
                         "`rfid write` needs the Flipper's own hex for %s, which is unknown." % p.key)
    if writer in ("cu1", "cu2") and p.cu_write is None:
        return Exclusion(p.key, source, reader, "no-write-arm",
                         "no Chameleon write command is registered for %s." % p.key)
    if source == "oem" and p.key not in bench.has_oem:
        return Exclusion(p.key, source, reader, "no-card",
                         "no genuine %s credential is owned on this bench." % p.key)
    return None


def _cells(protocols, sources, readers, bench) -> tuple[list[PlannedCell], list[Exclusion]]:
    wanted: dict[tuple[str, str, str], PlannedCell] = {}
    exclusions: list[Exclusion] = []

    def consider(p, source, reader, is_cal) -> bool:
        why = _refuse(p, source, reader, bench)
        if why is not None:
            exclusions.append(why)
            return False
        cell = PlannedCell(p, source, reader, is_cal)
        prev = wanted.get(cell.key)
        if prev is None or (is_cal and not prev.is_calibration):
            wanted[cell.key] = cell
        return True

    for p in protocols:
        for reader in readers:
            lic = licensing_source(p, bench)
            requested = [s for s in sources if s != lic]
            if lic is None:
                exclusions.append(Exclusion(
                    p.key, "-", reader, "unlicensable",
                    "%s cannot be held by a T5577 and no genuine card is owned, so nothing can "
                    "license %s for it." % (p.key, reader)))
                continue
            if not consider(p, lic, reader, True):
                for src in requested:
                    own = _refuse(p, src, reader, bench)
                    exclusions.append(own or Exclusion(
                        p.key, src, reader, "no-calibration",
                        "the licensing row (%s, %s) is itself refused, so this cell could only ever "
                        "be UNGRADED." % (lic, reader)))
                continue
            for src in requested:
                consider(p, src, reader, False)
    return list(wanted.values()), exclusions


# ------------------------------------------------------------------ stage 2: stations

def _covered(devices: frozenset[str], cells) -> list[PlannedCell]:
    st = Station(tuple(d for d in STACK_ORDER if d in devices))
    return [c for c in cells if station_admits(st, c.source, c.reader)]


def choose_stations(cells: list[PlannedCell], bench: Bench) -> list[Station]:
    """Greedy set cover: the fewest arrangements that measure every cell.

    ⭐ THE SEED IS A CELL'S OWN REQUIREMENT AND THE GROWTH IS GREEDY. Starting from what one cell
    needs and adding whichever device brings in the most other cells produces the Proxmark-tag-
    Chameleon stack on its own, because that is genuinely where the coverage is: four cells per
    protocol, against one for an isolated pair.

    ⚠ IT OPTIMISES INTERVENTIONS, NOT CROWDING. A bigger stack covers more and tells you less, and
    that trade is deliberate — the crowded-stack rule means the cost of over-stacking is paid only
    on the cells that fail, in the isolation phase, and never in a wrong verdict.
    """
    uncovered = list(cells)
    chosen: list[Station] = []
    while uncovered:
        seeds = {devices_to_produce(c.source, c.reader) for c in uncovered}
        best, best_hits = None, -1
        for seed in seeds:
            if len(seed) > bench.max_stack or not seed <= bench.devices:
                continue
            cand = set(seed)
            while len(cand) < bench.max_stack:
                gain = None
                for dev in bench.devices - cand:
                    trial = frozenset(cand | {dev})
                    if len(trial) > bench.max_stack or len(trial & TAGS) > 1:
                        continue
                    hits = len(_covered(trial, uncovered))
                    if gain is None or hits > gain[0]:
                        gain = (hits, dev)
                if gain is None or gain[0] <= len(_covered(frozenset(cand), uncovered)):
                    break
                cand.add(gain[1])
            hits = len(_covered(frozenset(cand), uncovered))
            # Prefer more coverage; break ties toward the SMALLER stack, which is less crowded and
            # therefore yields more cells that are verdicts rather than screening results.
            if hits > best_hits or (hits == best_hits and best is not None and len(cand) < len(best)):
                best, best_hits = frozenset(cand), hits
        if best is None or best_hits == 0:
            # ⚠ A KNOWN LIMIT, NOT A MYSTERY. Phase 1 covers each cell with ONE station, so a tag
            # cell needs its writer and its reader in the same stack. Where they will not fit, the
            # measurement is still possible — write at one station, carry the tag, read at the next,
            # which is exactly what the isolation phase does — but the set-cover planner does not
            # build that split, because in phase 1 it would trade a great many interventions for
            # coverage that a bigger stack gives for free.
            need = sorted({" / ".join(c.key) for c in uncovered})
            raise AssertionError(
                "%d cell(s) need more devices in one stack than --max-stack=%d allows:\n    %s\n"
                "  Each needs %s together. Raise --max-stack if they physically stack, or drop the "
                "source or reader that does not fit."
                % (len(uncovered), bench.max_stack, "\n    ".join(need),
                   ", ".join(sorted(devices_to_produce(uncovered[0].source, uncovered[0].reader)))))
        station = build_station(best, bench)
        chosen.append(station)
        done = {id(c) for c in _covered(best, uncovered)}
        uncovered = [c for c in uncovered if id(c) not in done]
    return chosen


def order_stations(stations: list[Station], cells: list[PlannedCell]) -> list[Station]:
    """Gold stations first, then the rest, each chain ordered by cheapest next move.

    ⛔ GOLD FIRST IS A CORRECTNESS CONSTRAINT, NOT A PREFERENCE. Only a station holding the Proxmark
    and a tag can produce the calibration rows, and a cell measured before its licence cannot be
    licensed by it — `audit()` refuses a plan where that happened.
    """
    def calibrates(st: Station) -> int:
        return sum(1 for c in cells
                   if c.is_calibration and station_admits(st, c.source, c.reader))

    gold = [s for s in stations if calibrates(s)]
    rest = [s for s in stations if not calibrates(s)]
    out, prev = [], None
    for group in (sorted(gold, key=lambda s: -calibrates(s)), rest):
        pool = list(group)
        while pool:
            nxt = min(pool, key=lambda s: (move_cost(prev, s), s.name))
            pool.remove(nxt)
            out.append(nxt)
            prev = nxt
    return out


# ------------------------------------------------------------------ stage 3: routines

def _routine(station: Station, cells: list[PlannedCell]) -> list[Op]:
    """The op sequence for one station. This is where the hands-off cycle is generated."""
    mine = [c for c in cells if station_admits(station, c.source, c.reader)]
    ops: list[Op] = []
    protocols, seen = [], set()
    for c in sorted(mine, key=lambda c: _rank(c.protocol.key)):
        if c.protocol.key not in seen:
            seen.add(c.protocol.key)
            protocols.append(c.protocol)

    def reads_for(p, source):
        """⛔ THE WRITER READS BACK FIRST. A T5577 does not acknowledge a write, so the writer's own
        read is the only evidence the credential is on the tag at all — and if it is not, every
        other read taken after that write is about a tag holding something else. Ordering it first
        lets the runner skip the rest of the write rather than file them as the reader's failures."""
        writer = SOURCES[source][1]
        return sorted((c for c in mine if c.protocol.key == p.key and c.source == source),
                      key=lambda c: (READERS[c.reader] != writer, not c.is_calibration, c.reader))

    for p in protocols:
        if station.has_tag:
            # ⭐ THE CYCLE: write with each writer in turn, and after each write let every reader in
            # the stack judge it. The Proxmark writes first so its row — the gold calibration —
            # exists before anything else at this station is graded.
            for writer in WRITER_ORDER:
                source = WRITER_SOURCE[writer]
                todo = reads_for(p, source)
                if not todo or writer not in station.devices:
                    continue
                ops.append(Op("write", writer, p))
                ops += _verify_ops(p, writer, station, todo)
                for c in todo:
                    ops.append(Op("read", READERS[c.reader], p, c,
                                  station.crowding(devices_to_measure(c.source, c.reader))))
            todo = reads_for(p, "oem")
            if todo:
                ops.append(Op("place", "operator", p))
                for c in todo:
                    ops.append(Op("read", READERS[c.reader], p, c,
                                  station.crowding(devices_to_measure(c.source, c.reader))))
        else:
            for source in ("emu.flip", "emu.cu1", "emu.cu2"):
                todo = reads_for(p, source)
                if not todo:
                    continue
                dev = SOURCES[source][0]
                ops.append(Op("arm", dev, p))
                for c in todo:
                    ops.append(Op("read", READERS[c.reader], p, c,
                                  station.crowding(devices_to_measure(c.source, c.reader))))
                ops.append(Op("disarm", dev, p))
    return ops


def _verify_ops(p: reg.Protocol, writer: str, station: Station, wanted: list, tag: int = 0) -> list:
    """A read-back by the writer, unless one of the wanted cells already is one.

    ⛔⛔ A WRITE IS NOT DONE BECAUSE IT RETURNED (RULES.md §10). A T5577 does not acknowledge a
    write, so the client's "Done!" says the commands went out and nothing more. If the only reader
    that then looks at the tag happens to be one that cannot decode this protocol, its silence is
    ambiguous — and the harness would have to call it either a write failure or a reader gap without
    being able to tell. One extra read by the writer, at the station that is already set up, removes
    the ambiguity for every reader that follows.
    """
    if writer not in READERS.values() or writer not in station.devices:
        return []
    if any(READERS[c.reader] == writer for c in wanted):
        return []                                   # a wanted cell already witnesses it
    if writer in ("cu1", "cu2") and p.cu_read is None:
        return []
    if writer == "flipper" and p.flip_expect is None:
        return []
    return [Op("verify", writer, p, tag=tag)]


def _rank(key: str) -> int:
    return reg.TIER0_ORDER.index(key) if key in reg.TIER0_ORDER else len(reg.TIER0_ORDER)


# ------------------------------------------------------------------ the entry point

def build(protocols: list[reg.Protocol], sources: list[str], readers: list[str],
          bench: Bench, phase: int = 1) -> RunPlan:
    for s in sources:
        if s not in SOURCES:
            raise ValueError("unknown source %r (known: %s)" % (s, ", ".join(SOURCES)))
    for r in readers:
        if r not in READERS:
            raise ValueError("unknown reader %r (known: %s)" % (r, ", ".join(READERS)))

    cells, exclusions = _cells(protocols, sources, readers, bench)
    blocks: list[Block] = []
    if cells:
        for station in order_stations(choose_stations(cells, bench), cells):
            blocks.append(Block(station, _routine(station, cells)))
    plan = RunPlan(bench=bench, blocks=_coalesce(blocks), exclusions=exclusions, phase=phase)
    bad = plan.audit()
    if bad:
        raise AssertionError("plan.build produced an ungradeable plan:\n  " + "\n  ".join(bad))
    return plan


# ------------------------------------------------------------------ phase 2: isolation

def isolate(screened: list, bench: Bench) -> RunPlan:
    """Build the minimal-stack plan that turns screening results into verdicts (RULES.md §7).

    ⭐ THIS IS THE ONLY PLACE A `SILENT` OR `WRONG` MAY BE PRODUCED for a cell that was first seen
    in a crowded stack. Phase 1 buys coverage by stacking; phase 2 pays for it, but only on the
    cells that actually failed, and never in a wrong verdict.

    ⚠ ISOLATING A TAG CELL TAKES TWO STATIONS, NOT ONE. The writer is exactly the device whose
    presence made the reading crowded, so it cannot be in the stack when the reading is retaken:
    write at (writer + tag), carry the tag to (tag + reader), read there. With one tag that is two
    interventions per protocol; with `bench.tag_count` tags a whole batch is written at the first
    station and read at the second, which is the one case where swapping tags is cheaper than
    rearranging the bench.
    """
    # ⛔ CALIBRATION ROWS FIRST, exactly as in phase 1. A screened gold row leaves its whole
    # (protocol, reader) pair unlicensed, so re-measuring a dependent cell before it would produce
    # another UNGRADED and a third phase.
    screened = sorted(screened, key=lambda c: (c.source not in GOLD_SOURCES, _rank(c.protocol)))

    by_writer: dict[str | None, list] = {}
    for cell in screened:
        by_writer.setdefault(SOURCES[cell.source][1], []).append(cell)

    blocks: list[Block] = []
    batch_size = max(1, bench.tag_count)

    def writer_rank(kv):
        # ⛔ THE GOLD WRITER GOES FIRST. Grouping by writer alone re-sorts alphabetically and puts
        # `cu1` before `pm3`, which would re-measure a dependent cell before the calibration row it
        # needs — the very thing the phase-1 ordering exists to prevent.
        writer, cells = kv
        return (not any(c.source in GOLD_SOURCES for c in cells), str(writer))

    for writer, group in sorted(by_writer.items(), key=writer_rank):
        if writer is None:
            # An emulated source: the emitter must be present, so the minimal stack IS the pair.
            for (source, reader), cells in sorted(_by_route(group).items()):
                emitter, rd_dev = SOURCES[source][0], READERS[reader]
                ops = []
                for p in _protocols(cells):
                    ops += [Op("arm", emitter, p),
                            Op("read", rd_dev, p, _cell(p, source, reader)),
                            Op("disarm", emitter, p)]
                blocks.append(Block(build_station({emitter, rd_dev}, bench), ops))
            continue

        # ⭐ ONE TRIP TO THE WRITER PER BATCH, THEN ONE TRIP PER READER. The writer's own re-reads
        # ride along at the write station, because there the writer is not crowding anything — it is
        # the reader. Everyone else's re-reads happen at a stack holding only the tag and them.
        routes = _by_route(group)
        protos = _protocols(group)
        write_station = build_station({writer, T5577}, bench)
        for i in range(0, len(protos), batch_size):
            batch = protos[i:i + batch_size]
            here = []
            for n, p in enumerate(batch):
                here.append(Op("write", writer, p, tag=n))
                wanted_here = [c for (src, rdr), cs in routes.items() for c in cs
                               if c.protocol == p.key and READERS[rdr] == writer]
                here += _verify_ops(p, writer, write_station, wanted_here, tag=n)
            for (source, reader), cells in sorted(routes.items()):
                if READERS[reader] != writer:
                    continue
                keys = {c.protocol for c in cells}
                for n, p in enumerate(batch):
                    if p.key in keys:
                        here.append(Op("read", writer, p, _cell(p, source, reader), tag=n))
            blocks.append(Block(write_station, here))
            for (source, reader), cells in sorted(routes.items()):
                rd_dev = READERS[reader]
                if rd_dev == writer:
                    continue
                keys = {c.protocol for c in cells}
                ops = [Op("read", rd_dev, p, _cell(p, source, reader), tag=n)
                       for n, p in enumerate(batch) if p.key in keys]
                if ops:
                    blocks.append(Block(build_station({T5577, rd_dev}, bench), ops))
    return RunPlan(bench=bench, blocks=_coalesce(blocks), exclusions=[], phase=2)


def _coalesce(blocks: list) -> list:
    """Merge consecutive blocks that share a station — one arrangement, one intervention.

    ⚠ ONLY CONSECUTIVE ONES. Re-ordering non-adjacent blocks to bring two visits together would
    move reads across the writes that set the tag up for them.
    """
    out: list[Block] = []
    for b in blocks:
        if out and out[-1].station == b.station:
            out[-1].ops.extend(b.ops)
        else:
            out.append(Block(b.station, list(b.ops)))
    return out


def _by_route(cells) -> dict:
    out: dict[tuple[str, str], list] = {}
    for c in cells:
        out.setdefault((c.source, c.reader), []).append(c)
    return out


def _protocols(cells) -> list:
    seen, out = set(), []
    for c in sorted(cells, key=lambda c: _rank(c.protocol)):
        if c.protocol not in seen and c.protocol in reg.TIER0:
            seen.add(c.protocol)
            out.append(reg.TIER0[c.protocol])
    return out


def _cell(p: reg.Protocol, source: str, reader: str) -> PlannedCell:
    """⛔ A GOLD-SOURCE CELL IS THE CALIBRATION ROW FOR ITS PAIR, in phase 2 as much as in phase 1.
    Rebuilding it as an ordinary cell would leave it looking for a licence it is itself supposed to
    issue, and every cell in the pair would come back UNGRADED from a run that measured them all."""
    return PlannedCell(p, source, reader, is_calibration=source in GOLD_SOURCES)
