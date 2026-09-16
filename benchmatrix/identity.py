"""Radio-identity check and null sweeps — the two controls that bracket every station.

⛔⛔ THE IDENTITY RULE (RULES.md §4): every setup is followed by a check, not a question. The
operator's word is the PLAN; the radio is the RECORD.

⛔ IT IS THE ONE CHECK THE NULL SWEEPS CANNOT DO FOR YOU. A null sweep catches a STRAY emitter; it
cannot catch a SWAPPED one, because the wrong Chameleon in reader mode is exactly as silent as the
right one. A wrong-device run produces an unfalsifiable null — every arm scored against something
that was never listening.

⭐ WHAT THE PORT ALREADY TELLS US, AND WHAT IT DOES NOT. Each device is commanded over its own named
serial port, so *which device we are talking to* is never in doubt. What the port cannot say is
*which device is physically in the stack*, and that is the only thing this check is about.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import registry as reg
from .devices import DeviceError
from .outcomes import _strip_ansi
from .stations import CU1, CU2, HUMAN, READERS, Station

#: Device-unique probe ids, distinct in every nibble so a partial decode still names one device,
#: and deliberately unlike any credential in the registry.
PROBE_ID = {CU1: "C1C1C1C1C1", CU2: "C2C2C2C2C2"}

PROBE_PROTOCOL = "em410x"

#: ⛔ THE PROBE IS NOT THE `em410x` ARM. It borrows EM410X's read command because that is the one
#: protocol every reader is known to decode from a Chameleon, but it carries a key of its own so a
#: probe read can never be filed as an `em410x` result, nor an `em410x` script intercept a probe.
PROBE_KEY = "__probe__"

#: How many reads to union before concluding nothing answered. A tag left in the stack can win the
#: decoder's attention on any single read, so one silent read is not proof of absence.
PROBE_READS = 3


class IdentityFault(Exception):
    """The bench is not what the plan says it is. Never recoverable by retrying the read."""


@dataclass(frozen=True)
class IdentityResult:
    expected: frozenset
    found: frozenset
    strays: frozenset
    reader: str
    text: str
    #: Every Chameleon that was armed for the check, including ones meant to be off the bench.
    armed: frozenset = frozenset()

    @property
    def ok(self) -> bool:
        return self.found == self.expected and not self.strays


def probe_protocol(device: str, protocols: dict[str, reg.Protocol] = reg.TIER0) -> reg.Protocol:
    base = protocols[PROBE_PROTOCOL]
    # ⚠ BOTH EXPECTATIONS ARE SET. The probe may be read by the Proxmark or by the other
    # Chameleon, and each renders EM410X in its own wording — a probe carrying only one client's
    # expectation would report the other as having heard nothing.
    return reg.Protocol(**{**base.__dict__,
                           "key": PROBE_KEY,
                           "expect": PROBE_ID[device],
                           "cu_expect": PROBE_ID[device],
                           "cu_emulate": "lf em 410x econfig -s {slot} --id %s"
                                         % PROBE_ID[device].lower()})


def identifiable(station: Station) -> frozenset:
    """Which Chameleons in this stack the radio can actually name.

    ⭐ A CHAMELEON THAT IS THE ONLY READER IN ITS OWN STACK NEEDS NO RADIO CHECK. We command it over
    its own named serial port, so which device it is was never in question; the check exists to say
    which device is IN FRONT OF a reader, and there is nothing in front of it but a tag, whose
    identity its own credential decode establishes. A stray Chameleon nearby is still caught, by the
    null sweep.
    """
    targets = [d for d in station.stack if d in PROBE_ID]
    if not targets:
        return frozenset()
    reader_dev = _reader_for(station, targets)
    return frozenset(d for d in targets if d != reader_dev)


def _reader_for(station: Station, targets: list) -> str:
    """Prefer a reader that is not itself one of the devices being identified."""
    rid = next((r for r in station.readers() if READERS[r] not in targets), None)
    if rid is None:
        rid = station.readers()[0] if station.readers() else None
    return READERS[rid] if rid else ""


def check(station: Station, devices, chameleons: dict,
          protocols: dict[str, reg.Protocol] = reg.TIER0) -> IdentityResult:
    """Arm every Chameleon on the bench, then ask a reader in the stack who is actually there.

    ⚠ EVERY CHAMELEON IS ARMED, NOT JUST THE EXPECTED ONE — including any that is supposed to be
    OUT of the stack. Arming only the expected device makes the check one-sided: a silent read then
    means either "the wrong device is there" or "the right device is broken", which is the ambiguity
    the whole project exists to remove. With all of them armed, a decode NAMES the device, and
    hearing one that should be nowhere near the stack is a stray — a different fault, reported as one.
    """
    targets = [d for d in station.stack if d in PROBE_ID]
    expected = identifiable(station)
    if not expected:
        raise IdentityFault("nothing at %s for the radio to identify — call identifiable() first"
                            % station.name)
    # A Chameleon cannot probe itself, so if the only reader in the stack is one of the targets it
    # becomes the instrument and drops out of the expected set.
    reader_dev = _reader_for(station, targets)
    reader_id = next(r for r in station.readers() if READERS[r] == reader_dev)

    armed = []
    for dev, cham in chameleons.items():
        if dev in PROBE_ID and dev != reader_dev:
            try:
                cham.arm(probe_protocol(dev, protocols))
                armed.append(dev)
            except DeviceError as e:
                raise IdentityFault("could not arm %s with its probe id: %s" % (HUMAN[dev], e)) from e

    reader = devices.by_dev(reader_dev)
    seen, text = set(), []
    for _ in range(PROBE_READS):
        got = _strip_ansi(reader.read(probe_protocol(next(iter(expected)), protocols)))
        text.append(got)
        for dev, pid in PROBE_ID.items():
            if pid.lower() in got.lower():
                seen.add(dev)
        if seen >= expected:
            break

    for dev in armed:
        chameleons[dev].disarm()

    return IdentityResult(expected=expected, found=frozenset(seen & expected),
                          strays=frozenset(seen - expected), reader=reader_id,
                          text="\n".join(text), armed=frozenset(armed))


def explain(res: IdentityResult) -> str:
    want = ", ".join(HUMAN[d] for d in sorted(res.expected))
    if res.ok:
        # ⚠ SAY THAT THE OTHERS WERE ARMED TOO. The operator watches a device they were just told
        # to set aside light up and reasonably wonders what the harness is doing with it. Arming
        # every Chameleon is the point of the check — it is what makes a decode NAME a device
        # rather than merely prove something is there, and what makes a stray detectable at all.
        others = sorted(res.armed - res.expected)
        extra = ("; %s %s armed too and stayed silent, which is how a stray would show"
                 % (", ".join(HUMAN[d] for d in others),
                    "was" if len(others) == 1 else "were")) if others else ""
        return "identity confirmed by radio (%s heard %s%s)" % (res.reader, want, extra)
    missing = sorted(res.expected - res.found)
    if res.strays and missing:
        return ("⛔ WRONG DEVICE. The stack should hold %s; the radio says %s is there instead. The "
                "null arms cannot catch this, because the wrong Chameleon is exactly as silent as "
                "the right one in reader mode. Everything measured here would be attributed to the "
                "wrong device."
                % (want, ", ".join(HUMAN[d] for d in sorted(res.strays))))
    if res.strays:
        return ("⛔ AN EXTRA EMITTER. %s answered as expected, but so did %s — something meant to be "
                "out of the stack is still in the field, and every arm here would be a mixture."
                % (want, ", ".join(HUMAN[d] for d in sorted(res.strays))))
    return ("⛔ NOTHING ANSWERED. %s was armed with a unique EM410X id and %s heard nothing in %d "
            "reads, so the stack is wrong, the device is dead, or the reader is. No arm measured "
            "here could be told apart from any of those three."
            % (", ".join(HUMAN[d] for d in missing), res.reader, PROBE_READS))


# ------------------------------------------------------- null sweeps — the A/B/A rule (RULES.md §3)

@dataclass(frozen=True)
class NullSweep:
    label: str
    hits: frozenset = frozenset()
    detail: dict = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.hits


def null_sweep(label: str, readers: list, protocols: list, emitters: list) -> NullSweep:
    """Every decoder in the station, asked by every reader in it, with nothing emitting.

    ⚠ ACTIVE DEVICES STAY IN THE STACK and go to reader mode; only a passive tag is physically
    removed, because it is the only thing with no idle state. A null taken with the stack pulled
    apart measures a different bench from the one the arms were measured on.
    """
    for e in emitters:
        try:
            e.disarm()
        except DeviceError:
            pass
    hits, detail = set(), {}
    for reader in readers:
        for p in protocols:
            text = _strip_ansi(reader.read(p))
            want = p.expect_for(getattr(reader, "id", "rd.pm3")) or p.expect
            if want and want.lower() in text.lower():
                hits.add(p.key)
                detail[p.key] = text.strip()[:200]
    return NullSweep(label=label, hits=frozenset(hits), detail=detail)


def sweeps_agree(before: NullSweep, after: NullSweep) -> tuple[bool, str]:
    """⛔ THE A/B/A RULE (RULES.md §3): a difference VOIDS the station rather than degrading it.

    Against anything intermittent, A/B is not an experiment. A closing sweep that differs from the
    opening one says the bench changed underneath the routine — and there is no way afterwards to
    know which reads were taken before it changed and which after, so none of them stand.
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
                   "underneath this station, and nothing measured here can be assigned to a before "
                   "or an after. The station is VOID, not degraded." % "; ".join(bits))
