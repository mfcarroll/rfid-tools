"""The protocol registry — one entry per protocol, holding everything needed to test it from
every side (DESIGN.md §5).

⭐ PORTED FROM `pm3grade.sh` + `emugrade.sh`, WHICH ARE THE ONLY PARTS OF THOSE SCRIPTS WORTH
KEEPING. The econfig signatures and the byte-exact expectations in them were each paid for on the
bench — `lf indala econfig` takes `--id` and not the `-r` its writer uses; `lf nexwatch econfig`
has no `--magic` at all; both were found by running one command rather than by reading. Those
strings are carried across verbatim.

⛔⛔ THREE CLASSES OF VALUE LIVE IN HERE AND THEY ARE NOT EQUALLY TRUSTWORTHY. Keep them apart:

  1. RUN ON THE BENCH — every `cu.*` and `pm3.read` string, and every `expect`, comes from
     pm3grade.sh, which has been executed against hardware.
  2. READ OUT OF SOURCE — `pm3.write` (from the client's own `clone` usage text), `flip.key` (from
     `lfrfid_protocols.c` `.name`), `pm3.decode_marker` (from each `cmdlf*.c` SUCCESS line). These
     are the same standard as SCOPE.md: *the source tree says so*, not *the device does it*.
  3. NOT KNOWN AT ALL — `flip.expect` is `None` for ten of sixteen protocols, because the Flipper's
     decoded byte string is a different encoding from the credential the Chameleon is armed with,
     and deriving it from the protocol's .c would be guessing at an answer the bench can simply be
     asked for. ⇒ `None` means the (P, rd.flip) column CANNOT BE PLANNED. It is not defaulted, not
     approximated, and not matched on the protocol name alone — that last one is the M28 trap
     `flipper.py` exists to document, where a name-substring count reported 10 successes out of 5
     attempts. Use `bench learn` to fill them in from a real tag; see `learned.py`.

⚠ CLASS 2 IS WHY `pm3.write` IS NOT ASSUMED CORRECT EITHER. Several clone commands take decoded
fields where the econfig arm takes `--raw`, so the written credential and the armed one can differ
even though both commands succeed. That does not need special handling: it surfaces as a
calibration row that decodes something other than `expect`, which `Calibration.from_row` reports as
a REGISTRY/WRITE fault rather than as a deaf reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Modulation family. Recorded truthfully; see `m52` for the rule that DESIGN.md §5 attaches to it.
FAMILIES = ("ask", "fsk", "psk")


@dataclass(frozen=True)
class Protocol:
    """⚠ `cu_read` IS `None` FOR ALL SIXTEEN AND THAT IS NOT AN OVERSIGHT. `rd.cu` is "the arm under
    test, when it has one" (DESIGN.md §1), and the Chameleon read arms live in the owning firmware
    project, not here. Until a read command is registered per protocol, plan.py refuses the whole
    `rd.cu` column rather than emit cells a channel would raise on — a column that cannot be
    measured is an exclusion with a reason, not an empty grid."""

    key: str
    tier: int
    pm3_write: str               # writes a real T5577 — the gold reference source `t55.pm3`
    pm3_read: str                # `lf <proto> reader`
    pm3_decode_marker: str       # "a demod happened", from the client's own SUCCESS line
    expect: str                  # byte-exact token that must appear in the pm3 read
    cu_type: str                 # `hw slot type -t <this>`
    cu_emulate: str              # `lf <proto> econfig -s {slot} ...`
    flip_key: str                # `.name` in lfrfid_protocols.c
    family: str                  # ask | fsk | psk — the modulation actually on the coil
    t55_capable: bool
    m52: bool                    # subcarrier-dependent ⇒ (emu.*, rd.cu) is refused, never "failed"
    cu_read: Optional[str] = None       # the Chameleon's own read arm, when it has one
    flip_expect: Optional[str] = None   # None = not known; the rd.flip column cannot be planned
    flip_write: bool = True      # False = the Flipper is known to refuse to write this to a T5577
    notes: str = ""

    def emulate_cmd(self, slot: int) -> str:
        return self.cu_emulate.format(slot=slot)

    def flip_line(self) -> Optional[str]:
        """The normalised `<name> <HEX>` line a successful Flipper read must produce."""
        return None if self.flip_expect is None else "%s %s" % (self.flip_key, self.flip_expect)


# ⛔ M52 (DESIGN.md §5): never test a SAADC-family read arm against an emulation. The set is named
# EXPLICITLY rather than derived from `family`, because the two do not agree and the difference is
# load-bearing: gallagher, securakey, noralsy and gproxii are ASK on the coil (emugrade.sh MOD
# table, measured) but are listed in DESIGN.md §5 as needing a subcarrier phase-locked to the
# reader's carrier, which only a real tag has. Deriving the rule from `family` would silently
# re-admit four cells the design refuses; deriving `family` from the rule would falsify the
# modulation record. So both are stored, and the disagreement is visible here instead of resolved
# by whichever one got read first.
M52_SUBCARRIER = frozenset({"indala", "gallagher", "securakey", "noralsy", "gproxii"})


def _p(**kw) -> Protocol:
    kw.setdefault("m52", kw["key"] in M52_SUBCARRIER)
    return Protocol(**kw)


TIER0: dict[str, Protocol] = {p.key: p for p in [
    _p(key="em410x", tier=0, family="ask", t55_capable=True,
       pm3_write="lf em 410x clone --id 2244668800",
       pm3_read="lf em 410x reader",
       pm3_decode_marker=r"EM 410x (XL )?ID",
       expect="2244668800",
       cu_type="EM410X",
       cu_emulate="lf em 410x econfig -s {slot} --id 2244668800",
       flip_key="EM4100", flip_expect="2244668800",
       notes="5-byte id both sides — the one protocol where every channel speaks the same bytes."),

    _p(key="viking", tier=0, family="ask", t55_capable=True,
       # ⚠ `--cn` IS 24 BITS AND THE ARMED ID IS 32. Viking's low byte is a checksum, so
       # `clone --cn 1A3371` is the nearest thing to `econfig --id 1a337195` — and whether it lands
       # on the same 4 bytes is a BENCH question. If it does not, the calibration row decodes
       # something other than `expect` and is reported as a registry fault, which is the correct
       # outcome and precisely why that path exists.
       pm3_write="lf viking clone --cn 1A3371",
       pm3_read="lf viking reader",
       pm3_decode_marker=r"Viking - Card",
       expect="1A337195",
       cu_type="Viking",
       cu_emulate="lf viking econfig -s {slot} --id 1a337195",
       flip_key="Viking", flip_expect="1A337195",
       notes="VIKING_DECODED_DATA_SIZE = 4, same width as the armed id."),

    _p(key="jablotron", tier=0, family="ask", t55_capable=True,
       pm3_write="lf jablotron clone --cn 8899aabbcc",
       pm3_read="lf jablotron reader",
       pm3_decode_marker=r"Jablotron - Card",
       expect="8899AABBCC",
       cu_type="Jablotron",
       cu_emulate="lf jablotron econfig -s {slot} --id 8899aabbcc",
       flip_key="Jablotron", flip_expect="8899AABBCC",
       notes="JABLOTRON_DECODED_DATA_SIZE = 5, same width as the armed id."),

    _p(key="pac", tier=0, family="ask", t55_capable=True,
       pm3_write="lf pac clone --cn CARD0042",
       pm3_read="lf pac reader",
       pm3_decode_marker=r"PAC/Stanley - Card",
       expect="CARD0042",
       cu_type="PAC",
       cu_emulate="lf pac econfig -s {slot} --cn CARD0042",
       flip_key="PAC/Stanley",
       notes="C465: the Flipper read NOTHING from a real PAC tag the pm3 read byte-exact. That is "
             "the calibration row this project exists to force, and it is expected to FAIL here."),

    _p(key="hidprox", tier=0, family="fsk", t55_capable=True,
       pm3_write="lf hid clone -w H10301 --fc 123 --cn 4567",
       pm3_read="lf hid reader",
       pm3_decode_marker=r"^.*\braw:\s*[0-9a-f]{24}\b",
       expect="FC: 123  CN: 4567",
       cu_type="HIDProx",
       cu_emulate="lf hid prox econfig -s {slot} -f H10301 --fc 123 --cn 4567",
       flip_key="H10301",
       notes="⚠ The Flipper's H10301 and HIDProx are DIFFERENT protocols — H10301 is the 26-bit "
             "arm we emit, HIDProx is `protocol_hid_generic.c` (SCOPE.md tier 2). Do not conflate."),

    _p(key="ioprox", tier=0, family="fsk", t55_capable=True,
       pm3_write="lf io clone --vn 1 --fc 83 --cn 1337",
       pm3_read="lf io reader",
       pm3_decode_marker=r"IO Prox - ",
       expect="XSF(01)53:01337",
       cu_type="ioProx",
       cu_emulate="lf ioprox econfig -s {slot} --ver 1 --fc 83 --cn 1337",
       flip_key="IoProxXSF",
       notes="IOPROXXSF_DECODED_DATA_SIZE = 4 (ver, fc, cn hi, cn lo) but the packing is the "
             "Flipper's, not ours — learn it, do not derive it."),

    _p(key="awid", tier=0, family="fsk", t55_capable=True,
       # ⚠ THE econfig ARM IS `--raw` (12 bytes) AND THE CLONE TAKES DECODED FIELDS. 26-bit AWID
       # with fc 1 / cn 1 is the nearest published example; the calibration row decides whether it
       # matches, and says so as a registry fault if it does not.
       pm3_write="lf awid clone --fmt 26 --fc 123 --cn 1337",
       pm3_read="lf awid reader",
       pm3_decode_marker=r"AWID - len:",
       expect="011d81711dd1181111111111",
       cu_type="AWID",
       cu_emulate="lf awid econfig -s {slot} --raw 011d81711dd1181111111111",
       flip_key="AWID",
       notes="⛔ pm3.write and cu.emulate are NOT known to produce the same credential. Expect "
             "the (t55.pm3, rd.pm3) row to read WRONG until the raw is matched to the fields."),

    _p(key="indala", tier=0, family="psk", t55_capable=True,
       pm3_write="lf indala clone -r a0000000e6bd0e92",
       pm3_read="lf indala reader",
       pm3_decode_marker=r"Indala \(len",
       expect="a0000000e6bd0e92",
       cu_type="Indala",
       cu_emulate="lf indala econfig -s {slot} --id a0000000e6bd0e92",
       flip_key="Indala26",
       notes="INDALA26_DECODED_DATA_SIZE = 4 against an 8-byte armed id — the Flipper prints a "
             "different encoding. M52 applies: no (emu.*, rd.cu) cell."),

    _p(key="keri", tier=0, family="psk", t55_capable=True,
       pm3_write="lf keri clone -t i --cn 12345",
       pm3_read="lf keri reader",
       pm3_decode_marker=r"KERI - Internal ID|Descrambled MS - FC:|probably KERI",
       expect="80003039",
       cu_type="Keri",
       cu_emulate="lf keri econfig -s {slot} --id 80003039",
       flip_key="Keri", flip_expect="80003039", flip_write=False,
       notes="0x80003039 = internal id 12345 with the top bit set; KERI_DECODED_DATA_SIZE = 4. "
             "⛔ Flipper cannot WRITE this to a T5577 (DESIGN.md §4) — t55.flip is unavailable."),

    _p(key="nexwatch", tier=0, family="psk", t55_capable=True,
       pm3_write="lf nexwatch clone --cn 87654321 -m 2 --nc",
       pm3_read="lf nexwatch reader",
       pm3_decode_marker=r"NexWatch raw id|88bit id",
       expect="87654321",
       cu_type="NexWatch",
       cu_emulate="lf nexwatch econfig -s {slot} --cn 87654321 -m 2",
       flip_key="Nexwatch", flip_write=False,
       notes="⚠ `clone` needs a credential flavour (--nc/--hc/--qc) that `econfig` has no "
             "argument for. If they disagree the calibration row will say so."),

    _p(key="idteck", tier=0, family="psk", t55_capable=True,
       pm3_write="lf idteck clone --raw 4944544B55667788",
       pm3_read="lf idteck reader",
       pm3_decode_marker=r"IDTECK Tag Found: Card ID",
       expect="4944544B55667788",
       cu_type="IDTECK",
       cu_emulate="lf idteck econfig -s {slot} --id 4944544b55667788",
       flip_key="Idteck", flip_expect="4944544B55667788", flip_write=False,
       notes="IDTECK_DECODED_DATA_SIZE = 8, same width as the armed id."),

    _p(key="gallagher", tier=0, family="ask", t55_capable=True,
       pm3_write="lf gallagher clone --raw 7feaa31e76d86c6d868cc249",
       pm3_read="lf gallagher reader",
       pm3_decode_marker=r"GALLAGHER - Region:",
       expect="7feaa31e76d86c6d868cc249",
       cu_type="Gallagher",
       cu_emulate="lf gallagher econfig -s {slot} --raw 7feaa31e76d86c6d868cc249",
       flip_key="Gallagher",
       notes="ASK on the coil, but M52 lists it as subcarrier-dependent — see M52_SUBCARRIER."),

    _p(key="securakey", tier=0, family="ask", t55_capable=True,
       pm3_write="lf securakey clone --raw 7fcb400001adea5344300000",
       pm3_read="lf securakey reader",
       pm3_decode_marker=r"Securakey - len:",
       expect="7fcb400001adea5344300000",
       cu_type="Securakey",
       cu_emulate="lf securakey econfig -s {slot} --raw 7fcb400001adea5344300000",
       flip_key="Radio Key",
       notes="⛔ THE FLIPPER CALLS IT `Radio Key`, WITH A SPACE. flipper.py's success pattern was "
             "one word for a whole session and scored a working emulation 0 of 6 — that number "
             "reached FINDINGS.md as an emulation defect. The name is not the protocol key."),

    _p(key="noralsy", tier=0, family="ask", t55_capable=True,
       pm3_write="lf noralsy clone --cn 112233",
       pm3_read="lf noralsy reader",
       pm3_decode_marker=r"Noralsy - Card:",
       expect="bb0214ff0112402233670000",
       cu_type="Noralsy",
       cu_emulate="lf noralsy econfig -s {slot} --raw bb0214ff0112402233670000",
       flip_key="Noralsy",
       notes="⛔ `clone --cn` vs `econfig --raw`: not known to agree. The calibration row decides."),

    _p(key="gproxii", tier=0, family="ask", t55_capable=True,
       pm3_write="lf gproxii clone --xor 141 --fmt 26 --fc 123 --cn 1337",
       pm3_read="lf gproxii reader",
       pm3_decode_marker=r"G-Prox-II - (Unknown )?[Ll]en:",
       expect="fac2a38c2b081af0210b12c2",
       cu_type="GProxII",
       cu_emulate="lf gproxii econfig -s {slot} --raw fac2a38c2b081af0210b12c2",
       flip_key="GProxII", flip_expect="FAC2A38C2B081AF0210B12C2", flip_write=False,
       notes="GPROXII_DATA_SIZE = 12, same width as the armed raw. ⛔ Flipper cannot write it."),

    _p(key="fdxb", tier=0, family="ask", t55_capable=True,
       pm3_write="lf fdxb clone --country 999 --national 1337",
       pm3_read="lf fdxb reader",
       pm3_decode_marker=r"FDX-B / ISO 11784/5 Animal Tag ID Found",
       expect="00339a080402079f8040797788040201",
       cu_type="FDXB",
       cu_emulate="lf fdxb econfig -s {slot} --raw 00339a080402079f8040797788040201",
       flip_key="FDX-B",
       notes="FDXB_DECODED_DATA_SIZE = 11 against a 16-byte armed raw — different encodings."),
]}


#: `ORDER` from pm3grade.sh, kept verbatim so a grid from this harness sits beside one from that
#: script without the rows having to be re-sorted by hand.
TIER0_ORDER = ("em410x", "viking", "jablotron", "pac", "hidprox", "ioprox", "awid", "indala",
               "keri", "nexwatch", "idteck", "gallagher", "securakey", "noralsy", "gproxii", "fdxb")


class RegistryError(Exception):
    pass


def validate(protocols: dict[str, Protocol] = TIER0) -> None:
    """Refuse a registry that cannot produce the four outcomes.

    ⛔ A MISSING `pm3_decode_marker` IS A HARD ERROR, NOT A DEFAULT. Without it the harness cannot
    tell WRONG from SILENT, and the only way to carry on would be to call every non-match SILENT —
    which is exactly the merge DESIGN.md §1 forbids. Refusing here is cheaper than discovering it
    in a grid.
    """
    problems = []
    for key, p in protocols.items():
        if p.key != key:
            problems.append("%s: key mismatch (%s)" % (key, p.key))
        if p.family not in FAMILIES:
            problems.append("%s: family %r not in %s" % (key, p.family, FAMILIES))
        if not p.pm3_decode_marker:
            problems.append("%s: no pm3_decode_marker — WRONG and SILENT would be "
                            "indistinguishable, which DESIGN.md §1 forbids" % key)
        if not p.expect:
            problems.append("%s: no byte-exact expectation" % key)
        if "{slot}" not in p.cu_emulate:
            problems.append("%s: cu_emulate has no {slot} placeholder" % key)
        if p.m52 != (key in M52_SUBCARRIER):
            problems.append("%s: m52 flag disagrees with M52_SUBCARRIER" % key)
    missing = set(TIER0_ORDER) - set(protocols)
    if protocols is TIER0 and missing:
        problems.append("tier 0 is incomplete, missing: %s" % ", ".join(sorted(missing)))
    if problems:
        raise RegistryError("registry is not fit to grade with:\n  - " + "\n  - ".join(problems))


def resolve(names: list[str] | tuple[str, ...] | None) -> list[Protocol]:
    """Names -> protocols, in TIER0_ORDER. Unknown names are an error, never a silent skip."""
    if not names:
        return [TIER0[k] for k in TIER0_ORDER]
    unknown = [n for n in names if n not in TIER0]
    if unknown:
        raise RegistryError("unknown protocol(s): %s\nknown: %s"
                            % (", ".join(unknown), ", ".join(TIER0_ORDER)))
    wanted = set(names)
    return [TIER0[k] for k in TIER0_ORDER if k in wanted]
