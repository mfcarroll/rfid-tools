"""`bench` — plan, run, learn, scope.

⛔ THERE IS NO `--no-calibration`, NO `--force`, AND NO `--assume`. It must be impossible to obtain
a scored grid without the calibration rows having passed (RULES.md §1). An option to skip the
control is the same defect with a friendlier name, so the argument parser below does not have one,
and `Calibration` cannot be constructed without a passing row even if someone added one.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import os as _os
import sys

from . import (cues, firmware, grid, learned, outcomes, plan as planning, registry as reg,
               runner, setup, ui)
from . import devices as devices_mod
from .devices import (DEFAULT_PM3, Chameleon, DeviceError, Flipper, Pm3, obedient_operator,
                      scripted_bench)
from .stations import CU1, CU2, FLIPPER, PM3, T5577, Bench, READERS, SOURCES, build_station

RUNS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "runs"))

#: ⭐ THE DEFAULT IS THE WHOLE CROSS-PRODUCT, because the station planner collapses it into a
#: handful of arrangements. Asking for less does not save the operator much and leaves holes.
DEFAULT_SOURCES = ["t55.pm3", "t55.cu1", "t55.cu2", "emu.cu1", "emu.cu2"]
DEFAULT_READERS = ["rd.pm3", "rd.cu1", "rd.cu2"]

#: ⭐ EVERY READER, because the command is no longer Flipper-only and defaulting to one of four
#: would leave the other three to be filled in by hand — which is what it used to do, and how a
#: hand-edited `fdxb` entry came to carry two faults that hid each other. `rd.cu2` is left out:
#: `cu_expect` is shared with `rd.cu1`, so learning it twice records the same value against a
#: second device and teaches the grid nothing (see `learned.FIELD_FOR`).
DEFAULT_LEARN_READERS = ["rd.pm3", "rd.cu1", "rd.flip"]


def _learn_device(a, reader: str):
    """The channel for one reader id. ⚠ A LEARNING STATION HAS EXACTLY ONE READER IN IT besides the
    Proxmark, so this returns one device rather than the whole bench.

    ⛔ THROUGH `_chameleons`, NOT A LOCAL SHORTCUT. This used to read `CU1_PORT` out of the
    environment and build a Chameleon with no `expect_chipid`, so the identity check that guards
    every run was simply absent from the one place where getting the device wrong is PERMANENT —
    the wrong Chameleon's rendering recorded as this one's expectation, and every later run graded
    against it.
    """
    if reader == "rd.flip":
        return Flipper(port=getattr(a, "flipper_port", None) or "")
    label = READERS[reader]
    got = _chameleons(a).get(label)
    if got is None:
        raise SystemExit("  ⛔ no port for %s. Run `bench setup`, or set %s_PORT."
                         % (label, label.upper()))
    return got


def _bench(a) -> Bench:
    has = {PM3, T5577, CU1}
    if not a.no_cu2:
        has.add(CU2)
    if not a.no_flipper:
        has.add(FLIPPER)
    return Bench(has=frozenset(has), max_stack=a.max_stack, has_oem=frozenset(a.oem or ()),
                 pad=a.pad, tag_count=a.tags)


def _protocols(a, session: str):
    protos = reg.resolve(a.protocol)
    records = learned.load(a.learned)
    protos, notes = learned.apply(protos, records, session)
    return protos, notes


def _devices(a) -> runner.Devices:
    if a.dry_run:
        return _scripted(a)
    d = runner.Devices()
    d.pm3 = Pm3(binary=a.pm3)
    if not a.no_flipper:
        d.flipper = Flipper(port=a.flipper_port or "",
                            attempts=max(1, getattr(a, "flip_attempts", 6)))
    for label, chameleon in _chameleons(a, skip=("cu2",) if a.no_cu2 else ()).items():
        setattr(d, label, chameleon)
    return d


def _chameleons(a, skip=()) -> dict:
    """Build the Chameleons this bench has, resolved by chip id.

    ⭐ PORTS ARE RESOLVED BY CHIP ID, NOT READ OUT OF A FILE. The cached port is a hint; if a cable
    has moved since it was written, the bus is rescanned and the label follows its silicon.

    ⛔⛔ AND `expect_chipid` IS WHY THIS IS SHARED RATHER THAN WRITTEN TWICE. `bench learn` built its
    own Chameleon without one, so nothing checked that its commands reached the device they were
    addressed to — and it printed exactly that warning on a real learning session. A run
    misattributing a device loses one grid; a LEARNING session misattributing one records Chameleon
    2's rendering as Chameleon 1's expectation and every later run is graded against it. `cu.py`
    already carries a scar from a correctly flashed device being graded through its neighbour twice.
    """
    known = {k: v for k, v in os.environ.items() if k.startswith(("CU1_", "CU2_"))}
    for label, flag in (("cu1", getattr(a, "cu1_port", None)), ("cu2", getattr(a, "cu2_port", None))):
        if flag:
            known["%s_PORT" % label.upper()] = flag
    resolved = setup.resolve_chameleons(known) if any(k.endswith("_CHIPID") for k in known) else {}
    out = {}
    for label, name in (("cu1", CU1), ("cu2", CU2)):
        port = resolved.get(label) or known.get("%s_PORT" % label.upper())
        if port and label not in skip:
            out[label] = Chameleon(port=port, name=name, id="rd.%s" % label,
                                   slot=getattr(a, "slot", 8),
                                   expect_chipid=known.get("%s_CHIPID" % label.upper(), ""))
    return out


def _scripted(a) -> runner.Devices:
    """⚠ A DRY RUN REHEARSES THE MOVE SCRIPT AND THE CONTROLS, WITH THE RADIO REPLACED BY A DICT.

    It walks every move, takes every null sweep and every identity check, and puts the whole licence
    flow through its paces — which is what makes it worth running before a bench session, because
    the eleven-move script and the tag-carrying trips are the expensive part to get wrong.

    ⛔ IT IS NOT A SIMULATOR AND ITS GRID IS NOT A RESULT. Every read is answered from `Air`, which
    knows only that an armed emitter on the reader's pad is audible. The grid it prints says the
    control logic works, and says NOTHING about any protocol.
    """
    kw, air = scripted_bench(flipper=not a.no_flipper, cu2=not a.no_cu2)
    d = runner.Devices(**kw)
    d.operator = obedient_operator(air)
    return d


# ------------------------------------------------------------------ commands

def cmd_scope(a) -> int:
    """What the registry holds, and — the part that matters — what each protocol can and cannot do.

    ⛔ CAPABILITY IS NOT ONE THING. The first version of this project's scope document counted our
    firmware's capability off a TEST SCRIPT's arm list and undercounted it badly: the firmware
    emulates 18 where the script tested 16. Emulate, scan and T55xx-write are three different
    questions with three different answers, so this prints three columns.
    """
    reg.validate()
    protos = reg.resolve(a.protocol) if a.protocol else [reg.ALL[k] for k in reg.ORDER]
    print("\n  registry — %d protocols (%d tier 0, %d tier 1)\n"
          % (len(protos), sum(1 for p in protos if p.tier == 0),
             sum(1 for p in protos if p.tier == 1)))
    print("  %-15s %-3s %-3s %-4s %-5s %-4s %-13s %s"
          % ("protocol", "emu", "rd", "wr", "sub", "tier", "cu type", "expectations known"))
    print("  " + "-" * 86)
    for p in protos:
        known = []
        if p.expect:
            known.append("pm3")
        if p.cu_expect:
            known.append("cu")
        if p.flip_expect:
            known.append("flip")
        print("  %-15s %-3s %-3s %-4s %-5s %-4d %-13s %s"
              % (p.key,
                 "✓" if p.can("emulate") else "·",
                 "✓" if p.can("cu_read") else "·",
                 "✓" if p.can("cu_write") else "·",
                 "✋" if p.subcarrier else "",
                 p.tier, p.cu_type, ", ".join(known) or "— none; `bench learn` them"))
    emu = sum(1 for p in protos if p.can("emulate"))
    rd = sum(1 for p in protos if p.can("cu_read"))
    wr = sum(1 for p in protos if p.can("cu_write"))
    print("\n  emulate %d · scan %d · write-to-T55xx %d — three questions, three answers."
          % (emu, rd, wr))
    print("  %d refuse `(emu.*, rd.cu*)` under the subcarrier rule (RULES.md §2)."
          % sum(1 for p in protos if p.subcarrier))
    print("  %d have no emitter at all: reader and cloner rows only, which is a row SHAPE and not "
          "a gap." % sum(1 for p in protos if not p.can("emulate")))
    research = [p.key for p in protos if p.research_only]
    if research:
        print("  ⛔ research-build-only (LF_RESEARCH_CMDS_ENABLED): %s" % ", ".join(research))
    return 0


def cmd_plan(a) -> int:
    reg.validate()
    session = a.session or runner.session_id()
    protos, notes = _protocols(a, session)
    p = planning.build(protos, a.source, a.reader, _bench(a), cross=getattr(a, "cross", False),
                       at=getattr(a, "at", None) or ())
    for n in notes:
        print("  %s" % n)
    print("\n  %d cells · %d stations · %d operator interventions · %d refused at plan time"
          % (len(p.cells), len(p.blocks), p.interventions, len(p.exclusions)))
    print("\n  station script:")
    for i, (move, block) in enumerate(p.moves(), 1):
        print("   %2d. %-14s %s" % (i, block.station.name, move.text()))
        kinds = {}
        for o in block.ops:
            kinds[o.kind] = kinds.get(o.kind, 0) + 1
        print("        %d ops (%s) over %d protocols → %d cells"
              % (len(block.ops), ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items())),
                 len(block.protocols), len(block.cells)))
        crowded = sum(1 for o in block.ops if o.kind == "read" and o.crowded)
        if crowded:
            print("        %d of those reads are crowded — a failure there is screened, not a "
                  "verdict" % crowded)
    print("\n   * = calibration row. Every (protocol, reader) pair above has one; the plan is "
          "refused at build time if any does not.")
    if p.exclusions:
        print("\n  refused at plan time:")
        by_rule: dict[str, int] = {}
        for e in p.exclusions:
            by_rule[e.rule] = by_rule.get(e.rule, 0) + 1
        for rule, n in sorted(by_rule.items()):
            why = next(e.why for e in p.exclusions if e.rule == rule)
            print("    %-18s %3d  %s" % (rule, n, why[:88]))
    bad = p.audit()
    print("\n  audit: %s" % ("; ".join(bad) if bad else "clean"))
    return 1 if bad else 0


def _carry_forward(a, plan, devices, session, protos):
    """Drop the stations an earlier run already completed, and keep its readings.

    ⭐ THE STATION IS THE UNIT, AND IT ALREADY WAS. Each one takes a null sweep before and after and
    voids itself if they disagree (RULES.md §3), so a station that finished cleanly carries its own
    proof that nothing was emitting around it. A USB dropout at station 3 cost two complete stations
    — 97 byte-exact readings and 49 licences — and none of that data was wrong.

    ⛔ IT IS NOT A CACHE OF "ALREADY VERIFIED". Firmware, pad and harness commit must all match, or
    the earlier reading is a claim about a different instrument and is refused. See `resume.py`.
    """
    from . import resume
    try:
        earlier = resume.load(a.resume)
    except resume.ResumeRefused as e:
        print("  ⛔ %s" % e)
        raise SystemExit(2)
    firmware = {}
    for dev in devices.all():
        ok, why = dev.alive()
        print("  %s %s" % ("✓" if ok else "⛔", why))
        if not ok:
            raise SystemExit(2)
        firmware[runner.firmware_key(dev)] = dev.reported
    note = resume.harness_note(earlier, runner._harness_version())
    if note:
        print("  ⚠ %s" % note)
    bad = resume.check(earlier, firmware, a.pad, runner._harness_version())
    if bad:
        print("\n  ⛔ cannot carry %s forward, and these are not warnings:" % earlier.session)
        for why in bad:
            print("     · %s" % why)
        print("\n     Run without --resume to measure it again.")
        raise SystemExit(2)
    cells, licences, moved = resume.rebuild(earlier, protos, session)
    done = set(earlier.stations)
    keep = [b for b in plan.blocks if b.station.name not in done]
    print("\n  ⟲ carrying %d station(s) forward from %s: %s"
          % (len(done), earlier.session, ", ".join(sorted(done))))
    print("     %d reading(s) and %d licence(s) re-graded from their stored evidence under this "
          "harness." % (len(cells), len(licences)))
    if moved:
        # ⛔ NOTHING SHOULD MOVE. `check` already refused a differing harness commit, so an outcome
        # that changes anyway means something neither the firmware nor the commit accounted for.
        print("     ⛔ %d carried reading(s) DO NOT re-grade the same way. Not carrying anything "
              "forward — this is a finding about the harness, not a detail:" % len(moved))
        for line in moved[:8]:
            print("        · %s" % line)
        raise SystemExit(2)
    print("     %d of this plan's %d stations remain." % (len(keep), len(plan.blocks)))
    plan.blocks = keep
    return plan, earlier, cells, licences


def cmd_run(a) -> int:
    reg.validate()
    session = a.session or runner.session_id()
    protos, notes = _protocols(a, session)
    for n in notes:
        print("  %s" % n)
    p = planning.build(protos, a.source, a.reader, _bench(a), cross=getattr(a, "cross", False),
                       at=getattr(a, "at", None) or ())
    devices = _devices(a)
    carried_cells, carried_lic, earlier = [], {}, None
    if getattr(a, "resume", None):
        p, earlier, carried_cells, carried_lic = _carry_forward(a, p, devices, session, protos)
    try:
        result = runner.run(p, devices, interactive=not a.no_prompt, session=session,
                            licences=dict(carried_lic))
    except runner.RunAborted as e:
        print("\n  ⛔ ABORTED — %s\n" % e)
        print("     No grid is published from an aborted run.")
        # ⚠ THE PARTIAL RECORD IS STILL WRITTEN, under a name that cannot be mistaken for a grid.
        # Losing forty completed readings because the forty-first could not be trusted helps nobody,
        # and the operator needs to see how far the session got before deciding what to redo.
        if e.result is not None and e.result.cells:
            stem = _write(e.result, protos, suffix="_ABORTED")
            print("     %d reading(s) taken before the abort are filed at %s.md" 
                  % (len(e.result.cells), stem))
        cues.cue_done("run aborted.", ok=False)
        return 2
    # ⭐ THE CARRIED READINGS JOIN THE GRID BEFORE PHASE 2 DECIDES ANYTHING, because a screened
    # cell from this session may be licensed by a gold row carried from the last one — and because
    # a cell measured today always wins over the same cell carried forward.
    if carried_cells:
        taken = {(c.protocol, c.source, c.reader) for c in result.cells}
        result.cells = list(result.cells) + [
            c for c in carried_cells if (c.protocol, c.source, c.reader) not in taken]
        result.carried_from = earlier.session

    # ⛔ PHASE 2 IS PART OF THE RUN, NOT AN EXTRA. Phase 1 buys its coverage by stacking, and the
    # crowded-stack rule means the bill comes due on whatever failed. Leaving those cells UNGRADED
    # and calling the run finished would publish the crowding as a result.
    if result.to_isolate and not result.aborted:
        print("\n  %d cell(s) were screened non-EXACT in a crowded stack and are not verdicts."
              % len(result.to_isolate))
        p2 = planning.isolate(result.to_isolate, _bench(a))
        print("  Isolating them takes %d station(s) and %d operator intervention(s)%s."
              % (len(p2.blocks), p2.interventions,
                 "" if a.tags > 1 else " — more tags would cut that"))
        if a.no_isolate:
            print("  --no-isolate given: they stay UNGRADED and the grid says so.")
        else:
            r2 = runner.run(p2, _devices(a), interactive=not a.no_prompt, session=session,
                            licences=result.licences)
            result = grid.merge(result, r2)
    md = grid.render(result, protos)
    stem = _write(result, protos)
    print("\n" + md)
    print("\n  written: %s.md  %s.json" % (stem, stem))
    graded = sum(1 for c in result.cells if c.outcome.value != "UNGRADED")
    cues.cue_done("run complete. %d of %d cells graded." % (graded, len(result.cells)),
                  ok=not result.void_blocks, partial=graded < len(result.cells))
    return 0


def cmd_build(a) -> int:
    """Build a firmware target, and judge it by what it produced."""
    targets = firmware.load()
    if a.target not in targets:
        print("  ⛔ unknown target %r. Known: %s" % (a.target, ", ".join(sorted(targets))))
        return 2
    res = firmware.build(targets[a.target], docker=a.docker)
    if res.ok:
        print("\n  ✓ %s built. Flash it with:  ./bench flash %s --device cu1"
              % (res.target, res.target))
        return 0
    print("\n  ⛔ %s did not produce fresh artifacts.%s"
          % (res.target, (" " + res.note) if res.note else ""))
    print("     Nothing was flashed and nothing stale was left behind to mistake for a build.")
    return 2


def cmd_flash(a) -> int:
    """Flash one or more named devices, recording everything that could say whether it took."""
    targets = firmware.load()
    if a.target not in targets:
        print("  ⛔ unknown target %r. Known: %s" % (a.target, ", ".join(sorted(targets))))
        return 2
    target = targets[a.target]
    wanted = a.device or list(target.flash.get("devices") or [])
    if not wanted:
        print("  ⛔ no devices named, and the target configures none.")
        return 2

    known = {k: v for k, v in os.environ.items() if k.startswith(("CU1_", "CU2_"))}
    resolved = setup.resolve_chameleons(known) if any(k.endswith("_CHIPID") for k in known) else {}
    plan_lines, jobs = [], []
    for name in wanted:
        port = resolved.get(name) or known.get("%s_PORT" % name.upper())
        if not port:
            print("  ⛔ no port for %s — run `./bench setup` first." % name)
            return 2
        jobs.append((name, port, known.get("%s_CHIPID" % name.upper(), "")))
        plan_lines.append("    %-4s %s%s" % (name, port,
                                             "  chip %s" % known.get("%s_CHIPID" % name.upper(), "")
                                             if known.get("%s_CHIPID" % name.upper()) else ""))

    artifact = a.artifact or target.artifact()
    print("\n  flashing %s" % artifact)
    print("  onto:")
    print("\n".join(plan_lines))
    if not a.yes:
        # ⚠ Firmware is not a reversible change, and the device cannot be asked afterwards which
        # build it USED to have. Confirm before, not after.
        if cues.ask_choice("\n  proceed? [y/N] ", "yn", "n",
                           spoken="flash %d device%s?" % (len(jobs),
                                                          "" if len(jobs) == 1 else "s")) != "y":
            print("  nothing flashed.")
            return 1

    failed = []
    for name, port, chipid in jobs:
        print("\n  ── %s on %s ──" % (name, port))
        try:
            res = firmware.flash(target, port, name, artifact=artifact, expect_chipid=chipid)
        except firmware.FirmwareError as e:
            print("    ⛔ %s" % e)
            failed.append(name)
            continue
        if not res.ok:
            failed.append(name)
    cues.cue_done("flashing complete." if not failed else "flashing failed.", ok=not failed)
    if failed:
        print("\n  ⛔ did not complete for: %s" % ", ".join(failed))
        return 2
    print("\n  ⚠ A VERSION STRING IS NOT A FUNCTIONAL CHECK. Confirm the build behaves, with:")
    print("     ./bench run -s t55.pm3 -s t55.cu1 -r rd.pm3 -r rd.cu1 --no-flipper")
    return 0


def cmd_setup(a) -> int:
    """Find the devices, establish which Chameleon is which, and write `.env`."""
    known = setup.load_env()
    ports = setup.serial_ports()
    if not ports:
        print("  ⛔ no USB serial devices found. Is anything plugged in?")
        return 2
    flip, pm3_ports, rest = setup.classify(ports)
    print("\n  %d serial device(s):" % len(ports))
    for p in ports:
        tag = ("Flipper" if p in flip else "Proxmark" if p in pm3_ports else "unidentified")
        print("    %-42s %s" % (p, tag))

    values = dict(known)
    values["PM3"] = setup.find_pm3(known.get("PM3"))
    print("\n  pm3 wrapper: %s%s" % (values["PM3"],
                                      "" if os.path.isfile(values["PM3"]) else "   ⛔ NOT FOUND"))
    if flip:
        values["FLIPPER_PORT"] = flip[0]
        print("  Flipper:     %s" % flip[0])
    else:
        values.pop("FLIPPER_PORT", None)
        print("  Flipper:     not connected — runs will need --no-flipper")

    # ⛔ THE PROXMARK NAMES ITSELF AND THE CHAMELEONS DO NOT. Everything unidentified gets asked.
    print("\n  identifying Chameleons (%d candidate port(s))" % len(rest))
    found = setup.identify_chameleons(rest, known)
    if not found:
        print("\n  ⛔ no Chameleon was identified. Nothing written.")
        return 2
    for label in ("cu1", "cu2"):
        if found.get(label):
            values["%s_PORT" % label.upper()] = found[label]
            values["%s_CHIPID" % label.upper()] = found[label + "_chipid"]
        elif not any(k.startswith(label.upper()) for k in known):
            values.pop("%s_PORT" % label.upper(), None)
            values.pop("%s_CHIPID" % label.upper(), None)

    setup.write_env(values)
    print("\n  written %s:" % setup.ENV_PATH)
    for k in ("PM3", "CU1_PORT", "CU1_CHIPID", "CU2_PORT", "CU2_CHIPID", "FLIPPER_PORT"):
        if values.get(k):
            print("    %-13s %s" % (k, values[k]))
    print("\n  ⭐ The chip ids are the point: a port can change between sessions, the silicon "
          "cannot.\n     `bench run` refuses to start if a port holds a device other than the one "
          "recorded\n     here, which is the one failure the radio identity check cannot catch.")
    print("\n  next: ./bench probe")
    return 0


def cmd_probe(a) -> int:
    """Ask every channel for proof of life and stop. Touches no tag, arms nothing, writes nothing.

    ⭐ RUN THIS FIRST, EVERY SESSION. A dead port discovered forty reads into a routine costs the
    whole routine; discovered here it costs nothing. It is also the one command that is safe to run
    with anything at all on the bench, because it only asks each device to name itself.
    """
    devices = _devices(a)
    ok = True
    for dev in devices.all():
        alive, why = dev.alive()
        ok = ok and alive
        print("  %s %s" % ("✓" if alive else "⛔", why))
    if ok:
        print("\n  every channel answered. `bench run` can measure with these.")
    else:
        print("\n  ⛔ at least one channel is not fit to measure with. A silent reader and a silent\n"
              "     emitter produce identical numbers (RULES.md §5), so nothing is run until this\n"
              "     is fixed.")
    return 0 if ok else 2


def _write(result, protos, suffix: str = "") -> str:
    """File a run's markdown and JSON. Returns the path stem."""
    os.makedirs(RUNS, exist_ok=True)
    stem = os.path.join(RUNS, "run_%s%s" % (result.session, suffix))
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(grid.render(result, protos) + "\n")
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        fh.write(grid.to_json(result, protos) + "\n")
    return stem


