"""The grid people actually want: protocols down, and what each DEVICE can do with each.

⭐⭐ A READER-BY-SOURCE GRID ANSWERS A QUESTION ABOUT PAIRS, AND THE QUESTION IS ABOUT DEVICES.
"Can the Chameleon read a Proxmark emulation" is worth knowing and is not what anybody opens the
file for. They open it to ask whether the Chameleon on the desk does gproxii — read it, clone it,
pretend to be it — and that is three facts about one device, spread across three different
(source, reader) cells in the other layout.

  read     `t55.pm3 -> rd.D`      D decodes the gold tag
  write    `t55.D   -> rd.<ref>`  D puts the credential on a tag that somebody else can read back
  emulate  `emu.D   -> rd.<ref>`  D emits it well enough for somebody else to decode

⛔ THE REFERENCE READER IS THE PROXMARK, AND NOT BECAUSE IT IS SPECIAL BY ASSERTION. It is the one
device whose reading is licensed by a byte-exact gold row for every protocol here, so it is the only
one that can serve as a common yardstick — and `check_reference` VERIFIES that choice against the
record instead of trusting it: if any other reader ever decodes a source the Proxmark called silent,
the yardstick is wrong and this module says so rather than quietly publishing a shorter grid.

⛔⛔ EXCEPT FOR THE PROXMARK ITSELF, WHICH MAY NOT BE ITS OWN REFERENCE. `emu.pm3 -> rd.pm3` is the
self-judging cell the planner refuses outright; a device cannot be both the instrument and the thing
measured. So the Proxmark's own write and emulate columns are answered by whatever OTHER reader has
an answer, and say which one.

⚠ AND "THE FIRMWARE HAS NO SUCH COMMAND" IS NOT "NOBODY HAS MEASURED IT". The ChameleonUltra reads
and clones fdxa, paradox, pyramid and instafob and emulates none of them; the Proxmark has no
`keri sim` this project will register. Those are facts about a firmware, already in the registry,
and printing them as blanks would send somebody to the bench to discover what is written down.
"""

from __future__ import annotations

from dataclasses import dataclass

#: What the registry says a device has an arm for, per capability. None means "always has one".
_ARM = {
    ("pm3", "read"): "pm3_read", ("pm3", "write"): "pm3_write", ("pm3", "emulate"): None,
    ("cu1", "read"): "cu_read", ("cu1", "write"): "cu_write", ("cu1", "emulate"): "emulate",
    ("cu2", "read"): "cu_read", ("cu2", "write"): "cu_write", ("cu2", "emulate"): "emulate",
    ("flipper", "read"): None, ("flipper", "write"): None, ("flipper", "emulate"): None,
}

DEVICES = ("pm3", "cu1", "cu2", "flipper")
CAPABILITIES = ("read", "write", "emulate")

#: ⚠ `–` IS A FIRMWARE FACT AND `▫` IS AN ERRAND. Conflating them sends somebody to measure a
#: command that does not exist.
GLYPH = {"EXACT": "✅", "WRONG": "❌", "SILENT": "·", "DISPUTED": "⁇",
         "none": "–", "unmeasured": "▫"}


@dataclass(frozen=True)
class Verdict:
    capability: str
    state: str                 # EXACT | WRONG | SILENT | DISPUTED | none | unmeasured
    cell: tuple = ()           # the (protocol, source, reader) it came from, when there is one
    via: str = ""              # which reader answered, when it was not the Proxmark
    #: True when every reference reader on this bench is REFUSED this cell by a rule, so it is not
    #: outstanding work — it is unanswerable until another device is attached.
    blocked: bool = False


def has_arm(p, device: str, capability: str) -> bool:
    """Does this firmware have a command for it at all? ⛔ The Proxmark's emulate is the one case
    the registry stores as a plain value rather than a `can()` key, because it was added late."""
    if device == "pm3" and capability == "emulate":
        return bool(p.pm3_emulate)
    if device == "flipper":
        # ⚠ THE FLIPPER'S ARMS ARE NOT IN THE REGISTRY as per-capability commands — it is driven by
        # protocol NAME, and what it supports is in SCOPE.md rather than here. Claiming "no arm"
        # from an absence would invent a firmware gap, so it is only ever "not measured".
        return True
    key = _ARM.get((device, capability))
    return True if key is None else p.can(key)


def cell_for(protocol: str, device: str, capability: str, reference: str = "pm3") -> tuple:
    """Which (protocol, source, reader) answers this capability."""
    if capability == "read":
        return (protocol, "t55.pm3", "rd.%s" % _rd(device))
    src = ("t55.%s" if capability == "write" else "emu.%s") % device
    return (protocol, src, "rd.%s" % _rd(reference))


