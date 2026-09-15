# rfid-tools

A bench-test harness and protocol-capability database that lives **outside** any one firmware
project. It is not part of the ChameleonUltra work and not part of the T5577 work; both of those
are *subjects* it tests, alongside the Proxmark3 and the Flipper.

## Why this exists

Three separate failures in the ChameleonUltra `indala-psk-read` run had the same root cause, and
none of them were protocol bugs:

1. **C378 / C431** — a capability grid built from one judge (the Flipper). Every "fail" cell was
   really "this judge did not speak up", and we could not tell a broken emitter from a deaf reader.
2. **C473 (retracted by C474)** — seven protocols graded silent on the Proxmark with **no
   calibration row**, then written up as a positive conclusion. The operator refuted it from their
   own bench in minutes: the Proxmark reads Indala, KERI, IDTECK and FDX-B perfectly well from a
   real tag and from a *Flipper* emulation. The silence was ours.
3. The **Flipper's own write gaps** (keri, nexwatch, idteck, gproxii won't write to a T5577 that the
   pm3 writes fine; Indala224 emulates but won't write) were discovered by accident, in passing,
   while chasing an unrelated question.

All three are the same shape: **a single device was used as both the instrument and the thing being
measured, and nothing in the process refused to produce a verdict when the controls were missing.**

This project's job is to make that structurally impossible, and — as a side effect of doing so —
to become the place where cross-firmware protocol gaps are recorded.

## The one rule the harness enforces in code

> **A reader's silence about a source means NOTHING until that reader has decoded the SAME PROTOCOL
> from a known-good source on the same pad in the same session.**
>
> No calibration row ⇒ **no verdict**. Not a weaker verdict — the harness prints `UNGRADED` and
> refuses to score the cell.

`pm3grade.sh` in the Chameleon tree is the counter-example: it scores every arm byte-exact and will
happily print a full-marks grid built entirely on uncalibrated silence. Its successor here must
refuse.

## What it is

- A **campaign runner** derived from `Momentum-Firmware/T5577_block0_analysis_data/t5577_campaign.py`
  (3546 lines, already drives pm3 + Flipper + Chameleon and already has spoken operator cues:
  `_cue`, `cue_done`, `ask`, `ask_choice`). The adaptation is to generalise its operator cues from
  T5577 block programming to **bench moves** — "put Chameleon 1 on the Proxmark", "move the tag to
  Chameleon 2", "separate everything" — and to make the move script a first-class part of a run
  plan, so a matrix that needs eleven physical rearrangements can be executed in one sitting
  without the operator having to hold the topology in their head.
- A **capability database**: SOURCE × READER × PROTOCOL, with provenance and a session stamp.
- A **scope register** (`SCOPE.md`): what the full LF protocol universe actually is, per firmware.

## What it is not

- Not a place for firmware changes. Findings go back to the owning project.
- Not a replacement for that project's notes. It records *what the bench observed*, not *what we
  concluded about a design*.

## How it is built

```
bench                 the CLI — scope | plan | run | learn
benchmatrix/
  outcomes.py         the four outcomes, and the Calibration licence they need
  registry.py         the 16 tier-0 protocols, with each value's provenance marked
  topology.py         sources, readers, arrangements, and the computed move cues
  plan.py             cells, plan-time refusals, and the injected calibration rows
  identity.py         the radio-identity check and the A/B/A null sweeps
  runner.py           the campaign: moves, controls, reads, voiding
  devices.py          pm3 / Flipper / Chameleon channels, and a scripted stand-in
  cues.py             spoken operator cues, ported from t5577_campaign.py
  learned.py          expectations learned from a real tag, and the self-licensing guard
  grid.py             the published grid, the exclusion list, the gap register
tests/                66 tests, all on the scripted bench — `./runtests`
```

The calibration rule is enforced by construction rather than by checking. `grade()` cannot be
called without a `Calibration`, and a `Calibration` cannot be built except by
`Calibration.from_row()`, which takes an observation and refuses it unless it is a byte-exact read
of a **real tag** for **that protocol**, on **that reader**, in **that session**, on **that pad**.
There is no bypass argument anywhere in the package, and a test walks the argument parser to prove
no flag has quietly acquired one.

## Using it

```bash
./bench scope                      # the registry, and what it can and cannot grade
./bench plan                       # the cells, the move script, and what is refused
./bench run --dry-run --no-prompt  # rehearse the whole thing with no hardware
./runtests                         # 66 tests, no hardware, no network
```

A real run needs the ports:

```bash
PM3=../proxmark3/pm3 CU1_PORT=/dev/tty.usbmodemC3A1656543DE1 \
CU2_PORT=/dev/tty.usbmodemF429364E46961 ./bench run
```

## Status

**The instrument is built; the bench run has not happened.** `DESIGN.md` §6 steps 2 and 3 —
the protocol registry and the campaign runner — are complete and tested. Steps 1, 4 and 5 need
hardware and are the next thing to do.

Three things are deliberately *not* known yet, and the harness refuses to guess at any of them:

- **Ten of sixteen protocols have no Flipper expectation.** The Flipper's decoded hex is a
  different encoding from the credential the Chameleon is armed with, and deriving it from each
  protocol's encoder would be guessing at something the bench can be asked. Those ten have no
  `rd.flip` column at all until `bench learn` fills them in from a Proxmark-written tag — and a
  value learned in one session cannot license a calibration row in that same session, because a
  control compared against itself cannot fail.
- **`rd.cu` has no column.** The Chameleon's read arms are the thing under test in the owning
  project, not a judge; no read command is registered here, so the whole column is refused with a
  reason rather than left blank.
- **Several `pm3.write` commands are not known to produce the credential the emulation arms.**
  Where `clone` takes decoded fields and `econfig` takes `--raw`, they may differ. This needs no
  special handling: it surfaces as a calibration row that decodes *something other than* `expect`,
  which is reported as a **registry fault** and not as a deaf reader.