def _why_not_learnable(p, reader: str) -> str | None:
    """Can this reader be asked about this protocol at all? ⛔ REFUSE IT, DO NOT CRASH ON IT.

    ⚠ `em410x_electra` HAS NO CHAMELEON SCAN COMMAND — the firmware emulates and clones it and
    cannot read it, which is a fact about the firmware and one of the row shapes SCOPE.md §B exists
    to record. Asking the Chameleon to learn it raised a `DeviceError` out of the middle of a
    station, after the tag had been wiped and written. `plan.py` refuses impossible cells by naming
    the firmware fact; so does this.
    """
    if not p.pm3_write:
        return ("the Proxmark has no clone command for %s, so there is no gold tag to learn from"
                % p.key)
    if reader in ("rd.cu1", "rd.cu2") and not p.cu_read:
        return "no Chameleon read command is registered for %s" % p.key
    if reader in ("rd.cu1", "rd.cu2") and not p.cu_decode_marker:
        return ("no Chameleon decode marker for %s, so a value could not be told apart from noise"
                % p.key)
    if reader == "rd.pm3" and not (p.pm3_read and p.pm3_decode_marker):
        return "the Proxmark has no read command or decode marker for %s" % p.key
    return None


def _decoded(p, reader: str, text: str, obs) -> bool:
    """Did the reader actually produce a credential? Per reader, because the Flipper is anchored."""
    if reader == "rd.flip":
        return learned.observed_value(text, p.flip_key) is not None
    return bool(obs.marker_fired)


