"""Devices, sources, readers, and the stations a run is executed at.

⭐⭐ THE UNIT OF WORK IS A STATION, NOT A MOVE. A station is a physical arrangement the operator
sets up **once**; everything that can be measured in it is then measured with no further
involvement. That is the only cost model that matches reality — the scarce resource is the
operator's hands, and a tag swap costs exactly as much as rearranging the bench.

The consequence is the whole reason this file replaced a one-reader-one-pad model. At a station of

    Proxmark ─ T5577 ─ Chameleon 1

one routine covers, for every protocol: the Proxmark writing and reading back, the Chameleon
reading what the Proxmark wrote, the Chameleon writing, and the Proxmark reading that. Four cells a
protocol, sixty-four cells, **one** intervention. The same work as a sequence of two-device
arrangements costs thirty-two.

⛔ AND THE PRICE IS THE CROWDED-STACK RULE (RULES.md §7). Devices left in the stack detune and load
the active coil even when idle, so a station tells you less than an isolated pair does. A byte-exact
decode of the armed credential cannot be manufactured by a parasitic coil, so a success is a
success — but a silence or a wrong decode might be the crowding, and is therefore not a verdict.
`plan.py` turns those into an isolation queue rather than into cells.
"""

from __future__ import annotations

from dataclasses import dataclass

# ------------------------------------------------------------------ devices (physical things)
PM3 = "pm3"
FLIPPER = "flipper"
CU1 = "cu1"
CU2 = "cu2"
T5577 = "t5577"
OEMTAG = "oemtag"

#: Passive things: they answer any field they are in and have no idle state.
TAGS = frozenset({T5577, OEMTAG})

HUMAN = {
    PM3: "the Proxmark",
    FLIPPER: "the Flipper",
    CU1: "Chameleon 1",
    CU2: "Chameleon 2",
    T5577: "the T5577 tag",
    OEMTAG: "the OEM card",
}
#: What `say` should pronounce. The printed text can carry digits the voice should not.
SPOKEN = dict(HUMAN, cu1="Chameleon one", cu2="Chameleon two")

#: Bottom to top. The Proxmark is the bench anchor, a tag sits in the middle, the rest go on top.
STACK_ORDER = (PM3, FLIPPER, T5577, OEMTAG, CU1, CU2)

SHORT = {PM3: "PM3", FLIPPER: "FLIP", CU1: "CU1", CU2: "CU2", T5577: "T55", OEMTAG: "OEM"}


# ------------------------------------------------------------------ sources and readers
#: source id -> (what emits, who had to write it). A writer of None means nothing writes it —
#: an emulator arms itself, and an OEM card was written by its manufacturer.
SOURCES: dict[str, tuple[str, str | None]] = {
    "t55.pm3":  (T5577, PM3),
    "t55.flip": (T5577, FLIPPER),
    "t55.cu1":  (T5577, CU1),
    "t55.cu2":  (T5577, CU2),
    "emu.flip": (FLIPPER, None),
    "emu.cu1":  (CU1, None),
    "emu.cu2":  (CU2, None),
    "oem":      (OEMTAG, None),
}

SOURCE_NOTE = {
    "t55.pm3":  "real T5577, written by the Proxmark — the gold reference",
    "t55.flip": "real T5577, written by the Flipper",
    "t55.cu1":  "real T5577, written by Chameleon 1 — tests our writer",
    "t55.cu2":  "real T5577, written by Chameleon 2 — tests our writer",
    "emu.flip": "Flipper emulating — an independent second opinion on our own emulator",
    "emu.cu1":  "Chameleon 1 emulating",
    "emu.cu2":  "Chameleon 2 emulating",
    "oem":      "a genuine OEM credential",
}

#: ⛔ The only sources that can license a reader (RULES.md §1). An emulation never licenses
#: anything, including itself.
REAL_SOURCES = frozenset({"t55.pm3", "t55.flip", "t55.cu1", "t55.cu2", "oem"})

#: ⭐ ...but only the Proxmark-written tag and a genuine card are *gold*. A tag written by the
#: device under test is a real tag carrying a credential we are not yet entitled to trust, so it
#: cannot license the reader that is about to judge its own writer.
GOLD_SOURCES = frozenset({"t55.pm3", "oem"})

