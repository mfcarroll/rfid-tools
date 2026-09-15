"""Radio-identity check and null sweeps — the two controls that bracket every block.

⛔⛔ EVERY MOVE IS FOLLOWED BY A CHECK, NOT A QUESTION (DESIGN.md §3). The operator's word is the
PLAN; the radio is the RECORD. C472 had to establish which Chameleon was on the pad by arming
distinct EM410X ids after a verbal mix-up, and the operator asked for exactly this afterwards:
"that's why I'm confirming the exact setup each time."

⛔ AND IT IS THE ONE CHECK THE NULL ARMS CANNOT DO FOR YOU. A null sweep catches a STRAY emitter;
it cannot catch a SWAPPED one, because the wrong Chameleon is just as silent as the right one when
both are in reader mode. That is the C461 trap, and a wrong-device run produces an unfalsifiable
null — every arm scored against a device that was never listening.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import registry as reg
from .devices import DeviceError
from .outcomes import _strip_ansi
from .topology import CU1, CU2, HUMAN, Topology

#: Device-unique probe ids. Distinct in every nibble so a partial decode still names one device,
#: and deliberately not near any credential in the registry.
PROBE_ID = {CU1: "C1C1C1C1C1", CU2: "C2C2C2C2C2"}

#: EM410X is the probe protocol: it is the one arm every reader in the matrix decodes, and the one
#: the Chameleon is known to emit to both the pm3 (C466) and the Flipper.
PROBE_PROTOCOL = "em410x"


class IdentityFault(Exception):
    """The bench is not what the plan says it is. Never recoverable by retrying the read."""


@dataclass(frozen=True)
class IdentityResult:
    expected: str
    found: str | None
    strays: tuple[str, ...]
    text: str

    @property
    def ok(self) -> bool:
        return self.found == self.expected and not self.strays


#: ⛔ THE PROBE IS NOT THE `em410x` ARM. It borrows EM410X's read command because that is the one
#: protocol every reader in the matrix is known to decode from a Chameleon (C466), but it carries
#: its own key so that a probe read can never be filed as an `em410x` result and an `em410x` script
#: can never intercept a probe. Two different questions that happen to use the same command.
PROBE_KEY = "__probe__"


def probe_protocol(device: str, protocols: dict[str, reg.Protocol] = reg.TIER0) -> reg.Protocol:
    """The EM410X read command, armed with `device`'s unique id, under a key of its own."""
    base = protocols[PROBE_PROTOCOL]
    return reg.Protocol(**{**base.__dict__,
                           "key": PROBE_KEY,
                           "expect": PROBE_ID[device],
                           "cu_emulate": "lf em 410x econfig -s {slot} --id %s"
                                         % PROBE_ID[device].lower()})


def check(topology: Topology, reader, chameleons: dict[str, object],
          protocols: dict[str, reg.Protocol] = reg.TIER0) -> IdentityResult:
    """Arm each Chameleon with its own id, ask the reader who is actually on the pad.

    ⚠ BOTH CHAMELEONS ARE ARMED, NOT JUST THE EXPECTED ONE. Arming only the expected device makes
    the check one-sided: a silent read then means either "the wrong device is there" or "the right
    device is broken", which is the ambiguity the whole project exists to remove. With both armed,
    a decode NAMES the device — and hearing the one that is supposed to be off the pad is a stray,
    which is a different fault again and gets said out loud as one.
    """
    present = [d for d in topology.on_pad if d in PROBE_ID]
    if not present:
        raise IdentityFault("identity check asked for on %s, which has no Chameleon on the pad"
                            % topology.name)
    if len(present) > 1:
        # CU1_CU2: the source is the one that is NOT the reader.
        present = [d for d in present if d != topology.reader_dev]
    expected = present[0]

    for dev, cham in chameleons.items():
        if dev not in PROBE_ID or dev == topology.reader_dev:
            continue
        try:
            cham.arm(probe_protocol(dev, protocols))
        except DeviceError as e:
            raise IdentityFault("could not arm %s with its probe id: %s" % (HUMAN[dev], e)) from e

    text = _strip_ansi(reader.read(probe_protocol(expected, protocols)))
    found = None
    strays = []
    for dev, pid in PROBE_ID.items():
        if pid.lower() in text.lower():
            if dev == expected:
                found = dev
            else:
                strays.append(dev)
    for dev, cham in chameleons.items():
        if dev in PROBE_ID and dev != topology.reader_dev:
            cham.disarm()
    return IdentityResult(expected=expected, found=found, strays=tuple(strays), text=text)


