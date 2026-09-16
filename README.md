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

Eleven of them, in [RULES.md](RULES.md). They are enforced in code, not left to discipline. The first
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

⚠ The tag sits **between** the devices that read it. A Chameleon or a Flipper reaches a tag from one
face only, so a stack holding a tag serves at most two active devices — `CU1 ─ T55 ─ CU2`, never
`T55 ─ CU1 ─ CU2`, where the second Chameleon would be working through the first.

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
./runtests                         # 167 tests, no hardware, no network
```

### Setup: which device is on which port

```bash
./bench setup
```

The Proxmark and the Flipper name themselves in their USB product strings. **The Chameleons do
not** — two of them enumerate as anonymous serial numbers, and nothing in that string says which is
the one labelled 1 on the bench. Crossing them is easy, silent, and poisons a whole run: every arm
attributed to the wrong device and the wrong firmware build.

⛔ **The radio identity check cannot save you from this.** It arms `cu1` with a unique id and asks a
reader who is there — but `cu1` means *whatever port the command went to*. Crossed ports make it
confirm the lie. Three questions, three answers:

| question | answered by | when |
|---|---|---|
| which device is **this**? | you, by eye, while it blinks | once, ever |
| is this the device the command was **addressed to**? | `hw chipid`, riding along with the command | **every action** |
| is that device the one in the **stack**? | the radio identity probe | every setup |

Setup makes one device visibly busy with a burst of LF reads and asks which one blinked. The LEDs
are the out-of-band channel: every other way of asking runs through the same USB mapping we are
trying to establish, and so cannot check it.

⭐ **After that the port stops mattering.** A label is bound to its chip id, not its cable:

- the port in `.env` is a **cache**, tried first for speed;
- if it holds the wrong device, or nothing, the bus is rescanned and the label follows its silicon.
  Replug, use a different hub, plug them in the other order — it costs a couple of seconds;
- and every Chameleon command carries `hw chipid` with it, so a device swapped **mid-run** is caught
  at the exact action it would have corrupted, not at the next startup.

That last point is the one that matters. `cu.py` runs a list of commands in one session with one
connect, so the check costs an extra command on an already-open link rather than another process —
which is what makes it affordable on every action. And the failure it guards against is silent by
construction: the wrong Chameleon answers confidently, with no error and no wrong exit code.

`.env` is gitignored and loaded automatically; an explicit environment variable always wins over it.

### The first session, in order

Each step is a superset of the one before, so a failure tells you which step introduced it.

```bash
./bench setup                                       # once: which Chameleon is which
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

**Ctrl-C is safe at any point.** The run stops, every device goes back to reader mode, and the
readings taken so far are filed as `run_<session>_ABORTED.md` — clearly marked, never as a grid.

## How it is built

```
bench                 the CLI — setup | probe | scope | plan | run | learn | build | flash
benchmatrix/
  outcomes.py         the four outcomes, the Calibration licence, and screening
  registry.py         the 16 tier-0 protocols, with each value's provenance marked
  stations.py         devices, sources, readers, stacks, and the computed move cues
  plan.py             cells, refusals, station set-cover, routines, and the isolation phase
  identity.py         the radio-identity check and the A/B/A null sweeps
  runner.py           the campaign: setups, controls, routines, voiding
  devices.py          pm3 / Flipper / Chameleon channels, and a scripted stand-in
  cues.py             spoken operator cues
  setup.py            device discovery, chip-id identity, and `.env`
  firmware.py         build and flash orchestration, driven by firmware.toml
  dfu.py              Nordic DFU: trigger and program in one process
  learned.py          expectations learned from a real tag, and the self-licensing guard
  grid.py             the published grid, the exclusion list, the gap register
tests/                167 tests, all on the scripted bench — `./runtests`
```

## The protocol registry

One entry per protocol, holding everything needed to test it from every side — `pm3.write`,
`pm3.read`, `cu.read`, `cu.write`, `cu.emulate`, `flip.key`, the byte-exact `expect`, the
modulation family and the subcarrier flag.

⛔ **Every capability is optional, because the firmware's are.** Assuming every protocol can be
emulated, read and written by every device is false in four directions: `fdxa`/`paradox`/`pyramid`
are read and cloned with no emitter, `instafob` is scan-only, `em410x_electra` is emulated and
written with no scan command, and `fdxa`/`instafob` have no Proxmark clone signature to make a gold
tag with. A `None` is a **fact about the firmware**, and the planner refuses the cells it makes
impossible with that fact as the reason — a different published statement from a cell that was
measured and failed. `./bench scope` prints the three capability columns.

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

## Building and flashing

`bench build` and `bench flash` make this a general tooling resource rather than only a matrix
runner. What to build, what environment it needs, which artifacts prove it worked and how to get
them onto a device are all in [`firmware.toml`](firmware.toml) — adding another firmware project is
a section there, not a code change.

```bash
./bench build chameleon-ultra                  # host toolchain, env supplied from the config
./bench build chameleon-ultra --docker         # the project's own image instead
./bench flash chameleon-ultra                  # every device the target configures
./bench flash chameleon-ultra -d cu1           # just one
```

The same discipline as the rest of the harness, because flashing fails the same way measuring does —
the tool returns cheerfully and nothing says whether it worked:

- **The artifacts decide, not the exit code.** `build.sh` ends with a `mergehex` step that produces
  the SWD artifact and fails harmlessly *after* the DFU zips are written; judging by exit status
  would throw away a good build. Each artifact must exist **and be newer than the build started** —
  a tool returning zero having produced nothing is not rare either.
- **Trigger and program are one process.** The bootloader window is shorter than the gap between two
  shell commands. Trigger in one and flash in the next, and the device has already fallen back to
  the application: `nrfutil` emits nothing, exits clean, and the version afterwards is the old
  build. That is a race, and by output alone it is indistinguishable from success.
- **Quiet output is not success.** Captured non-interactively `nrfutil` prints only an unrelated
  JLink warning — exactly what a flash that never happened prints. `--json` gives a record per
  progress step, and an explicit success record is what is required.
- **One named device.** The stock tool takes the first port matching the Chameleon's USB id, which
  with two units on the bench is a coin toss on enumeration order. This takes a port, refuses
  anything else, and refuses outright if something is already in DFU — a bootloader scan cannot then
  say which unit it found.
- **The device that comes back must be the one that went in.** Chip id is read before and after.
- **A version string is not a functional check.** It is recorded before and after and compared, and
  when it has not changed the tool says plainly that this does *not* confirm the flash — a version
  string cannot tell two builds apart when the tree was dirty. The functional check is the matrix.

⚠ The flash always runs on the host, even when the build ran in Docker: Docker Desktop on macOS
passes no USB through.

The DFU flow is a port of `enterdfu.py` by Matthew Carroll, from the ChameleonUltra project
(`research/indala-psk-read/enterdfu.py`), as is the build recipe in `firmware.toml`. It lives here
rather than being called there so that this repository does not depend on one project's research
directory — see the header of [`dfu.py`](benchmatrix/dfu.py) for what was carried over and what this
version adds.

## Provenance

Every run records what each device reported at proof of life, and publishes it with the grid —
firmware for each device, the Proxmark's client version alongside its firmware, and the harness's
own commit. The two Chameleons run different builds on purpose, so a cell is a claim about a
firmware and not about a device in general.

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