def _rd(device: str) -> str:
    return "flip" if device == "flipper" else device


def check_reference(found: dict) -> list:
    """Is the Proxmark actually the right yardstick? ⛔ VERIFIED, NOT ASSERTED.

    Returns every (protocol, source) where some other reader decoded what `rd.pm3` did not. Empty
    means the reference holds. A non-empty result means a column of this grid is understating a
    device, and the operator asked the question directly: "unless there are any examples where the
    proxmark cannot read it, but another device can".
    """
    by: dict = {}
    for (proto, src, rdr), k in found.items():
        by.setdefault((proto, src), {})[rdr] = k.verdict
    out = []
    for (proto, src), readers in sorted(by.items()):
        ref = readers.get("rd.pm3")
        if ref in (None, "EXACT"):
            continue
        better = [r for r, v in readers.items()
                  if r != "rd.pm3" and v == "EXACT" and not _same_device(r, src)]
        if better:
            out.append((proto, src, ref, tuple(sorted(better))))
    return out


def _same_device(reader: str, source: str) -> bool:
    """⚠ `cu1` READING `cu2` IS NOT A COUNTEREXAMPLE and the operator excluded it by name. Two
    Chameleons on the same firmware are one implementation talking to itself, so one decoding the
    other says nothing about whether the emission is good by any independent standard."""
    fam = {"rd.cu1": "cu", "rd.cu2": "cu", "rd.pm3": "pm3", "rd.flip": "flip"}
    return fam.get(reader) == fam.get("rd." + source.split(".", 1)[-1])


def assess(found: dict, protocols, devices=DEVICES, reference: str = "pm3",
           refused=None) -> dict:
    """(protocol, device, capability) -> Verdict, from an amalgamated `state.gather` result."""
    out = {}
    for p in protocols:
        for d in devices:
            for cap in CAPABILITIES:
                out[(p.key, d, cap)] = _one(found, p, d, cap, reference, refused or {}, devices)
    return out


def _one(found: dict, p, device: str, capability: str, reference: str, refused,
         devices=DEVICES) -> Verdict:
    if not has_arm(p, device, capability):
        return Verdict(capability, "none")
    ref = reference
    # ⛔ A DEVICE MAY NOT JUDGE ITSELF. For the Proxmark's own write and emulate, fall through to
    # whatever other reader has an answer — and name it, because a verdict reached by a different
    # instrument is a different claim and the reader of the grid is entitled to know.
    if device == reference and capability in ("write", "emulate"):
        # ⛔ ONLY READERS THAT ARE ACTUALLY HERE. Searching a fixed list meant a cell counted as
        # answerable because a Chameleon 2 in a drawer was not refused it, so the genuine
        # unanswerable cases never appeared and four irrelevant ones did.
        tried = []
        for alt in [d for d in devices if d != reference]:
            key = cell_for(p.key, device, capability, alt)
            k = found.get(key)
            if k:
                return Verdict(capability, k.verdict, key, via="rd.%s" % _rd(alt))
            tried.append(key)
        # ⛔ THE BLOCKED CHECK BELONGS ON THIS BRANCH TOO, AND WAS ONLY ON THE OTHER. The Proxmark's
        # own emulation is exactly where it bites: `emu.pm3 -> rd.cu1` is refused for every
        # subcarrier protocol (RULES.md §2) and `emu.pm3 -> rd.pm3` is self-judging, so indala,
        # gallagher, securakey, noralsy, gproxii and indala224 are UNANSWERABLE without a Flipper.
        # Reported as plain "not measured", they read as an afternoon's work that does not exist.
        # ⚠ EVERY ATTACHED READER COUNTS, INCLUDING THE FLIPPER. An earlier version skipped
        # `rd.flip` here — a leftover from when the candidate list was fixed rather than taken from
        # the bench — so a cell stayed "blocked" with the very device that answers it plugged in.
        return Verdict(capability, "unmeasured", tried[0] if tried else (),
                       blocked=bool(tried) and all(t in refused for t in tried))
    key = cell_for(p.key, device, capability, ref)
    k = found.get(key)
    if k:
        return Verdict(capability, k.verdict, key)
    return Verdict(capability, "unmeasured", key, blocked=key in refused)


NAME = {"pm3": "Proxmark", "cu1": "Chameleon 1", "cu2": "Chameleon 2", "flipper": "Flipper"}