def explain(res: IdentityResult) -> str:
    if res.ok:
        return "identity confirmed by radio: %s is on the pad" % HUMAN[res.expected]
    if res.strays and res.found is None:
        return ("⛔ WRONG DEVICE. The plan says %s; the radio says %s. This is the C461 trap — the "
                "null arms cannot catch it, because the wrong Chameleon is exactly as silent as the "
                "right one. Everything measured under this topology would be attributed to the "
                "wrong device."
                % (HUMAN[res.expected], " and ".join(HUMAN[d] for d in res.strays)))
    if res.strays:
        return ("⛔ TWO EMITTERS. %s answered as expected, but so did %s — something that is meant "
                "to be off the pad is still in the field, and every arm here would be a mixture."
                % (HUMAN[res.expected], " and ".join(HUMAN[d] for d in res.strays)))
    return ("⛔ NOTHING ANSWERED. %s was armed with a unique EM410X id and the reader heard nothing, "
            "so the pad is empty, the device is dead, or the reader is. No arm measured under this "
            "topology can be told apart from any of those three."
            % HUMAN[res.expected])


# ------------------------------------------------------------------ null sweeps (M35 A/B/A)

@dataclass(frozen=True)
class NullSweep:
    label: str
    hits: frozenset[str] = frozenset()
    detail: dict[str, str] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.hits


def null_sweep(label: str, reader, protocols: list[reg.Protocol], emitters: list) -> NullSweep:
    """Every decoder in the block, asked with nothing emitting.

    ⚠ THE DEVICES STAY ON THE PAD AND GO TO READER MODE — see `topology.null_topology`. A null taken
    with the pad cleared measures a different bench from the one the arms were measured on.
    """
    for e in emitters:
        e.disarm()
    hits, detail = set(), {}
    for p in protocols:
        text = _strip_ansi(reader.read(p))
        if p.expect and p.expect.lower() in text.lower():
            hits.add(p.key)
            detail[p.key] = text.strip()[:200]
    return NullSweep(label=label, hits=frozenset(hits), detail=detail)


def sweeps_agree(before: NullSweep, after: NullSweep) -> tuple[bool, str]:
    """⛔ A/B/A, AND A DIFFERENCE VOIDS THE RUN RATHER THAN DEGRADING IT (DESIGN.md §3).

    Against anything intermittent, A/B is not an experiment. A closing sweep that differs from the
    opening one says the bench changed underneath the block — and there is no way afterwards to
    know which arms were measured before it changed and which after, so none of them stand.
    """
    if before.hits == after.hits:
        return True, "null sweeps agree (%s)" % ("both clean" if before.clean
                                                 else "both dirty: " + ", ".join(sorted(before.hits)))
    appeared = sorted(after.hits - before.hits)
    vanished = sorted(before.hits - after.hits)
    bits = []
    if appeared:
        bits.append("appeared: " + ", ".join(appeared))
    if vanished:
        bits.append("vanished: " + ", ".join(vanished))
    return False, ("⛔ THE CLOSING NULL SWEEP DIFFERS FROM THE OPENING ONE (%s). The bench changed "
                   "underneath this block, and nothing measured in it can be assigned to a before "
                   "or an after. The block is VOID, not degraded." % "; ".join(bits))
