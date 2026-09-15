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
import sys

from . import cues, grid, learned, plan as planning, registry as reg, runner
from .devices import (Chameleon, DeviceError, Flipper, Pm3, obedient_operator,
                      scripted_bench)
from .stations import CU1, CU2, FLIPPER, PM3, T5577, Bench, READERS, SOURCES

RUNS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "runs"))

#: ⭐ THE DEFAULT IS THE WHOLE CROSS-PRODUCT, because the station planner collapses it into a
#: handful of arrangements. Asking for less does not save the operator much and leaves holes.
DEFAULT_SOURCES = ["t55.pm3", "t55.cu1", "t55.cu2", "emu.cu1", "emu.cu2"]
DEFAULT_READERS = ["rd.pm3", "rd.cu1", "rd.cu2"]


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
        d.flipper = Flipper(port=a.flipper_port or "")
    d.cu1 = Chameleon(port=a.cu1_port, name=CU1, slot=a.slot) if a.cu1_port else None
    d.cu2 = Chameleon(port=a.cu2_port, name=CU2, slot=a.slot) if (a.cu2_port and not a.no_cu2) else None
    return d


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
    reg.validate()
    protos = reg.resolve(a.protocol)
    print("\n  tier-0 registry — %d protocols\n" % len(protos))
    print("  %-11s %-5s %-4s %-12s %-14s %s" % ("protocol", "fam", "sub", "cu type", "flipper key",
                                                "flipper hex"))
    print("  " + "-" * 74)
    for p in protos:
        print("  %-11s %-5s %-4s %-12s %-14s %s"
              % (p.key, p.family, "✋" if p.subcarrier else "", p.cu_type, p.flip_key,
                 p.flip_expect or "— not known, `bench learn` it"))
    known = sum(1 for p in protos if p.flip_expect)
    print("\n  %d/%d have a Flipper expectation; the other %d cannot have an `rd.flip` column."
          % (known, len(protos), len(protos) - known))
    print("  %d refuse `(emu.*, rd.cu)` under the subcarrier rule."
          % sum(1 for p in protos if p.subcarrier))
    print("  %d cannot be written to a T5577 by the Flipper (registered gap)."
          % sum(1 for p in protos if not p.flip_write))
    return 0


def cmd_plan(a) -> int:
    reg.validate()
    session = a.session or runner.session_id()
    protos, notes = _protocols(a, session)
    p = planning.build(protos, a.source, a.reader, _bench(a))
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


def cmd_run(a) -> int:
    reg.validate()
    session = a.session or runner.session_id()
    protos, notes = _protocols(a, session)
    for n in notes:
        print("  %s" % n)
    p = planning.build(protos, a.source, a.reader, _bench(a))
    devices = _devices(a)
    try:
        result = runner.run(p, devices, interactive=not a.no_prompt, session=session)
    except runner.RunAborted as e:
        print("\n  ⛔ ABORTED — %s\n" % e)
        print("     No grid is published from an aborted run.")
        return 2
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
    os.makedirs(RUNS, exist_ok=True)
    stem = os.path.join(RUNS, "run_%s" % result.session)
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    with open(stem + ".json", "w", encoding="utf-8") as fh:
        fh.write(grid.to_json(result, protos) + "\n")
    print("\n" + md)
    print("\n  written: %s.md  %s.json" % (stem, stem))
    graded = sum(1 for c in result.cells if c.outcome.value != "UNGRADED")
    cues.cue_done("run complete. %d of %d cells graded." % (graded, len(result.cells)),
                  ok=not result.void_blocks, partial=graded < len(result.cells))
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


