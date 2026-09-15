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

## Status

Write-up only. Nothing implemented yet. See `DESIGN.md` for the build order and `SCOPE.md` for the
first task's answer (drafted from source, **not yet verified on the bench**).
