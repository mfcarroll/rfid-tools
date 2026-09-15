"""Sources, readers, bench topologies, and the spoken move vocabulary.

⭐ THE RUN PLAN DECLARES TOPOLOGIES, NOT MOVES. A full tier-0 matrix is eleven physical
rearrangements; asking the operator to hold that in their head is how the wrong Chameleon ends up
on the pad. The harness computes the move sequence from the cells it was asked for, orders the
blocks so each topology is visited once, and speaks each transition.

⛔ A CUE NAMES WHAT GOES ON *AND* WHAT COMES OFF. "Put Chameleon 2 on the Proxmark" is not enough —
it does not say that Chameleon 1 and the tag have to leave, and the single most expensive error of
the run so far was the operator and the agent disagreeing about which Chameleon was on the pad. The
cue is generated from the difference between two topologies precisely so it cannot forget the half
that is about removal.
"""

from __future__ import annotations

from dataclasses import dataclass

# ------------------------------------------------------------------ device ids (physical things)
PM3 = "pm3"
FLIPPER = "flipper"
CU1 = "cu1"
CU2 = "cu2"
T5577 = "t5577"
OEMTAG = "oemtag"

HUMAN = {
    PM3: "the Proxmark",
    FLIPPER: "the Flipper",
    CU1: "Chameleon 1",
    CU2: "Chameleon 2",
    T5577: "the T5577 tag",
    OEMTAG: "the OEM card",
}
#: What `say` should pronounce. The terminal text can carry punctuation the voice should not.
SPOKEN = dict(HUMAN, cu1="Chameleon one", cu2="Chameleon two")

# ------------------------------------------------------------------ sources (RULES.md §1)
SOURCES = {
    "t55.pm3":  (T5577,   "real T5577, written by the Proxmark — the gold reference"),
    "t55.flip": (T5577,   "real T5577, written by the Flipper"),
    "emu.flip": (FLIPPER, "Flipper emulating"),
    "emu.cu1":  (CU1,     "Chameleon #1 emulating (v2.2.0-861-g1866718)"),
    "emu.cu2":  (CU2,     "Chameleon #2 emulating (v2.2.0-875-g02fc2e2)"),
    "oem":      (OEMTAG,  "a genuine OEM credential"),
}

#: ⛔ The only sources that can license a reader (RULES.md §1). An emulation never licenses
#: anything, including itself — that is the calibration rule in one line (RULES.md §1).
REAL_SOURCES = frozenset({"t55.pm3", "oem"})

#: Sources that are a Chameleon emulating. The subcarrier rule refuses these against `rd.cu`.
EMULATED_SOURCES = frozenset({"emu.flip", "emu.cu1", "emu.cu2"})

# ------------------------------------------------------------------ readers (RULES.md §1)
READERS = {
    "rd.pm3":  (PM3,     "Proxmark3"),
    "rd.flip": (FLIPPER, "Flipper"),
    "rd.cu":   (None,    "Chameleon reader mode"),   # which Chameleon is bench configuration
}


class TopologyError(Exception):
    pass


@dataclass(frozen=True)
class Topology:
    """One physical arrangement: a reader, and what is sitting on its antenna."""

    name: str
    reader_dev: str
    on_pad: tuple[str, ...] = ()

    @property
    def devices(self) -> frozenset[str]:
        return frozenset((self.reader_dev,) + self.on_pad)

    def describe(self) -> str:
        if not self.on_pad:
            return "%s + nothing" % HUMAN[self.reader_dev]
        return "%s + %s" % (HUMAN[self.reader_dev], " + ".join(HUMAN[d] for d in self.on_pad))


@dataclass(frozen=True)
class Bench:
    """Which physical devices this bench has, and which Chameleon is the designated reader.

    ⚠ `cu_reader` MATTERS AND IS NOT COSMETIC. `rd.cu` grades an arm on one Chameleon while the
    other may be the source; the two builds differ, and which was which has had to be established BY
    RADIO after a verbal mix-up. Name it here, and let `identity.py` prove it (RULES.md §4).
    """

    cu_reader: str = CU1
    has_oem: frozenset[str] = frozenset()       # protocol keys an OEM card is owned for
    has_cu2: bool = True
    has_flipper: bool = True
    pad: str = "pm3-antenna"                    # free text, stamped into every licence

    def __post_init__(self) -> None:
        if self.cu_reader not in (CU1, CU2):
            raise TopologyError("cu_reader must be %r or %r" % (CU1, CU2))

    @property
    def cu_other(self) -> str:
        return CU2 if self.cu_reader == CU1 else CU1


def _name(reader_dev: str, on_pad: tuple[str, ...]) -> str:
    """PM3_CU2, FLIP_T55, CU1_CU2 — the spellings RULES.md §3 uses."""
    short = {PM3: "PM3", FLIPPER: "FLIP", CU1: "CU1", CU2: "CU2", T5577: "T55", OEMTAG: "OEM"}
    tail = "_".join(short[d] for d in on_pad) if on_pad else "ALONE"
    return "%s_%s" % (short[reader_dev], tail)