def cmd_learn(a) -> int:
    """Write a credential with the Proxmark, read it on the Flipper, record what it printed.

    ⛔ THE TAG IS WRITTEN BY THE PROXMARK EVERY TIME. Learning from an emulation would record what
    our own emitter produces, which is the thing under test — the expectation has to come from the
    gold reference or it is not an expectation, it is a restatement.
    """
    reg.validate()
    session = a.session or runner.session_id()
    protos = reg.resolve(a.protocol)
    pm3 = Pm3(binary=a.pm3)
    flip = Flipper(port=a.flipper_port or "")
    for dev in (pm3, flip):
        ok, why = dev.alive()
        print("  %s %s" % ("✓" if ok else "⛔", why))
        if not ok:
            return 2
    records = learned.load(a.learned)
    for p in protos:
        if p.flip_expect is not None and not a.relearn:
            print("  · %-10s already known (%s)" % (p.key, p.flip_expect))
            continue
        cues.ask("\n  put the T5577 on the Proxmark, then press Enter (%s): " % p.key,
                 spoken="put the T5577 tag on the Proxmark")
        out = pm3.write_t55(p)
        if "error" in out.lower():
            print("    ⛔ write refused — %s" % out.strip()[-160:])
            continue
        verify = pm3.read(p)
        if p.expect.lower() not in verify.lower():
            print("    ⛔ the Proxmark cannot read back what it just wrote. Not learning from this "
                  "tag — the credential is not what the registry says it is.")
            continue
        cues.ask("  now move the tag to the Flipper and press Enter: ",
                 spoken="move the tag to the Flipper")
        try:
            text = flip.read(p)
        except DeviceError as e:
            print("    ⛔ %s" % e)
            continue
        value = learned.observed_value(text, p.flip_key)
        if value is None:
            print("    · the Flipper printed no `%s <HEX>` line — it does not decode %s from a real "
                  "tag on this bench. That is a FINDING, not a learning failure." % (p.flip_key, p.key))
            continue
        records[(p.key, "rd.flip")] = learned.Learned(
            protocol=p.key, reader="rd.flip", value=value, session=session, source="t55.pm3",
            when=_dt.datetime.now().isoformat(timespec="seconds"), evidence=text[:400])
        print("    ✓ %s rd.flip expects %r" % (p.key, value))
    learned.save(records, a.learned)
    print("\n  written: %s" % os.path.normpath(a.learned))
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

    sp = sub.add_parser("probe", help="ask every channel for proof of life; touch nothing else")
    common(sp, with_plan=False)
    sp.add_argument("--pm3", default=os.environ.get("PM3", "pm3"))
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
    sp.add_argument("--pm3", default=os.environ.get("PM3", "pm3"))
    sp.add_argument("--cu1-port", default=os.environ.get("CU1_PORT"))
    sp.add_argument("--cu2-port", default=os.environ.get("CU2_PORT"))
    sp.add_argument("--flipper-port", default=os.environ.get("FLIPPER_PORT"))
    sp.add_argument("--slot", type=int, default=8, help="scratch slot, so nothing curated is lost")
    sp.add_argument("--no-prompt", action="store_true",
                    help="speak the moves but do not block on Enter (for a watched run)")
    sp.add_argument("--no-isolate", action="store_true",
                    help="stop after phase 1; screened cells stay UNGRADED rather than being "
                         "re-measured in isolation")
    sp.add_argument("--dry-run", action="store_true",
                    help="exercise the control logic with no hardware; every cell will be UNGRADED")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("learn", help="learn a reader's expectation from a Proxmark-written tag")
    common(sp, with_plan=False)
    sp.add_argument("--pm3", default=os.environ.get("PM3", "pm3"))
    sp.add_argument("--flipper-port", default=os.environ.get("FLIPPER_PORT"))
    sp.add_argument("--relearn", action="store_true", help="re-learn values the registry already has")
    sp.set_defaults(func=cmd_learn)
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if a.quiet:
        cues.silence()
    for attr, default in (("source", DEFAULT_SOURCES), ("reader", DEFAULT_READERS)):
        if hasattr(a, attr) and getattr(a, attr) is None:
            setattr(a, attr, list(default))
    try:
        return a.func(a)
    except (reg.RegistryError, ValueError, AssertionError) as e:
        print("\n  ⛔ %s\n" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
