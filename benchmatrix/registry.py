"""The protocol registry — one entry per protocol, holding everything needed to test it from
every side (RULES.md §2).

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
     approximated, and not matched on the protocol name alone — that last one breaks the name-match
     rule (RULES.md §6), which exists because a name-substring count once reported 10 successes out
     of 5 attempts. Use `bench learn` to fill them in from a real tag; see `learned.py`.

⚠ CLASS 2 IS WHY `pm3.write` IS NOT ASSUMED CORRECT EITHER. Several clone commands take decoded
fields where the econfig arm takes `--raw`, so the written credential and the armed one can differ
even though both commands succeed. That does not need special handling: it surfaces as a
calibration row that decodes something other than `expect`, which `Calibration.from_row` reports as
a REGISTRY/WRITE fault rather than as a deaf reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

#: Modulation family. Recorded truthfully; see `m52` for the rule that RULES.md §2 attaches to it.
FAMILIES = ("ask", "fsk", "psk")


@dataclass(frozen=True)
class Protocol:
    """One protocol, described from every side a bench can approach it from.

    ⭐⭐ THE CHAMELEON IS A READER AND A WRITER, NOT ONLY AN EMITTER, and `cu_read` is the most
    important field in this table. An emulation is a waveform driven onto a coil; only a real tag's
    silicon produces genuine load modulation. So `(t55.*, rd.cu)` — the Chameleon decoding a real
    T5577 — is the ONLY measurement that says whether its decoders work on real RF, and no amount
    of emulation testing substitutes for it. It is simultaneously the control that licenses the
    `rd.cu` column and the headline result of the run.
    """

    key: str
    tier: int
    #: ⛔⛔ EVERY CAPABILITY IS OPTIONAL, BECAUSE THE FIRMWARE'S ARE. The first version of this
    #: registry assumed every protocol could be emulated, read and written by every device, which is
    #: false in three different directions: `fdxa`, `paradox` and `pyramid` are read and cloned but
    #: have no emitter; `instafob` is scan-only; `em410x_electra` is emulated and written but has no
    #: scan command at all. A `None` here is a fact about the firmware, and the planner refuses the
    #: cells it makes impossible with that fact as the reason — which is a different statement from
    #: a cell that was measured and failed.
    pm3_write: Optional[str]     # writes a real T5577 — the gold reference source `t55.pm3`
    pm3_read: Optional[str]      # `lf <proto> reader`
    pm3_decode_marker: Optional[str]   # "a demod happened", from the client's own SUCCESS line
    expect: Optional[str]        # byte-exact token that must appear in the pm3 read
    cu_type: str                 # `hw slot type -t <this>`
    cu_emulate: Optional[str]    # `lf <proto> econfig -s {slot} ...`; None = no emitter exists
    flip_key: str                # `.name` in lfrfid_protocols.c
    family: str                  # ask | fsk | psk — the modulation actually on the coil
    t55_capable: bool
    subcarrier: bool                    # subcarrier-dependent ⇒ (emu.*, rd.cu) is refused, never "failed"
    cu_read: Optional[str] = None       # the Chameleon's own decoder — `lf <proto> read`
    cu_write: Optional[str] = None      # the Chameleon's own T5577 writer — `lf <proto> write`
    cu_decode_marker: Optional[str] = None   # "a demod happened", in the Chameleon's own wording
    cu_expect: Optional[str] = None     # None = not known; the rd.cu* column cannot be planned
    flip_expect: Optional[str] = None   # None = not known; the rd.flip column cannot be planned
    flip_write: bool = True      # False = the Flipper is known to refuse to write this to a T5577
    #: ⛔ Needs `LF_RESEARCH_CMDS_ENABLED`, which defaults to 0 and is set only on our own branch. A
    #: step using one of these cannot run against stock or upstream firmware, and a run that forgets
    #: that reports a TOOL gap as a FIRMWARE gap — this project's own failure mode, committed by its
    #: own harness.
    research_only: bool = False
    notes: str = ""

    def emulate_cmd(self, slot: int) -> str:
        if self.cu_emulate is None:
            raise RegistryError("%s has no emitter in this firmware" % self.key)
        return self.cu_emulate.format(slot=slot)

    def can(self, what: str) -> bool:
        """`emulate` | `cu_read` | `cu_write` | `pm3_read` | `pm3_write` — what the firmware has."""
        return bool({"emulate": self.cu_emulate, "cu_read": self.cu_read,
                     "cu_write": self.cu_write, "pm3_read": self.pm3_read,
                     "pm3_write": self.pm3_write}[what])

    def flip_line(self) -> Optional[str]:
        """The normalised `<name> <HEX>` line a successful Flipper read must produce."""
        return None if self.flip_expect is None else "%s %s" % (self.flip_key, self.flip_expect)

    def expect_for(self, reader: str) -> Optional[str]:
        """⛔ THE EXPECTATION IS PER (PROTOCOL, READER), NOT PER PROTOCOL. Three clients decode the
        same credential and print it three different ways — the Proxmark renders `FC: 123  CN: 4567`
        where the Chameleon prints `HIDProx/H10301` and its own fields. Comparing one client's
        output against another's expectation reports a working decoder as silent."""
        if reader == "rd.flip":
            return self.flip_line()
        if reader in ("rd.cu1", "rd.cu2"):
            return self.cu_expect
        return self.expect

    def marker_for(self, reader: str) -> Optional[str]:
        if reader in ("rd.cu1", "rd.cu2"):
            return self.cu_decode_marker
        return self.pm3_decode_marker