def topology_for(source: str, reader: str, bench: Bench) -> Topology:
    """The arrangement a (source, reader) cell has to be measured in."""
    if source not in SOURCES:
        raise TopologyError("unknown source %r" % source)
    if reader not in READERS:
        raise TopologyError("unknown reader %r" % reader)
    src_dev = SOURCES[source][0]
    rd_dev = READERS[reader][0] or bench.cu_reader
    if src_dev == rd_dev:
        raise TopologyError(
            "(%s, %s) puts %s on its own antenna. A device cannot be both the instrument and the "
            "thing being measured — that is the shape of all three failures in README.md."
            % (source, reader, HUMAN[rd_dev]))
    return Topology(_name(rd_dev, (src_dev,)), rd_dev, (src_dev,))


def null_topology(of: Topology) -> Topology:
    """The same arrangement with nothing emitting.

    ⚠ THE DEVICES STAY WHERE THEY ARE. pm3grade.sh's null sweep leaves the Chameleon physically on
    the pad and puts it in READER mode, and that is the right control: a null taken with the pad
    cleared measures a different bench from the one the arms were measured on. Only a passive tag,
    which has no idle state, is physically removed.
    """
    passive = (T5577, OEMTAG)
    stays = tuple(d for d in of.on_pad if d not in passive)
    return Topology(_name(of.reader_dev, stays) + "_NULL", of.reader_dev, stays)


# ------------------------------------------------------------------ moves

@dataclass(frozen=True)
class Move:
    """One operator instruction: what to place, what to take away, and the topology it reaches."""

    to: Topology
    place: tuple[str, ...] = ()
    remove: tuple[str, ...] = ()
    frm: Topology | None = None
    reader_changed: bool = False

    @property
    def is_noop(self) -> bool:
        return not self.place and not self.remove and not self.reader_changed

    def _parts(self, names: dict[str, str]) -> list[str]:
        """Removal first, always. It is the half that gets forgotten."""
        bits = []
        if self.reader_changed:
            # ⛔ A READER CHANGE CLEARS THE OLD PAD EVEN FOR A DEVICE THE NEXT TOPOLOGY ALSO USES.
            # PM3_CU2 -> CU1_CU2 keeps Chameleon 2 in the run but it still has to come off the
            # Proxmark first, and a set difference alone says "no change" — which would leave the
            # operator with a Chameleon on the wrong pad and a grid that looks fine.
            if self.remove:
                bits.append("clear %s — take %s off it"
                            % (names[self.frm.reader_dev], _join(names[d] for d in self.remove)))
            bits.append("move to %s" % names[self.to.reader_dev])
            if self.place:
                bits.append("put %s on it" % _join(names[d] for d in self.place))
            return bits
        if self.remove:
            bits.append("take %s off" % _join(names[d] for d in self.remove))
        if self.place:
            bits.append("put %s on %s" % (_join(names[d] for d in self.place),
                                          names[self.to.reader_dev]))
        return bits

    def text(self) -> str:
        bits = self._parts(HUMAN)
        if not bits:
            return "no change — still %s" % self.to.describe()
        joined = ", then ".join(bits)
        return joined[:1].upper() + joined[1:] + "  ⇒  " + self.to.describe()

    def spoken(self) -> str:
        """What `say` pronounces. Same order, names the voice can pronounce."""
        bits = self._parts(SPOKEN)
        return ", then ".join(bits) if bits else "no change"


def _join(items) -> str:
    items = list(items)
    if len(items) <= 1:
        return items[0] if items else "nothing"
    return "%s and %s" % (", ".join(items[:-1]), items[-1])


def plan_move(frm: Topology | None, to: Topology) -> Move:
    """The difference between two arrangements, as an instruction.

    ⛔ COMPUTED, NEVER WRITTEN BY HAND. A hand-written cue says what to add and forgets what to take
    away; a set difference cannot. The one case a set difference gets wrong is a READER change, and
    it gets it wrong in the dangerous direction — see `Move._parts`.
    """
    if frm is None:
        return Move(to=to, place=tuple(to.on_pad), remove=(), frm=None)
    if frm.reader_dev != to.reader_dev:
        return Move(to=to, place=tuple(to.on_pad), remove=tuple(frm.on_pad), frm=frm,
                    reader_changed=True)
    gone = tuple(d for d in frm.on_pad if d not in to.on_pad)
    added = tuple(d for d in to.on_pad if d not in frm.on_pad)
    return Move(to=to, place=added, remove=gone, frm=frm)


def order_topologies(needed: list[Topology]) -> list[Topology]:
    """Visit each arrangement exactly once, grouped by reader, cheapest moves first.

    ⚠ ONE VISIT PER TOPOLOGY IS THE WHOLE SAVING. Ordering cells by protocol would revisit
    PM3_CU2 sixteen times; ordering by topology makes it eleven moves for the entire matrix. The
    secondary sort keeps a reader's blocks adjacent, so the operator finishes at one bench position
    before walking to the next.
    """
    seen: dict[str, Topology] = {}
    for t in needed:
        seen.setdefault(t.name, t)
    reader_first = [PM3, FLIPPER, CU1, CU2]
    pad_rank = {T5577: 0, OEMTAG: 1, FLIPPER: 2, CU1: 3, CU2: 4}
    return sorted(seen.values(), key=lambda t: (reader_first.index(t.reader_dev),
                                                tuple(pad_rank.get(d, 9) for d in t.on_pad),
                                                t.name))