def _isolated_retry(a, p, reader, dev, bench, write_station):
    """Take the bystander out of the stack and ask again (RULES.md §7).

    ⛔ THE PROXMARK IS A BYSTANDER DURING THE READ. It has to be in the stack to make the gold tag,
    and then it sits under that tag loading it while another device tries to read. A silence there
    says nothing about the reader, and recording it as "does not decode" manufactures a firmware gap
    out of a bench topology.

    ⭐ THE TAG DOES NOT MOVE — the Proxmark does. It is a pure removal, so the cue is "take out the
    Proxmark" rather than a description of a rig the operator can already see, and the credential
    stays exactly where it was written.
    """
    read_station = build_station({READERS[reader], T5577}, bench)
    print("      %s nothing decoded — and the Proxmark is in the stack, loading the tag. That is "
          "not a verdict about %s (RULES.md §7)." % (ui.mark("screen"), reader))
    _cue_station(read_station, bench, frm=write_station)
    done = ui.working(print, "%s reads it again, isolated" % reader)
    try:
        text, obs, proposals = _learn_read(dev, p, reader)
    except DeviceError as e:
        print("      ⛔ %s" % e)
        text, obs, proposals = None, None, None
    else:
        done("      %s %s answered" % (ui.mark("ok"), reader))
        odd = list(getattr(dev, "last_unrecognised", []))
        if not _decoded(p, reader, text, obs) and odd:
            # ⛔⛔ THE READER ANSWERED AND WE DID NOT UNDERSTAND IT. That is OUR gap, and recording
            # it as the reader's is the single mistake this harness has made over and over: the
            # anchored `^name HEX$` pattern is an assumption about output shape, and a protocol
            # that renders differently produces no match. `fdxb` was written up as a Flipper FDX-B
            # gap against a firmware that reads FDX-B fine and prints it as `ISO FDX-B` with the id
            # on its own line. A null is only evidence with a positive control (F05) — and lines we
            # cannot account for ARE the control, pointing the other way.
            print("      ⛔ %s PRINTED SOMETHING THIS HARNESS DOES NOT RECOGNISE. Nothing is "
                  "recorded and this is NOT a finding about %s — the registry's `flip_key` or the "
                  "anchored success pattern does not match what this reader prints:" % (reader, p.key))
            for line in odd[:8]:
                print("          said      %s" % line[:110])
            return None, None, None
        if not _decoded(p, reader, text, obs):
            # ⛔⛔ SCOPED TO THE SOURCE, BECAUSE THE UNSCOPED CLAIM IS FALSE. "The Flipper does not
            # decode fdxb" was what this used to say — and the Flipper then wrote an FDX-B tag from
            # its own template and read it straight back, with the Proxmark confirming the tag is
            # valid FDX-B. What was actually measured is that it produced nothing from the
            # PROXMARK's frame, which is an interop finding and not a capability gap.
            print("      · still nothing with the stack cleared. %s decodes nothing from the "
                  "t55.pm3 frame of %s — a finding about THAT FRAME, and it is entitled to be one."
                  % (reader, p.key))
            print("      ⚠ it is NOT a claim that %s cannot decode %s. Write one from another "
                  "source and ask again before putting that in the gap register."
                  % (reader, p.key))
            text = None
    # ⚠ THE WRITER GOES BACK, because the next protocol needs a wipe and a fresh gold write.
    _cue_station(write_station, bench, frm=read_station)
    return text, obs, proposals