#: Sources that are a device emulating. The subcarrier rule refuses these against a Chameleon.
EMULATED_SOURCES = frozenset({"emu.flip", "emu.cu1", "emu.cu2"})

#: Sources that are a physical tag in the stack.
TAG_SOURCES = frozenset(s for s, (dev, _) in SOURCES.items() if dev in TAGS)

READERS: dict[str, str] = {
    "rd.pm3":  PM3,
    "rd.flip": FLIPPER,
    "rd.cu1":  CU1,
    "rd.cu2":  CU2,
}

READER_NOTE = {
    "rd.pm3":  "Proxmark3 — `lf <proto> reader`",
    "rd.flip": "Flipper — `rfid read`",
    "rd.cu1":  "Chameleon 1 reader mode — one of the arms under test",
    "rd.cu2":  "Chameleon 2 reader mode — one of the arms under test",
}


class StationError(Exception):
    pass


# ------------------------------------------------------------------ the bench

@dataclass(frozen=True)
class Bench:
    """What this bench physically has, and how much can be stacked at once."""

    has: frozenset[str] = frozenset({PM3, FLIPPER, CU1, CU2, T5577})
    #: ⚠ HOW MANY DEVICES WILL PHYSICALLY STACK. Three is a Proxmark, a tag and one more on top.
    #: Raising it buys coverage per intervention and costs crowding; it is a bench fact, not a
    #: preference, so it is measured once and set here rather than guessed per run.
    max_stack: int = 3
    has_oem: frozenset[str] = frozenset()      # protocol keys a genuine card is owned for
    pad: str = "pad0"
    #: Tags available for the isolation phase. One is enough; more makes phase 2 cheaper.
    tag_count: int = 1

    @property
    def devices(self) -> frozenset[str]:
        """Everything this bench can put in a stack, the OEM card included when one is owned."""
        return self.has | (frozenset({OEMTAG}) if self.has_oem else frozenset())

    def available(self, dev: str) -> bool:
        # ⚠ AN OEM CARD IS A DEVICE THE BENCH HAS ONLY IF ONE IS OWNED for some protocol. Listing it
        # in `has` as well would be two places to keep in step, and `has_oem` is the one the planner
        # already consults per protocol.
        if dev == OEMTAG:
            return bool(self.has_oem)
        return dev in self.has


# ------------------------------------------------------------------ stations

@dataclass(frozen=True)
class Station:
    """One physical arrangement: an ordered stack of devices, bottom to top."""

    stack: tuple[str, ...]

    @property
    def name(self) -> str:
        return "+".join(SHORT[d] for d in self.stack)

    @property
    def devices(self) -> frozenset[str]:
        return frozenset(self.stack)

    @property
    def has_tag(self) -> bool:
        return bool(self.devices & TAGS)

    @property
    def tags(self) -> frozenset[str]:
        return self.devices & TAGS

    def describe(self) -> str:
        return " ─ ".join(HUMAN[d] for d in self.stack)

    def readers(self) -> list[str]:
        return [r for r, dev in READERS.items() if dev in self.devices]

    def crowding(self, needed: frozenset[str]) -> frozenset[str]:
        """Devices present but not required by the operation — the crowded-stack rule's trigger."""
        return self.devices - needed


def build_station(devices, bench: Bench | None = None) -> Station:
    """Order a set of devices into a physical stack."""
    devs = frozenset(devices)
    unknown = devs - set(STACK_ORDER)
    if unknown:
        raise StationError("unknown device(s): %s" % ", ".join(sorted(unknown)))
    if bench is not None and not devs <= bench.devices:
        raise StationError("this bench does not have: %s"
                           % ", ".join(sorted(devs - bench.devices)))
    if len(devs & TAGS) > 1:
        raise StationError("a stack may hold at most one tag; both %s answer any field they are in"
                           % " and ".join(HUMAN[d] for d in sorted(devs & TAGS)))
    return Station(tuple(d for d in STACK_ORDER if d in devs))


# ------------------------------------------------------------------ what a cell needs