# ⛔ THE SUBCARRIER RULE (RULES.md §2): never judge an emulation with a subcarrier-dependent read
# arm. The set is named
# EXPLICITLY rather than derived from `family`, because the two do not agree and the difference is
# load-bearing: gallagher, securakey, noralsy and gproxii are ASK on the coil (emugrade.sh MOD
# table, measured) but are listed in RULES.md §2 as needing a subcarrier phase-locked to the
# reader's carrier, which only a real tag has. Deriving the rule from `family` would silently
# re-admit four cells the design refuses; deriving `family` from the rule would falsify the
# modulation record. So both are stored, and the disagreement is visible here instead of resolved
# by whichever one got read first.
SUBCARRIER_RULE = frozenset({"indala", "indala224", "gallagher", "securakey", "noralsy",
                             "gproxii"})

#: ⛔ Protocols the Chameleon can emulate and write but CANNOT scan — `data_cmd.h` has no
#: `*_SCAN` for them. Listed so that a missing `cu_read` is a recorded fact and not an omission.
NO_CU_SCAN = frozenset({"em410x_electra"})


def _p(**kw) -> Protocol:
    kw.setdefault("subcarrier", kw["key"] in SUBCARRIER_RULE)
    return Protocol(**kw)


ALL: dict[str, Protocol] = {p.key: p for p in [
    _p(key="em410x", tier=0, family="ask", t55_capable=True,
       pm3_write="lf em 410x clone --id 2244668800",
       pm3_read="lf em 410x reader",
       pm3_decode_marker=r"EM 410x (XL )?ID",
       expect="2244668800",
       cu_type="EM410X",
       cu_emulate="lf em 410x econfig -s {slot} --id 2244668800",
       cu_read="lf em 410x read",
       cu_write="lf em 410x write --id 2244668800",
       # ⛔ THE DEVICE PRINTS THE VARIANT: `EM410X/64: 2244668800`, not `EM410X:`. Observed on the
       # bench 2026-09-15. This marker was derived from the source's `{TagSpecificType(data[0])}:`
       # and guessed at how the enum renders — and it never fired. It went unnoticed because a
       # byte-exact hit forces `decoded` True, so a CORRECT read masked it; a read that decoded the
       # WRONG value would have been reported SILENT, which is the merge the four outcomes forbid.
       cu_decode_marker=r"EM410X[/_0-9]*\s*:",
       cu_expect="2244668800",
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
       cu_read="lf viking read",
       cu_write="lf viking write --id 1a337195",
       cu_decode_marker=r"Viking\s*:",
       cu_expect="1a337195",
       flip_key="Viking", flip_expect="1A337195",
       notes="VIKING_DECODED_DATA_SIZE = 4, same width as the armed id."),

    _p(key="jablotron", tier=0, family="ask", t55_capable=True,
       pm3_write="lf jablotron clone --cn 8899aabbcc",
       pm3_read="lf jablotron reader",
       pm3_decode_marker=r"Jablotron - Card",
       expect="8899AABBCC",
       cu_type="Jablotron",
       cu_emulate="lf jablotron econfig -s {slot} --id 8899aabbcc",
       cu_read="lf jablotron read",
       cu_write="lf jablotron write --id 8899aabbcc",
       cu_decode_marker=r"Jablotron ID\s*:",
       cu_expect="8899aabbcc",
       flip_key="Jablotron", flip_expect="8899AABBCC",
       notes="JABLOTRON_DECODED_DATA_SIZE = 5, same width as the armed id."),

    _p(key="pac", tier=0, family="ask", t55_capable=True,
       pm3_write="lf pac clone --cn CARD0042",
       pm3_read="lf pac reader",
       pm3_decode_marker=r"PAC/Stanley - Card",
       expect="CARD0042",
       cu_type="PAC",
       cu_emulate="lf pac econfig -s {slot} --cn CARD0042",
       cu_read="lf pac read",
       cu_write="lf pac write --cn CARD0042",
       cu_decode_marker=r"PAC/Stanley - CN",
       cu_expect="CARD0042",
       flip_key="PAC/Stanley",
       notes="The Flipper has read NOTHING from a real PAC tag the Proxmark read byte-exact. That is "
             "the calibration row this project exists to force, and it is expected to FAIL here."),

    _p(key="hidprox", tier=0, family="fsk", t55_capable=True,
       pm3_write="lf hid clone -w H10301 --fc 123 --cn 4567",
       pm3_read="lf hid reader",
       pm3_decode_marker=r"^.*\braw:\s*[0-9a-f]{24}\b",
       expect="FC: 123  CN: 4567",
       cu_type="HIDProx",
       cu_emulate="lf hid prox econfig -s {slot} -f H10301 --fc 123 --cn 4567",
       cu_read="lf hid prox read",
       cu_write="lf hid prox write -f H10301 --fc 123 --cn 4567",
       cu_decode_marker=r"HIDProx/",
       cu_expect=None,
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
       cu_read="lf ioprox read",
       cu_write="lf ioprox write --ver 1 --fc 83 --cn 1337",
       cu_decode_marker=r"ioProx XSF",
       cu_expect=None,
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
       cu_read="lf awid read",
       cu_write="lf awid write --raw 011d81711dd1181111111111",
       cu_decode_marker=r"AWID FSK2a",
       cu_expect="011d81711dd1181111111111",
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
       cu_read="lf indala read",
       cu_write="lf indala write --raw a0000000e6bd0e92",
       cu_decode_marker=r"Indala\d*\s+PSK1",
       cu_expect="a0000000e6bd0e92",
       flip_key="Indala26",
       notes="INDALA26_DECODED_DATA_SIZE = 4 against an 8-byte armed id — the Flipper prints a "
             "different encoding. The subcarrier rule applies: no (emu.*, rd.cu) cell."),

    _p(key="keri", tier=0, family="psk", t55_capable=True,
       pm3_write="lf keri clone -t i --cn 12345",
       pm3_read="lf keri reader",
       pm3_decode_marker=r"KERI - Internal ID|Descrambled MS - FC:|probably KERI",
       expect="80003039",
       cu_type="Keri",
       cu_emulate="lf keri econfig -s {slot} --id 80003039",
       cu_read="lf keri read",
       cu_write="lf keri write --id 80003039",
       cu_decode_marker=r"Keri PSK1",
       cu_expect="80003039",
       flip_key="Keri", flip_expect="80003039", flip_write=False,
       notes="0x80003039 = internal id 12345 with the top bit set; KERI_DECODED_DATA_SIZE = 4. "
             "⛔ Flipper cannot WRITE this to a T5577 — t55.flip is unavailable."),

    _p(key="nexwatch", tier=0, family="psk", t55_capable=True,
       pm3_write="lf nexwatch clone --cn 87654321 -m 2 --nc",
       pm3_read="lf nexwatch reader",
       pm3_decode_marker=r"NexWatch raw id|88bit id",
       expect="87654321",
       cu_type="NexWatch",
       cu_emulate="lf nexwatch econfig -s {slot} --cn 87654321 -m 2",
       cu_read="lf nexwatch read",
       cu_write="lf nexwatch write --cn 87654321 -m 2",
       cu_decode_marker=r"NexWatch PSK1",
       cu_expect="87654321",
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
       cu_read="lf idteck read",
       cu_write="lf idteck write --id 4944544b55667788",
       cu_decode_marker=r"IDTECK PSK1",
       cu_expect="4944544b55667788",
       flip_key="Idteck", flip_expect="4944544B55667788", flip_write=False,
       notes="IDTECK_DECODED_DATA_SIZE = 8, same width as the armed id."),

    _p(key="gallagher", tier=0, family="ask", t55_capable=True,
       pm3_write="lf gallagher clone --raw 7feaa31e76d86c6d868cc249",
       pm3_read="lf gallagher reader",
       pm3_decode_marker=r"GALLAGHER - Region:",
       expect="7feaa31e76d86c6d868cc249",
       cu_type="Gallagher",
       cu_emulate="lf gallagher econfig -s {slot} --raw 7feaa31e76d86c6d868cc249",
       cu_read="lf gallagher read",
       cu_write="lf gallagher write --raw 7feaa31e76d86c6d868cc249",
       cu_decode_marker=r"Gallagher ASK/Manchester",
       cu_expect="7feaa31e76d86c6d868cc249",
       flip_key="Gallagher",
       notes="ASK on the coil, but subcarrier-dependent all the same — see SUBCARRIER_RULE."),

    _p(key="securakey", tier=0, family="ask", t55_capable=True,
       pm3_write="lf securakey clone --raw 7fcb400001adea5344300000",
       pm3_read="lf securakey reader",
       pm3_decode_marker=r"Securakey - len:",
       expect="7fcb400001adea5344300000",
       cu_type="Securakey",
       cu_emulate="lf securakey econfig -s {slot} --raw 7fcb400001adea5344300000",
       cu_read="lf securakey read",
       cu_write="lf securakey write --raw 7fcb400001adea5344300000",
       cu_decode_marker=r"Securakey ASK/Manchester",
       cu_expect="7fcb400001adea5344300000",
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
       cu_read="lf noralsy read",
       cu_write="lf noralsy write --raw bb0214ff0112402233670000",
       cu_decode_marker=r"Noralsy ASK/Manchester",
       cu_expect="bb0214ff0112402233670000",
       flip_key="Noralsy",
       notes="⛔ `clone --cn` vs `econfig --raw`: not known to agree. The calibration row decides."),

    _p(key="gproxii", tier=0, family="ask", t55_capable=True,
       pm3_write="lf gproxii clone --xor 141 --fmt 26 --fc 123 --cn 1337",
       pm3_read="lf gproxii reader",
       pm3_decode_marker=r"G-Prox-II - (Unknown )?[Ll]en:",
       expect="fac2a38c2b081af0210b12c2",
       cu_type="GProxII",
       cu_emulate="lf gproxii econfig -s {slot} --raw fac2a38c2b081af0210b12c2",
       cu_read="lf gproxii read",
       cu_write="lf gproxii write --raw fac2a38c2b081af0210b12c2",
       cu_decode_marker=r"GProxII ASK/biphase",
       cu_expect="fac2a38c2b081af0210b12c2",
       flip_key="GProxII", flip_expect="FAC2A38C2B081AF0210B12C2", flip_write=False,
       notes="GPROXII_DATA_SIZE = 12, same width as the armed raw. ⛔ Flipper cannot write it."),

    _p(key="fdxb", tier=0, family="ask", t55_capable=True,
       pm3_write="lf fdxb clone --country 999 --national 1337",
       pm3_read="lf fdxb reader",
       pm3_decode_marker=r"FDX-B / ISO 11784/5 Animal Tag ID Found",
       expect="00339a080402079f8040797788040201",
       cu_type="FDXB",
       cu_emulate="lf fdxb econfig -s {slot} --raw 00339a080402079f8040797788040201",
       cu_read="lf fdxb read",
       cu_write="lf fdxb write --raw 00339a080402079f8040797788040201",
       cu_decode_marker=r"FDX-B ASK/biphase",
       cu_expect="00339a080402079f8040797788040201",
       flip_key="FDX-B",
       notes="FDXB_DECODED_DATA_SIZE = 11 against a 16-byte armed raw — different encodings."),
    # ---------------------------------------------------------------- tier 0b: built, never tested
    # ⭐ These two are not new work. The firmware dispatches them (`lf_tag_em.c`, 18 entries) and has
    # done all along; they are grid rows nobody has run. The first draft of SCOPE.md counted our
    # capability off `pm3grade.sh`'s arm list — a test script — and so reported 16 where the firmware
    # emulates 18. A number taken from the nearest artefact rather than from the thing it describes.

    _p(key="em410x_electra", tier=0, family="ask", t55_capable=True,
       pm3_write="lf em 410x clone --id 2244668800 --electra",
       pm3_read="lf em 410x reader",
       pm3_decode_marker=r"EM 410x (XL )?ID",
       # ⛔ THE TWO WRITERS DO NOT WRITE THE SAME CREDENTIAL HERE, which no other entry has to deal
       # with. `--electra` is a FLAG: the Proxmark appends its own fixed Electra blocks to a 5-byte
       # EM410X id, while the Chameleon takes a 13-byte id that carries the Electra half itself. So
       # there is no single byte-exact token that both produce, and `expect = None` refuses the
       # `rd.pm3` column until the bench says what the Proxmark prints for a Chameleon-written tag.
       expect=None,
       cu_type="EM410X_ELECTRA",
       cu_emulate="lf em 410x econfig -s {slot} --id deadbeef880102030405060708",
       cu_read=None,
       cu_write="lf em 410x write --id deadbeef880102030405060708",
       cu_decode_marker=None,
       cu_expect=None,
       flip_key="Electra",
       notes="⛔ NO `EM410X_ELECTRA_SCAN` EXISTS — the Chameleon emulates and writes Electra but "
             "cannot read it, so `rd.cu*` is refused for it. Emulated since before the first "
             "grid; never once tested."),

    _p(key="indala224", tier=0, family="psk", t55_capable=True,
       pm3_write="lf indala clone -r 80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5",
       pm3_read="lf indala reader",
       pm3_decode_marker=r"Indala \(len",
       expect="80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5",
       cu_type="Indala224",
       cu_emulate="lf indala econfig -s {slot} "
                  "--id 80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5 --224",
       cu_read="lf indala read --224",
       cu_write="lf indala write --raw "
                "80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5 --224",
       cu_decode_marker=r"Indala224 PSK1",
       cu_expect="80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5",
       flip_key="Indala224", flip_write=False,
       notes="Emulated and never tested. ⛔ The Flipper emulates Indala224 but cannot WRITE it, and "
             "the Proxmark does not decode the Flipper's emulation of it — two registered gaps "
             "meeting on one protocol."),

    # ---------------------------------------------------------------- tier 1: read and clone, but
    # no emitter. ⛔ A DIFFERENT ROW SHAPE, NOT A MISSING PROTOCOL. `(t55.cu*, rd.pm3)` is testable
    # today; `(emu.cu*, *)` cannot exist. The planner refuses the emulated cells with that as the
    # reason, which is a different statement from a cell that was measured and failed.

    _p(key="paradox", tier=1, family="fsk", t55_capable=True,
       pm3_write="lf paradox clone --raw 0f55555695596a6a9999a59a",
       pm3_read="lf paradox reader",
       pm3_decode_marker=r"Paradox -",
       expect="0f55555695596a6a9999a59a",
       cu_type="Paradox",
       cu_emulate=None,
       cu_read="lf paradox read",
       cu_write="lf paradox write --raw 0f55555695596a6a9999a59a",
       cu_decode_marker=r"Paradox FSK2a",
       cu_expect="0f55555695596a6a9999a59a",
       flip_key="Paradox",
       notes="Reader and T55xx writer exist; no emitter. Both clients use the same raw frame, so "
             "the calibration row should agree on the first run."),

    _p(key="pyramid", tier=1, family="fsk", t55_capable=True,
       pm3_write="lf pyramid clone --raw 0001010101010101010440013223921c",
       pm3_read="lf pyramid reader",
       pm3_decode_marker=r"Pyramid - (Unknown )?len:",
       expect="0001010101010101010440013223921c",
       cu_type="Pyramid",
       cu_emulate=None,
       cu_read="lf pyramid read",
       cu_write="lf pyramid write --raw 0001010101010101010440013223921c",
       cu_decode_marker=r"Pyramid FSK2a",
       cu_expect="0001010101010101010440013223921c",
       flip_key="Pyramid",
       notes="⚠ The two clients ship DIFFERENT example frames; this uses the Proxmark's for both "
             "so the writers agree. If the Chameleon's writer rejects it, that is the finding."),

    _p(key="fdxa", tier=1, family="fsk", t55_capable=True,
       # ⛔ `lf destron clone` exists but its argument shape is not recorded in the client's own
       # examples, so there is no gold writer for this protocol yet and the planner will say so.
       pm3_write=None,
       pm3_read="lf destron reader",
       pm3_decode_marker=r"FDX-A FECAVA Destron",
       expect=None,
       cu_type="FDXA",
       cu_emulate=None,
       cu_read="lf fdxa read",
       cu_write="lf fdxa write --raw 551d95aa96a999a69aa5a59a",
       cu_decode_marker=r"FDX-A FSK2a",
       cu_expect="551d95aa96a999a69aa5a59a",
       flip_key="FDX-A",
       notes="The Proxmark calls it Destron. Reader and Chameleon writer exist; no emitter, and no "
             "Proxmark clone signature recorded yet — so nothing can license it."),

    _p(key="instafob", tier=1, family="ask", t55_capable=False,
       pm3_write=None, pm3_read=None, pm3_decode_marker=None, expect=None,
       cu_type="InstaFob",
       cu_emulate=None,
       cu_read="lf instafob read",
       cu_write=None,
       cu_decode_marker=r"InstaFob ASK/Manchester",
       cu_expect=None,
       flip_key="InstaFob",
       notes="⛔ SCAN ONLY — no T55xx write, no emitter, and no Proxmark command at all. Nothing on "
             "this bench can put an InstaFob credential anywhere, so no reader can be licensed for "
             "it. Registered so the capability is recorded, not because it can be measured."),
]}