def _cue_station(station, bench, frm=None) -> None:
    """⚠ THE SAME WORDING A RUN USES, from the same function. Taking the Proxmark out of a stack is
    "take out the Proxmark", not a re-description of the two things that did not move."""
    print("")
    for line in ui.diagram([station], sorted(bench.devices - station.devices)):
        print(line)
    print("")
    cues.ask("     press Enter when the bench looks like that: ",
             spoken=ui.spoken_move(frm, station))


def _learn_read(dev, p, reader):
    """Read with one device and turn the text into (observation, proposals)."""
    text = dev.read(p)
    obs = outcomes.observe(p.key, "t55.pm3", reader, text, "", dev.decode_marker(p))
    return text, obs, learned.candidates(None, text)


def _confirm_value(p, reader, text, obs, proposals, interactive) -> str | None:
    """Show what the device said, propose the expectation, and let the operator settle it.

    ⛔⛔ THE OPERATOR CONFIRMS, ALWAYS. Every extractor trusted to choose on its own has eventually
    chosen wrong and made it permanent — `fdxb` was registered with the T5577 BLOCK IMAGE as its
    Proxmark expectation, which is a real value printed by a real device and simply not the one that
    reader compares against. It then reported SILENT on every read for as long as it existed. The
    machine proposes; a person with the bench in front of them decides.
    """
    said = learned.value_lines(text)
    print("      the device said:")
    for line in said[:12]:
        print("        %s" % line[:110])
    if not said:
        # ⚠ AN EMPTY SECTION READS AS A BROKEN TOOL. Nothing at all is a result about the reader,
        # and it is a different result from "it printed something the marker did not match".
        print("        (nothing at all — not even a banner)")
    if not obs.marker_fired:
        # ⚠ NOT A VALUE TO RECORD EITHER WAY: an expectation taken from output the decode marker
        # did not match would license a reader that never decoded anything.
        print("      ⛔ the decode marker for %s did not fire. Either this reader does not decode "
              "%s from a real tag, or the marker is wrong, or the Proxmark in the stack is loading "
              "the tag (RULES.md §7). Not recording." % (reader, p.key))
        return None
    if not proposals:
        print("      ⛔ nothing in that output looks like a credential. Not recording.")
        return None
    print("      proposals, best first:")
    for i, c in enumerate(proposals[:9], 1):
        print("        %d. %r" % (i, c))
    if not interactive:
        print("      · --no-prompt: taking 1")
        return proposals[0]
    print("        s. skip this one")
    choice = cues.ask_choice(
        "      which does %s expect for %s? [1-%d / s / or type a value] "
        % (reader, p.key, min(9, len(proposals))),
        choices="123456789s", default="1",
        spoken="which value for %s" % p.key)
    if choice == "s":
        return None
    return proposals[int(choice) - 1]