def render(verdicts: dict, protocols, now: dict, devices=DEVICES, mismatches=()) -> str:
    """Protocols down, three columns per device. One table, which is the whole point."""
    live = [d for d in devices if any(v.state not in ("unmeasured", "none")
                                      for (_, dd, _), v in verdicts.items() if dd == d)]
    w = max(len(p.key) for p in protocols)
    head = ["# Device capability — what each device can do with each protocol", "",
            "⭐ **Three questions per device**, from the amalgamated record of every run whose "
            "readings are still about the devices attached now.", "",
            "| | means |", "|---|---|",
            "| **read** | decodes a Proxmark-written gold tag (`t55.pm3 → rd.D`) |",
            "| **write** | puts the credential on a T5577 that another device reads back "
            "(`t55.D → rd.pm3`) |",
            "| **emul** | emits it well enough for another device to decode (`emu.D → rd.pm3`) |",
            "",
            "⛔ **The Proxmark is the reference reader for write and emulate** — it is the one "
            "device licensed by a byte-exact gold row for every protocol here. That choice is "
            "checked against the record, not asserted: see below. The Proxmark cannot judge its "
            "own write or emulation, so those two cells are answered by another reader and say "
            "which.", ""]
    if mismatches:
        head += ["⛔⛔ **THE REFERENCE DOES NOT HOLD.** Another reader decoded something `rd.pm3` "
                 "did not, so the Proxmark is understating these and the columns built on it are "
                 "too short:", ""]
        for proto, src, was, better in mismatches:
            head.append("- `%s` from `%s` — `rd.pm3` says %s, %s say EXACT"
                        % (proto, src, was, ", ".join("`%s`" % b for b in better)))
        head.append("")
    else:
        head += ["✓ Reference checked: no reader has ever decoded a source `rd.pm3` called silent "
                 "(excluding one Chameleon hearing the other, which is one implementation talking "
                 "to itself).", ""]
    head.append("legend  " + "   ".join(
        "%s %s" % (GLYPH[k], v) for k, v in
        (("EXACT", "works"), ("WRONG", "wrong value"), ("SILENT", "not decoded"),
         ("DISPUTED", "readings disagree"), ("none", "no such command in this firmware"),
         ("unmeasured", "not measured"))))
    head.append("")

    cols = [(d, c) for d in live for c in CAPABILITIES]
    head.append("| %-*s | %s |" % (w, "protocol",
                                   " | ".join("%s·%s" % (d, {"read": "rd", "write": "wr",
                                                             "emulate": "emu"}[c])
                                              for d, c in cols)))
    head.append("|" + "|".join(["-" * (w + 2)] + ["-" * 11] * len(cols)) + "|")
    for p in protocols:
        row = ["%-9s" % GLYPH[verdicts[(p.key, d, c)].state] for d, c in cols]
        head.append("| %-*s | %s |" % (w, p.key, " | ".join(row)))
    head.append("")

    # ⛔ "NOT MEASURED" IS NOT ONE THING, AND THE USEFUL HALF WAS INVISIBLE. Some of these are
    # simply undone; others cannot be done with the readers to hand, because a rule refuses the
    # only reference available — `emu.pm3 -> rd.cu1` is refused for every subcarrier protocol
    # (RULES.md §2), so the Proxmark's indala emulation is unmeasurable until a Flipper is on the
    # bench. Printing both as `▫` sends somebody to a bench that cannot answer the question.
    # ⚠ ONLY ABOUT DEVICES THAT ARE HERE. A cell needing a Chameleon 2 that is in a drawer is not
    # "blocked by a rule", it is simply about a device this grid does not cover — and listing it
    # alongside the genuine cases buried them.
    stuck = sorted({(k[0], k[1], v.capability) for k, v in verdicts.items()
                    if v.state == "unmeasured" and v.blocked and k[1] in live})
    if stuck:
        head += ["⚠ **Cannot be measured with the devices currently attached** — a rule refuses the "
                 "only reference reader available, not the cell itself. A third device on the "
                 "bench answers these:", "",
                 "  " + "; ".join("`%s` %s·%s" % (p, d, c) for p, d, c in stuck[:14])
                 + (" …" if len(stuck) > 14 else ""), ""]

    via = sorted({(k[0], v.capability, v.via) for k, v in verdicts.items() if v.via})
    if via:
        head += ["⚠ The Proxmark's own write and emulate were judged by another reader:", "",
                 "  " + "; ".join("`%s` %s via `%s`" % x for x in via[:10])
                 + (" …" if len(via) > 10 else ""), ""]

    head += ["## devices", "", "| device | firmware |", "|---|---|"]
    for d, fw in sorted(now.items()):
        head.append("| `%s` | %s |" % (d, fw))
    head.append("")
    return "\n".join(head)