#: ⭐ EIGHTEEN, NOT SIXTEEN. The first sixteen are `pm3grade.sh`'s `ORDER`, kept in place so a grid
#: from this harness sits beside one from that script without re-sorting; `em410x_electra` and
#: `indala224` follow, because the firmware has emulated them all along and nobody had run them.
TIER0_ORDER = ("em410x", "viking", "jablotron", "pac", "hidprox", "ioprox", "awid", "indala",
               "keri", "nexwatch", "idteck", "gallagher", "securakey", "noralsy", "gproxii", "fdxb",
               "em410x_electra", "indala224")

#: Read and cloned by the firmware but not emulated — a different row shape, not a gap.
TIER1_ORDER = ("paradox", "pyramid", "fdxa", "instafob")


#: Tier 0 alone, which is what a default run measures.
TIER0: dict = {}


class RegistryError(Exception):
    pass


def _partition() -> None:
    TIER0.clear()
    TIER0.update({k: v for k, v in ALL.items() if v.tier == 0})


def validate(protocols: dict[str, Protocol] | None = None) -> None:
    """Refuse a registry that cannot produce the four outcomes.

    ⛔ A MISSING `pm3_decode_marker` IS A HARD ERROR, NOT A DEFAULT. Without it the harness cannot
    tell WRONG from SILENT, and the only way to carry on would be to call every non-match SILENT —
    which is exactly the merge RULES.md §1 forbids. Refusing here is cheaper than discovering it
    in a grid.
    """
    protocols = ALL if protocols is None else protocols
    problems = []
    for key, p in protocols.items():
        if p.key != key:
            problems.append("%s: key mismatch (%s)" % (key, p.key))
        if p.family not in FAMILIES:
            problems.append("%s: family %r not in %s" % (key, p.family, FAMILIES))
        if p.pm3_read and not p.pm3_decode_marker:
            problems.append("%s: has a pm3 reader but no decode marker — WRONG and SILENT would be "
                            "indistinguishable, which the four outcomes forbid" % key)
        if p.expect and not p.pm3_read:
            problems.append("%s: has a pm3 expectation but no pm3 reader to produce it" % key)
        if p.cu_emulate and "{slot}" not in p.cu_emulate:
            problems.append("%s: cu_emulate has no {slot} placeholder" % key)
        if p.cu_read and not p.cu_decode_marker:
            problems.append("%s: has a Chameleon reader but no decode marker" % key)
        if not any(p.can(w) for w in ("emulate", "cu_read", "cu_write", "pm3_read")):
            problems.append("%s: no capability at all — nothing could be measured" % key)
        if p.subcarrier != (key in SUBCARRIER_RULE):
            problems.append("%s: m52 flag disagrees with SUBCARRIER_RULE" % key)
        # ⚠ A CAPABILITY THE FIRMWARE HAS MUST BE REGISTERED. The check is no longer "every
        # protocol has every arm" — that was the false assumption — but a `None` still has to be a
        # deliberate statement about the firmware rather than an entry nobody got round to.
        if p.tier == 0 and not p.cu_read and p.key not in NO_CU_SCAN:
            problems.append("%s: no cu_read, and it is not in NO_CU_SCAN — say which it is" % key)
    missing = set(TIER0_ORDER) - set(protocols)
    if protocols is ALL and missing:
        problems.append("tier 0 is incomplete, missing: %s" % ", ".join(sorted(missing)))
    if problems:
        raise RegistryError("registry is not fit to grade with:\n  - " + "\n  - ".join(problems))