def cmd_learn(a) -> int:
    """Write a credential with the Proxmark, read it back, and record what each reader printed.

    ⛔ THE TAG IS WRITTEN BY THE PROXMARK EVERY TIME. Learning from an emulation would record what
    our own emitter produces, which is the thing under test — the expectation has to come from the
    gold reference or it is not an expectation, it is a restatement.

    ⭐⭐ ONE OPERATOR INTERVENTION PER READER, NOT TWO PER PROTOCOL. This used to cue "put the tag on
    the Proxmark", write, then "now move the tag to the Flipper" — 28 interventions to learn the
    Flipper's fourteen unknowns. The reader goes in the STACK with the Proxmark and the tag between
    them, exactly as a run does it, and the whole protocol list is then hands-off. Fourteen becomes
    one. The station model was already in `build_station`; this command predated it.

    ⚠ A CONFIRMED WIPE IS WHAT MAKES THE READ ATTRIBUTABLE. The tag is wiped and `lf t55xx detect`
    says so, then written, then read: something decoding a credential out of a tag that held none a
    moment ago is the write landing (RULES.md §10). Where the Proxmark's own expectation is already
    known it must also match, which catches a clone command whose arguments disagree with it.
    """
    reg.validate()
    session = a.session or runner.session_id()
    protos = reg.resolve(a.protocol)
    bench = Bench(has=frozenset({PM3, FLIPPER, CU1, CU2, T5577}))
    readers = a.reader or [r for r in DEFAULT_LEARN_READERS]

    # ⚠ A RECORDED NON-DECODE IS ANSWERED, NOT OUTSTANDING. Without this the confirmed findings
    # are re-measured every session — two bench moves and 76 seconds apiece — and never settle.
    settled = {k for k, rec in learned.load(a.learned).items() if not rec.decoded}
    todo, refused = {}, []
    for r in readers:
        want = [p for p in protos
                if (p.expect_for(r) is None and (p.key, r) not in settled) or a.relearn]
        keep = []
        for p in want:
            why = _why_not_learnable(p, r)
            (refused.append((p.key, r, why)) if why else keep.append(p))
        if keep:
            todo[r] = keep
    if refused:
        print("\n  cannot be learned, and not a failure — the reason is a firmware fact:")
        for key, r, why in refused:
            print("    · %-15s %-8s %s" % (key, r, why))
    if not todo:
        print("\n  · every expectation asked for is already known or cannot be taken. "
              "`--relearn` to take the known ones again.")
        return 0

    print("\n  learning %d expectation(s) over %d station(s):"
          % (sum(len(ps) for ps in todo.values()), len(todo)))
    for r, ps in todo.items():
        print("    %-8s %d — %s" % (r, len(ps), ", ".join(p.key for p in ps)))
    print("\n  ⛔ These cannot license a calibration row in session %s (RULES.md §8). Learn now, "
          "grade in a later session." % session)

    pm3 = Pm3(binary=a.pm3)
    records = learned.load(a.learned)
    learned_now = 0
    for reader, wanted in todo.items():
        dev = pm3 if reader == "rd.pm3" else _learn_device(a, reader)
        for d in ([pm3] if dev is pm3 else [pm3, dev]):
            ok, why = d.alive()
            print("  %s %s" % ("✓" if ok else "⛔", why))
            if not ok:
                return 2
        station = build_station({PM3, T5577} | ({READERS[reader]} if reader != "rd.pm3" else set()),
                                bench)
        print("")
        for line in ui.diagram([station], sorted(bench.devices - station.devices)):
            print(line)
        print("")
        if not a.no_prompt:
            cues.ask("     press Enter when the bench looks like that: ",
                     spoken=ui.spoken_arrangement([station]))
        for n, p in enumerate(wanted, 1):
            print("\n    %s %s → %s  (%d of %d)"
                  % (ui.mark("write"), p.key, reader, n, len(wanted)))
            done = ui.working(print, "wiping the tag and proving it with `lf t55xx detect`")
            ok, detail = pm3.wipe_t55()
            done("      %s tag wiped — %s" % (ui.mark("wipe" if ok else "bad"), detail))
            if not ok:
                print("      ⛔ the tag was not wiped (%s). A read now cannot be attributed to the "
                      "write that follows it. Skipping." % detail)
                continue
            done = ui.working(print, "the Proxmark writes %s to the tag" % p.key)
            try:
                wrote = pm3.write_t55(p)
            except DeviceError as e:
                print("      ⛔ %s" % e)
                continue
            # ⚠ "ISSUED", NOT "WRITTEN". A T5577 does not acknowledge a write, so `Done!` says the
            # commands went out and nothing more (RULES.md §10). The read-back on the next line is
            # what makes it a fact — and it now says so out loud, because "not yet verified by
            # anything" followed by silence reads as if nothing checked.
            done("      %s write issued" % ui.mark("write"))
            if reader == "rd.pm3":
                text, obs, proposals = _learn_read(pm3, p, reader)
            else:
                # ⭐ THE PROXMARK CHECKS ITS OWN WORK FIRST where it can. A reader's rendering of a
                # credential the tag does not carry is not an expectation, it is noise recorded
                # forever.
                if p.expect:
                    done = ui.working(print, "the Proxmark reads its own write back")
                    back = pm3.read(p)
                    # ⛔⛔ ONE RETRY, AND IT IS RECORDED. This read-back failed for seven protocols
                    # in one session and for two in the next, and NOTHING reproduces it: the same
                    # three commands in a shell pass 9/9 with no gap, the same protocol through
                    # this same loop passes alone, and passes again with the preceding protocol's
                    # 76-second Flipper read in between. The operator has ruled out the stack by
                    # hand. Whatever it is, it is intermittent and it is ours.
                    #
                    # ⚠ A RETRY IS NOT A FIX AND MUST NOT LOOK LIKE ONE. It is here because losing
                    # a protocol to a one-off costs a bench session, and because "it took two
                    # tries" is DATA about an intermittency nobody can yet reproduce — so it is
                    # printed, and the cost of not noticing is a line of output rather than a
                    # silent papering-over. If retries start succeeding often, that is the finding.
                    if outcomes._flat(p.expect) not in outcomes._flat(back):
                        done("      %s nothing came back — asking once more" % ui.mark("warn"))
                        first = back
                        done = ui.working(print, "the Proxmark reads its own write back, again")
                        back = pm3.read(p)
                        if outcomes._flat(p.expect) in outcomes._flat(back):
                            done("      %s the credential IS on the tag, on the second read — the "
                                 "first read of this write returned nothing. Not a clean result; "
                                 "the write landed and something ate the first look."
                                 % ui.mark("warn"))
                            print("          first     %s"
                                  % " / ".join((first or "").strip().splitlines()[-2:])[:110])
                    if outcomes._flat(p.expect) in outcomes._flat(back):
                        done("      %s the credential is on the tag — %r"
                             % (ui.mark("ok"), p.expect))
                    else:
                        # ⛔⛔ SHOW WHAT IT SAID. This reported only that the read-back failed, which
                        # is the same fault that hid the Flipper channel for this whole session: a
                        # check that discards its evidence cannot be told apart from a check that
                        # is wrong. Three live explanations — the write did not land, the registry
                        # expectation is wrong, or something in the stack is loading the tag — and
                        # they look identical without the transcript.
                        done("      %s the Proxmark cannot read back what it just wrote"
                             % ui.mark("bad"))
                        print("          expected  %r" % p.expect)
                        said = outcomes.observe(p.key, "t55.pm3", "rd.pm3", back, p.expect,
                                                p.pm3_decode_marker).summary
                        # ⚠ AN EMPTY SUMMARY IS EXACTLY WHEN THE RAW TEXT IS NEEDED. `_summarise`
                        # keeps lines that match the expectation, the marker, or "raw" — so a
                        # client error matches none of them and prints as `device (nothing)`,
                        # which is indistinguishable from a reader that decoded nothing. That is
                        # what `(nothing)` meant on the bench: the pm3 client had not reached the
                        # device at all.
                        for line in said or (back or "").strip().splitlines()[-4:] or ["(no output)"]:
                            print("          device    %s" % line.strip()[:110])
                        # ⛔ AND WHAT THE CLONE SAID ABOUT ITSELF. `write_t55` looks for one
                        # confirmation marker and discards the transcript — but the Proxmark prints
                        # `Data written and verified` when it read the blocks back on the spot, and
                        # that single line separates "the write did not land" from "it landed and
                        # the reader cannot see it". Both look exactly like this failure without it.
                        for line in devices_mod.clone_evidence(wrote):
                            print("          clone     %s" % line[:110])
                        print("      · not learning from this tag. The write, the registry entry "
                              "and the stack are all still candidates — the lines above say which.")
                        continue
                done = ui.working(print, "%s reads it back" % reader)
                try:
                    text, obs, proposals = _learn_read(dev, p, reader)
                except DeviceError as e:
                    print("      ⛔ %s" % e)
                    continue
                done("      %s %s answered" % (ui.mark("ok"), reader))
                if not _decoded(p, reader, text, obs) and not a.no_prompt:
                    # ⛔⛔ A SILENCE FROM A CROWDED STACK IS NOT A FINDING (RULES.md §7), AND THIS
                    # COMMAND HAD NO IDEA. The gold writer has to be present to make the tag, so
                    # the reader is ALWAYS being asked through a Proxmark sitting directly under it
                    # — and that is a bystander coil, loading the tag, for the whole read.
                    #
                    # ⚠ IT IS NOT HYPOTHETICAL. The Flipper reported "does not decode" for viking,
                    # jablotron, pac and hidprox in a row, 12 failed reads each, ~50s apiece — and
                    # the operator then read the same tag on the same Flipper instantly with the
                    # Proxmark out of the stack. Four false findings, and they would have been
                    # recorded as firmware gaps.
                    #
                    # ⇒ Try the stack first because it costs nothing, and pay for an isolated
                    # reading ONLY where the stack came up empty. A reader that works stacked
                    # (the Chameleon does) never sees this; one that does not is still measured.
                    text, obs, proposals = _isolated_retry(a, p, reader, dev, bench, station)
                    if text is None:
                        # ⭐ A CONFIRMED SILENCE IS A RESULT, SO IT IS WRITTEN DOWN. Recording
                        # nothing meant the reading was retaken every session and the finding never
                        # reached anywhere it could be cited.
                        records[(p.key, reader)] = learned.negative(
                            p.key, reader, "t55.pm3", session,
                            getattr(dev, "last_transcript", "") or "")
                        learned_now += 1
                        continue
            if reader == "rd.flip":
                # ⛔ THE FLIPPER KEEPS ITS ANCHORED EXTRACTOR (RULES.md §6). Its success line has a
                # shape worth pinning to, and `flip_expect` is the bare hex that `flip_line()`
                # composes a full expectation from — not a line the operator picked.
                value = learned.observed_value(text, p.flip_key)
                if value is None:
                    # ⛔ ONLY REACHABLE WITH `--no-prompt`, where nobody can be asked to clear the
                    # stack — so it must NOT claim a finding. It said "the Flipper does not decode
                    # viking from a real tag on this bench" four times in a row about a Flipper
                    # that decodes all of them with the Proxmark out of the stack.
                    print("      · no `%s <HEX>` line. The Proxmark is in the stack loading the "
                          "tag, so this is SCREENED, not a verdict about %s (RULES.md §7) — and "
                          "--no-prompt means nobody can be asked to clear it. Re-run without it to "
                          "have the reading retaken isolated." % (p.flip_key, p.key))
                    continue
                print("      ✓ anchored `%s %s`" % (p.flip_key, value))
            else:
                value = _confirm_value(p, reader, text, obs, proposals, not a.no_prompt)
                if value is None:
                    continue
            # ⛔ THE EVIDENCE IS THE TRANSCRIPT, NOT THE FILTERED RESULT. `Flipper.read` returns
            # only anchored success lines, so recording its return value stored `Viking 001A3371`
            # as the "evidence" for `001A3371` — the value restating itself, which proves nothing
            # and cannot be re-read later to check the extraction. The Chameleon's records kept the
            # whole reply and were the better provenance by accident.
            records[(p.key, reader)] = learned.Learned(
                protocol=p.key, reader=reader, value=value, session=session, source="t55.pm3",
                when=_dt.datetime.now().isoformat(timespec="seconds"),
                evidence=(getattr(dev, "last_transcript", "") or text)[-1200:])
            learned_now += 1
            print("      ✓ %s %s expects %r" % (p.key, reader, value))
    learned.save(records, a.learned)
    print("\n  learned %d. written: %s" % (learned_now, _os.path.normpath(a.learned)))
    print("  ⛔ These cannot license a calibration row in session %s. Run the matrix in a new one."
          % session)
    return 0