def devices_to_measure(source: str, reader: str) -> frozenset[str]:
    """What must be in the stack AT READ TIME: the thing emitting, and the thing judging.

    ⚠ NOT THE WRITER. A tag written by the Proxmark keeps its credential when the Proxmark is taken
    away, so the Proxmark is not part of the measurement — which is precisely why it counts as
    crowding when it is left in the stack, and why isolating a failure is possible at all.
    """
    if source not in SOURCES:
        raise StationError("unknown source %r" % source)
    if reader not in READERS:
        raise StationError("unknown reader %r" % reader)
    emitter, _ = SOURCES[source]
    rd = READERS[reader]
    if emitter == rd:
        raise StationError(
            "(%s, %s) puts %s on its own antenna. A device cannot be both the instrument and the "
            "thing being measured." % (source, reader, HUMAN[rd]))
    return frozenset({emitter, rd})


def devices_to_produce(source: str, reader: str) -> frozenset[str]:
    """Everything the station needs, including the writer that has to put the credential there."""
    need = set(devices_to_measure(source, reader))
    _, writer = SOURCES[source]
    if writer is not None:
        need.add(writer)
    return frozenset(need)


def station_admits(station: Station, source: str, reader: str) -> bool:
    """Can this cell be measured at this station?

    ⛔ A TAG AND AN EMULATION NEVER SHARE A STATION. If the tag holds protocol P and a device
    emulates P, a reader that decodes P cannot say which produced it — the self-judging failure in
    a new dress. So a tag station measures tag sources and an emulation station measures emulated
    ones, and the two sets of stations are disjoint by construction rather than by care.
    """
    if not devices_to_produce(source, reader) <= station.devices:
        return False
    # ⛔ ONE PASSIVE EMITTER AT MOST. Two tags in a stack both answer the field, so a decode cannot
    # say which of them it came from — the same ambiguity as mixing a tag with an emulation.
    if len(station.tags) > 1:
        return False
    return station.has_tag == (source in TAG_SOURCES)


# ------------------------------------------------------------------ moves between stations

@dataclass(frozen=True)
class Move:
    """One operator instruction: what comes off, what goes on, and the stack it reaches."""

    to: Station
    place: tuple[str, ...] = ()
    remove: tuple[str, ...] = ()
    frm: Station | None = None

    @property
    def is_noop(self) -> bool:
        return not self.place and not self.remove

    def _parts(self, names: dict[str, str]) -> list[str]:
        """Removal first, always — it is the half that gets forgotten, and the half that ruins a
        run by leaving a device in the field that nothing in the plan knows about."""
        bits = []
        if self.remove:
            bits.append("take %s out" % _join(names[d] for d in self.remove))
        if self.place:
            bits.append("add %s" % _join(names[d] for d in self.place))
        return bits

    def text(self) -> str:
        bits = self._parts(HUMAN)
        if not bits:
            return "no change — still %s" % self.to.describe()
        joined = ", then ".join(bits)
        return joined[:1].upper() + joined[1:] + "  ⇒  " + self.to.describe()

    def spoken(self) -> str:
        bits = self._parts(SPOKEN)
        if not bits:
            return "no change"
        return ", then ".join(bits) + ". Stack is " + " on ".join(
            SPOKEN[d] for d in reversed(self.to.stack))


def _join(items) -> str:
    items = list(items)
    if len(items) <= 1:
        return items[0] if items else "nothing"
    return "%s and %s" % (", ".join(items[:-1]), items[-1])


def plan_move(frm: Station | None, to: Station) -> Move:
    """The difference between two stacks, as an instruction. Computed, never written by hand."""
    if frm is None:
        return Move(to=to, place=tuple(to.stack), remove=(), frm=None)
    gone = tuple(d for d in frm.stack if d not in to.devices)
    added = tuple(d for d in to.stack if d not in frm.devices)
    return Move(to=to, place=added, remove=gone, frm=frm)


def move_cost(frm: Station | None, to: Station) -> int:
    """Devices handled. Used to order stations so the operator does the least work."""
    m = plan_move(frm, to)
    return len(m.place) + len(m.remove)


def null_station(of: Station) -> Station:
    """The same stack with every passive tag taken out, for a null sweep.

    ⚠ ACTIVE DEVICES STAY WHERE THEY ARE and go to reader mode; a null taken with the stack pulled
    apart measures a different bench from the one the arms were measured on. A tag has no idle
    state, so it is the one thing that has to physically leave (RULES.md §3).
    """
    return Station(tuple(d for d in of.stack if d not in TAGS))