ORDER = TIER0_ORDER + TIER1_ORDER


def resolve(names: list[str] | tuple[str, ...] | None) -> list[Protocol]:
    """Names -> protocols, in registry order. A default run is tier 0; tier 1 must be asked for.

    ⚠ Unknown names are an error, never a silent skip — a typo that quietly measures fifteen
    protocols instead of sixteen is the kind of thing that reaches a published grid.
    """
    if not names:
        return [ALL[k] for k in TIER0_ORDER]
    unknown = [n for n in names if n not in ALL]
    if unknown:
        raise RegistryError("unknown protocol(s): %s\nknown: %s"
                            % (", ".join(unknown), ", ".join(ORDER)))
    wanted = set(names)
    return [ALL[k] for k in ORDER if k in wanted]


#: ⛔⛔ YOU CANNOT VERIFY A WRITE THAT WRITES WHAT IS ALREADY THERE. Every writer in this registry
#: puts the SAME credential on the tag for a given protocol, so after the Proxmark has written it, a
#: byte-exact read following the Chameleon's write proves nothing about the Chameleon: a write that
#: did nothing at all leaves exactly the same reading behind. The `t55.cu*` and `t55.flip` columns
#: would have measured the Proxmark's work and credited it to the device under test.
#:
#: ⇒ Before a writer under test is asked to write P, the tag is put into a state known to DIFFER
#: from P, and that parking write is itself verified. Then a read of P afterwards can only have come
#: from the writer under test. EM410X is the parking protocol because it is the one arm every reader
#: on the bench is known to decode.
PARK_ID = "5A5A5A5A5A"
PARK_KEY = "__park__"


def park_protocol(protocols: dict[str, Protocol] | None = None) -> Protocol:
    """A credential distinct from every entry in the registry, used to clear the tag."""
    base = (protocols or TIER0)["em410x"]
    return Protocol(**{**base.__dict__,
                       "key": PARK_KEY,
                       "expect": PARK_ID,
                       "cu_expect": PARK_ID,
                       "flip_expect": PARK_ID,
                       "pm3_write": "lf em 410x clone --id %s" % PARK_ID,
                       "cu_write": "lf em 410x write --id %s" % PARK_ID.lower()})


_partition()