# ------------------------------------------------------------------ argument parsing

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="bench",
        description="SOURCE x READER x PROTOCOL bench matrix with calibration enforced.",
        epilog="There is no --no-calibration. See RULES.md §1.")
    ap.add_argument("--quiet", action="store_true", help="no sound, no speech")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, with_plan=True):
        sp.add_argument("-p", "--protocol", action="append",
                        help="repeatable; default is all 16 tier-0 arms")
        sp.add_argument("--learned", default=learned.DEFAULT_PATH)
        sp.add_argument("--session", help="override the session stamp (normally the timestamp)")
        if with_plan:
            sp.add_argument("-s", "--source", action="append", choices=list(SOURCES),
                            help="repeatable; default %s" % " ".join(DEFAULT_SOURCES))
            sp.add_argument("-r", "--reader", action="append", choices=list(READERS),
                            help="repeatable; default %s" % " ".join(DEFAULT_READERS))
            sp.add_argument("--max-stack", type=int, default=3,
                            help="how many devices will physically stack (a bench fact, not a "
                                 "preference: more coverage per setup, more crowding)")
            sp.add_argument("--at", action="append", metavar="STATION",
                            help="the bench is ALREADY in this layout — measure what it admits and "
                                 "move nothing. Spelled as the grid prints it: `PM3+T55+CU1`. "
                                 "Repeatable. ⭐ For a rig left standing, or one shared with "
                                 "another session. ⛔ Cells this layout cannot produce are refused "
                                 "BY NAME, not dropped. ⚠ A station holding a TAG still needs the "
                                 "tag lifted out and back for its two null sweeps — only a "
                                 "tagless layout is genuinely hands-off")
            sp.add_argument("--cross", action="store_true",
                            help="also measure tag cells with the Proxmark on NEITHER side "
                                 "(t55.flip → rd.cu1 and friends). ⚠ Normally redundant: a T5577's "
                                 "state after a write is digital, so nothing of the writer survives "
                                 "into what the tag transmits, and (t55.X → rd.pm3) plus "
                                 "(t55.pm3 → rd.Y) already answer it. Worth it when one of THOSE "
                                 "fails — a second reader is how a bad writer is told from a bad "
                                 "reader. Costs 9 extra operator interventions on a full sweep")
            sp.add_argument("--tags", type=int, default=1,
                            help="T5577 tags available, which is what makes the isolation phase cheap")
            sp.add_argument("--oem", action="append", help="protocol an OEM card is owned for")
            sp.add_argument("--pad", default="pad0",
                            help="pad label stamped into every licence; change it when a reader is "
                                 "physically repositioned, which invalidates earlier licences")
            sp.add_argument("--no-cu2", action="store_true")
            sp.add_argument("--no-flipper", action="store_true")

    sp = sub.add_parser("scope", help="print the registry and what it can and cannot grade")
    sp.add_argument("-p", "--protocol", action="append")
    sp.set_defaults(func=cmd_scope)

    sp = sub.add_parser("setup", help="find the devices, learn which Chameleon is which, write .env")
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("build", help="build a firmware target from firmware.toml")
    sp.add_argument("target")
    sp.add_argument("--docker", action="store_true",
                    help="build in the project's own image instead of with the host toolchain "
                         "(the flash still runs on the host — Docker passes no USB through)")
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("flash", help="flash a built target onto named devices")
    sp.add_argument("target")
    sp.add_argument("-d", "--device", action="append",
                    help="repeatable; default is every device the target configures")
    sp.add_argument("--artifact", help="override the firmware file")
    sp.add_argument("--yes", action="store_true", help="do not ask before flashing")
    sp.set_defaults(func=cmd_flash)

    sp = sub.add_parser("probe", help="ask every channel for proof of life; touch nothing else")
    common(sp, with_plan=False)
    sp.add_argument("--pm3", default=DEFAULT_PM3)
    sp.add_argument("--cu1-port", default=os.environ.get("CU1_PORT"))
    sp.add_argument("--cu2-port", default=os.environ.get("CU2_PORT"))
    sp.add_argument("--flipper-port", default=os.environ.get("FLIPPER_PORT"))
    sp.add_argument("--slot", type=int, default=8)
    sp.add_argument("--no-cu2", action="store_true")
    sp.add_argument("--no-flipper", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_probe)

    sp = sub.add_parser("plan", help="expand a request into cells, moves and refusals; run nothing")
    common(sp)
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("run", help="execute the matrix")
    common(sp)
    sp.add_argument("--pm3", default=DEFAULT_PM3)
    sp.add_argument("--cu1-port", default=os.environ.get("CU1_PORT"))
    sp.add_argument("--cu2-port", default=os.environ.get("CU2_PORT"))
    sp.add_argument("--flipper-port", default=os.environ.get("FLIPPER_PORT"))
    sp.add_argument("--flip-attempts", type=int, default=6,
                    help="tries per Flipper front end before giving up (default 6). ⚠ ONLY A MISS "
                         "COSTS THIS — a decode returns on the first hit, in about two seconds. A "
                         "miss runs BOTH front ends to exhaustion at ~6s a try, so 6 is ~76s and 3 "
                         "is ~38s. Across a full matrix that is the difference between minutes and "
                         "hours. Lower trades a longer tail of false silences — which the "
                         "crowded-stack rule then sends to isolation — for wall-clock")
    sp.add_argument("--slot", type=int, default=8, help="scratch slot, so nothing curated is lost")
    sp.add_argument("--no-prompt", action="store_true",
                    help="speak the moves but do not block on Enter (for a watched run)")
    sp.add_argument("--resume", metavar="RUN",
                    help="carry the completed stations of an earlier run forward and measure only "
                         "what is left. ⭐ A station takes a null sweep before and after and voids "
                         "itself if they disagree, so one that finished cleanly is a self-contained "
                         "measurement. ⛔ NOT a cache of what passed: the firmware on every device, "
                         "the pad and the harness commit must all match, or the earlier readings "
                         "are claims about a different instrument and it refuses")
    sp.add_argument("--no-isolate", action="store_true",
                    help="stop after phase 1; screened cells stay UNGRADED rather than being "
                         "re-measured in isolation")
    sp.add_argument("--dry-run", action="store_true",
                    help="exercise the control logic with no hardware; every cell will be UNGRADED")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("learn",
                        help="learn what a reader prints for a Proxmark-written tag, and record "
                             "it with the transcript that produced it")
    common(sp, with_plan=False)
    sp.add_argument("-r", "--reader", action="append", choices=list(READERS),
                    help="repeatable; default %s. `rd.cu2` shares `cu_expect` with `rd.cu1`, so "
                         "learning both records the same value twice"
                         % " ".join(DEFAULT_LEARN_READERS))
    sp.add_argument("--pm3", default=DEFAULT_PM3)
    sp.add_argument("--flipper-port", default=os.environ.get("FLIPPER_PORT"))
    sp.add_argument("--relearn", action="store_true", help="re-learn values the registry already has")
    sp.add_argument("--no-prompt", action="store_true",
                    help="no operator prompts: take the best proposal for every reading. ⚠ The "
                         "confirmation is the control on an automatic extractor — use it for a "
                         "bench you are watching, not for one you have walked away from")
    sp.set_defaults(func=cmd_learn)
    return ap


