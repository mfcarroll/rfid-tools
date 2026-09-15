# rfid-tools

A bench-test harness and protocol-capability database that lives **outside** any one firmware
project. It is not part of the ChameleonUltra work and not part of the T5577 work; both of those
are *subjects* it tests, alongside the Proxmark3 and the Flipper.

## Why this exists

Three separate failures in an earlier LF investigation had the same root cause, and none of them
were protocol bugs:

1. A capability grid built from **one judge**. Every "fail" cell was really "this judge did not
   speak up", and a broken emitter could not be told from a deaf reader.
2. Seven protocols graded silent on the Proxmark with **no calibration row**, then written up as a
   positive conclusion. The operator refuted it from their own bench in minutes: the Proxmark reads
   Indala, KERI, IDTECK and FDX-B perfectly well from a real tag. The silence was ours.
3. The Flipper's own **write gaps** (keri, nexwatch, idteck, gproxii will not write to a T5577 the
   Proxmark writes fine) discovered by accident, in passing, while chasing something else.

All three are the same shape: **a single device was used as both the instrument and the thing being
measured, and nothing in the process refused to produce a verdict when the controls were missing.**

This project's job is to make that structurally impossible, and — as a side effect — to become the
place where cross-firmware protocol gaps are recorded.

## The rules

Nine of them, in [RULES.md](RULES.md). They are enforced in code, not left to discipline. The first
is the one the rest exist to protect:

> **A reader's silence about a source means nothing until that reader has decoded the same protocol
> from a known-good source on the same pad in the same session.**
>
> No calibration row ⇒ **no verdict**. Not a weaker verdict — the harness prints `UNGRADED` and
> refuses to score the cell.

It is enforced by type. `grade()` cannot be called without a `Calibration`; a `Calibration` cannot
be built except by `Calibration.from_row()`, which refuses anything but a byte-exact read of a
**gold source** for **that protocol**, on **that reader**, in **that session**, on **that pad**.
There is no bypass argument anywhere in the package, and a test walks the argument parser to prove
none has quietly appeared.

## The matrix

For each protocol, a cell is `(SOURCE, READER) → outcome`.

**Sources** — what is emitting:

| id | what |
|---|---|
| `t55.pm3` | real T5577, written by the Proxmark — **the gold reference** |
| `t55.flip` | real T5577, written by the Flipper — tests the Flipper's writer |
| `t55.cu1` / `t55.cu2` | real T5577, written by a Chameleon — tests our writer |
| `emu.flip` | Flipper emulating — an independent second opinion on our own emulator |
| `emu.cu1` / `emu.cu2` | a Chameleon emulating |
| `oem` | a genuine OEM credential, where one is owned |

**Readers** — what is judging: `rd.pm3`, `rd.flip`, `rd.cu1`, `rd.cu2`.

⭐ `(t55.*, rd.cu*)` — a Chameleon decoding a real T5577 — is not one column among several. An
emulation is a waveform driven onto a coil; only a tag's silicon produces genuine load modulation,
so this is the **only** measurement that says whether our decoders work on real RF. It is
simultaneously the control that licenses the column and the headline result of the run.

**Outcomes** — exactly four, no free text:

- `EXACT` — decoded, byte-identical to what was armed or written
- `WRONG` — decoded, but not what was armed. A real and important result; never merged with silence
- `SILENT` — no decode
- `UNGRADED` — the harness could not license a verdict. It emits this, not the operator

## Stations: the unit of work

The scarce resource is the operator's hands. A tag swap costs exactly as much as rearranging the
bench, so the thing to minimise is **interventions**, not abstract "moves".

A **station** is a physical arrangement set up once; a **routine** is everything measured there,
hands-off. At

    Proxmark ─ T5577 ─ Chameleon 1

one routine covers, per protocol: the Proxmark writes and reads back, the Chameleon reads what the
Proxmark wrote, the Chameleon writes, the Proxmark reads that. **Four cells a protocol, sixty-four
cells, one intervention.** The planner generates that cycle itself, from the cells you ask for.

```
  246 cells · 4 stations · 10 operator interventions      # the default matrix
  380 cells · 9 stations · 21 operator interventions      # all four readers, all seven sources
```

**The price is the crowded-stack rule.** Devices left in the stack detune and load the active coil
even when idle. A parasitic coil cannot manufacture a byte-exact decode of the credential we armed,
so a **success is a success** — but a silence or a wrong decode might be the crowding, so it is not
a verdict. It is *screened*, and queues an isolated re-measurement.

So a run has two phases. **Phase 1** buys coverage by stacking. **Phase 2** isolates whatever
failed, in stacks with no bystanders, and only phase 2 may call a cell `SILENT` or `WRONG`. More
T5577 tags make phase 2 cheaper — a batch is written at one station and read at the next — which is
the one place where swapping tags beats rearranging the bench.

## Using it

```bash
./bench scope                      # the registry, and what it can and cannot grade
./bench plan                       # the cells, the station script, and what is refused
./bench run --dry-run --no-prompt  # rehearse the whole thing with no hardware
./runtests                         # 86 tests, no hardware, no network
```

Put the ports in the environment once:

```bash
export PM3=/Users/Shared/code/personal/rfid/proxmark3/pm3
export CU1_PORT=/dev/tty.usbmodemC3A1656543DE1
export CU2_PORT=/dev/tty.usbmodemF429364E46961
export FLIPPER_PORT=/dev/tty.usbmodemflip_Matthew1
```

### The first session, in order

Each step is a superset of the one before, so a failure tells you which step introduced it.

```bash
./bench probe --no-flipper                          # proof of life. Touches nothing.
./bench run -p em410x -s t55.pm3 -r rd.pm3 --no-flipper     # 1 protocol, 1 station: the plumbing
./bench run -s t55.pm3 -r rd.pm3 --no-flipper              # THE GOLD COLUMN — all 16
./bench run -s t55.pm3 -s t55.cu1 -r rd.pm3 -r rd.cu1 --no-flipper   # the full cycle, 60 cells
```

⭐ **The third command is the one that is worth the project on its own.** `PM3+T55` holds only the
Proxmark and the tag, so nothing in it is crowded and **every cell is an isolated verdict** — no
screening, no phase 2. Anything that fails there is a *bench* problem or a registry fault, and must
be fixed before a single emulation is graded.

`--max-stack` is a bench fact, not a preference: how many devices will physically stack. More
coverage per setup, more crowding. `--tags N` only affects the isolation phase.

## How it is built

```
bench                 the CLI — scope | plan | run | learn
benchmatrix/
  outcomes.py         the four outcomes, the Calibration licence, and screening
  registry.py         the 16 tier-0 protocols, with each value's provenance marked
  stations.py         devices, sources, readers, stacks, and the computed move cues
  plan.py             cells, refusals, station set-cover, routines, and the isolation phase
  identity.py         the radio-identity check and the A/B/A null sweeps
  runner.py           the campaign: setups, controls, routines, voiding
  devices.py          pm3 / Flipper / Chameleon channels, and a scripted stand-in
  cues.py             spoken operator cues
  learned.py          expectations learned from a real tag, and the self-licensing guard
  grid.py             the published grid, the exclusion list, the gap register
tests/                86 tests, all on the scripted bench — `./runtests`
```

## The protocol registry

One entry per protocol, holding everything needed to test it from every side — `pm3.write`,
`pm3.read`, `cu.read`, `cu.write`, `cu.emulate`, `flip.key`, the byte-exact `expect`, the
modulation family and the subcarrier flag.

⛔ **Three classes of value live in there and they are not equally trustworthy.** The registry keeps
them apart and says which is which:

1. **Run on the bench** — the `cu.emulate` strings and every `expect`, inherited from scripts that
   have been executed against hardware.
2. **Read out of source** — `pm3.write`, `cu.read`, `cu.write`, `flip.key`, and the decode markers.
   The same standard as `SCOPE.md`: *the source tree says so*, not *the device does it*.
3. **Not known at all** — `flip.expect` is `None` for ten of sixteen. It is not defaulted, not
   approximated, and never matched on the protocol name alone. Those ten have no `rd.flip` column
   until `bench learn` fills them in from a Proxmark-written tag.

## Cross-firmware gap register

The matrix produces firmware gaps as a by-product, and the grid records them as first-class rows
with the evidence that proves them. This is the deliverable that makes the project worth running
against other firmwares: a maintainer can run the matrix themselves, and a gap row with a capture
attached is the strongest form a bug report takes.

⛔ Only an isolated reading may become a gap. A gap is a claim that something does **not** work, and
a crowded stack cannot support that claim.

## Status

**The instrument is built; the bench run has not happened.** The registry, the station planner, the
runner, the controls and the isolation phase are complete and tested. What remains needs hardware:

1. **Verify the gold column.** `./bench run -s t55.pm3 -r rd.pm3` confirms every tier-0 protocol has
   a working `(t55.pm3, rd.pm3)` calibration. Anything that fails there is a *bench* problem and
   must be fixed before any emulation is graded. **This alone is worth the project.**
2. **`bench learn`** the ten missing Flipper expectations, in a session of its own.
3. **The full matrix.** Publish the grid.
4. **Populate the gap register** from it, with captures attached.
5. **Scope tiers 1 and 2** — see [SCOPE.md](SCOPE.md).

Three things are deliberately *not* known yet, and the harness refuses to guess at any of them:

- **Ten of sixteen protocols have no Flipper expectation** (registry class 3 above). A value learned
  in one session cannot license a calibration row in that same session, because a control compared
  against itself cannot fail.
- **Several `pm3.write` commands are not known to produce the credential the emulation arms.** Where
  `clone` takes decoded fields and `econfig` takes `--raw`, they may differ. This needs no special
  handling: it surfaces as a calibration row that decodes *something other than* `expect`, reported
  as a **registry fault** and not as a deaf reader.
- **No LF OEM cards are owned**, so `t55.pm3` is the sole licence source for everything. That puts
  more weight on the point above.

## What it is not

- Not a place for firmware changes. Findings go back to the owning project.
- Not a replacement for that project's notes. It records *what the bench observed*, not *what we
  concluded about a design*. When this harness produces a verdict, the owning project cites it by
  run id; it does not re-argue it.