def main(argv=None) -> int:
    # ⚠ `.env` FILLS THE GAPS AND NEVER OVERRIDES. An explicit `CU1_PORT=... ./bench run` must win,
    # or the override does the opposite of what it looks like.
    setup.apply_env()
    a = build_parser().parse_args(argv)
    if a.quiet:
        cues.silence()
    for attr, default in (("source", DEFAULT_SOURCES), ("reader", DEFAULT_READERS)):
        if hasattr(a, attr) and getattr(a, attr) is None:
            setattr(a, attr, list(default))
    try:
        return a.func(a)
    except KeyboardInterrupt:
        # ⛔ STOPPING A RUN IS A NORMAL THING TO DO. Hands full, something wrong on the bench, a cue
        # that turned out to be for the wrong station — none of that deserves a traceback, and the
        # devices have already been put back to idle by the runner's own cleanup.
        cues.hush()
        print("\n\n  ⛔ interrupted. Every device has been put back into reader mode, so the bench "
              "is idle.\n     Nothing is emulating and no grid was published.\n", file=sys.stderr)
        return 130
    except (reg.RegistryError, ValueError, AssertionError) as e:
        print("\n  ⛔ %s\n" % e, file=sys.stderr)
        return 2
    except DeviceError as e:
        print("\n  ⛔ %s\n" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
