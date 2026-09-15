# Design — the bench matrix and the harness

## 1. The matrix

For each protocol P, a cell is `(SOURCE, READER) → outcome`.

**Sources** (what is emitting):

| id | what | notes |
|---|---|---|
| `t55.pm3` | real T5577, written by the Proxmark | the gold reference |
| `t55.flip` | real T5577, written by the Flipper | differs from `t55.pm3` — see §4 |
| `emu.flip` | Flipper emulating | an independent emulator, i.e. a second opinion on our own |
| `emu.cu1` | Chameleon #1 emulating | older build `v2.2.0-861-g1866718` |
| `emu.cu2` | Chameleon #2 emulating | current build `v2.2.0-875-g02fc2e2` |
| `oem` | a genuine OEM credential | only where one is owned |

**Readers** (what is judging):

| id | what | command shape |
|---|---|---|
| `rd.pm3` | Proxmark3 | `lf <proto> reader`, plus `lf search` as a secondary |
| `rd.flip` | Flipper | `lfrfid read`, plus `raw_read` for waveform work |
| `rd.cu` | Chameleon reader mode | the arm under test, when it has one |

**Outcomes** — exactly four, no free text:

- `EXACT` — decoded, byte-identical to what was armed/written
- `WRONG` — decoded, but not what was armed (a real and important result; never merge with silence)
- `SILENT` — no decode
- `UNGRADED` — **the calibration row for this (P, READER) is missing or failed.** The harness emits
  this, not the operator. A cell that would otherwise read `SILENT` reads `UNGRADED` instead.

## 2. The calibration rule, mechanically

For every reader R and protocol P in a run:

1. The run plan **must** contain a real-tag row `(t55.pm3, R)` for P (or `oem` where a T5577 cannot
   hold P).
2. That row must be executed **in the same session, on the same pad, with the same antenna
   position** as the emulated rows it licenses.
3. If it returns anything but `EXACT`, every emulated row for that (P, R) is forced to `UNGRADED`
   and the run reports **"reader R cannot judge P on this bench"** — which is itself a finding, and
   the *only* finding that block of the run is allowed to produce.

This is the direct fix for C473 and it is the reason this harness exists rather than another shell
script. It must be impossible to obtain a scored grid without the calibration rows having passed;
`--no-calibration` must not exist as a flag.

Corollary that C474 also cost us: **complementarity across different protocols is not evidence about
any single protocol.** "Reader A missed X, reader B missed Y, so each is just a decoder gap" is a
fallacy. The harness reports per-(P, R) and never aggregates across P to license a claim about one P.

## 3. Operator cues — the adaptation of `t5577_campaign.py`

The existing harness already has everything except the vocabulary:

| existing | role | what it becomes |
|---|---|---|
| `_cue` / `cue_done` / `_spoken` / `_gap_phrase` | spoken operator prompts + chime | **bench-move cues** |
| `ask` / `ask_choice` | blocking confirmation | move confirmation, with a **radio-identity check** |
| `pm3_exec` / `pm3_probe` | pm3 command channel | unchanged |
| `flip_read_command` / `autodetect_flipper` | Flipper channel | unchanged |
| `chameleon_capture` / `chameleon_read_command` | Chameleon channel | extended with emulate-arming |
| `resolve_configs` / config registry | T5577 block recipes | becomes the **protocol registry** (§5) |
| `progress_printer` / `read_avg` | ETA display | unchanged |

**Move vocabulary** — a run plan declares topologies, not individual moves, and the harness computes
the cue sequence:

```
topology PM3_ALONE      = pm3 + nothing
topology PM3_T55        = pm3 + t5577
topology PM3_CU1        = pm3 + chameleon1
topology PM3_CU2        = pm3 + chameleon2
topology PM3_FLIP       = pm3 + flipper
topology FLIP_T55       = flipper + t5577
topology FLIP_CU1       = flipper + chameleon1
topology CU1_CU2        = chameleon1 face-to-face chameleon2
```

Cues are spoken and must name the device **and** what is being removed, because the single most
expensive error of the run so far was the operator and the agent disagreeing about which Chameleon
was on the pad — and the agent guessing would have produced an unfalsifiable null.

**⛔ Every move is followed by a radio-identity check, not a question.** After `PM3_CU2`, the harness
arms a device-unique EM410X id on each Chameleon and asks the pm3 who is actually there. The
operator's word is the *plan*; the radio is the *record*. (This is how the #1/#2 mix-up was caught,
and the operator asked for exactly this: "that's why I'm confirming the exact setup each time.")

**Null sweep before and after** every topology block (M35 A/B/A): with nothing armed, every reader
must be silent. A run whose closing null sweep differs from its opening one is **void**, not
degraded.

## 4. Cross-firmware gap register

The matrix produces firmware gaps as a by-product, and they should be recorded as first-class rows
rather than as asides. Already known, all discovered accidentally:

| firmware | gap | evidence |
|---|---|---|
| Flipper | cannot **write** keri, nexwatch, idteck, gproxii to a T5577 that the pm3 writes fine | operator bench, 2026-09 |
| Flipper | can emulate Indala224 but cannot write it | operator bench |
| Proxmark | does not decode the Flipper's Indala224 emulation | operator bench |
| Proxmark | no dedicated Electra or InstaFob command | `cmdlf.c` `CommandTable[]` |
| ChameleonUltra | 10 of the Flipper's 26 protocols unimplemented | `SCOPE.md` §B |
| ChameleonUltra | FSK2a mark is a fixed 32 µs on **both** tones (`LF_FSK2A_MARK_CYCLES = 4`); a real tag is symmetric 32/32 and 40/40 | C472 |

This register is the deliverable that makes the project worth running against other firmwares: it is
where "this firmware is wrong about this protocol" accumulates with the capture that proves it.

## 5. Protocol registry

One entry per protocol, holding everything needed to test it from every side:

```
protocol pac:
  pm3.write   = lf pac clone --cn CARD0042
  pm3.read    = lf pac reader
  flip.key    = PAC/Stanley
  cu.emulate  = lf pac econfig -s {slot} --cn CARD0042
  cu.type     = PAC
  expect      = CARD0042            # byte-exact token that must appear
  family      = ask                 # ask | fsk | psk — drives the M52 rule
  t55.capable = yes
```

`family` is not decoration. **M52: never test a SAADC-family read arm against an emulation** — the
PSK/subcarrier family (indala, gallagher, securakey, noralsy, gproxii) needs a subcarrier phase-locked
to the reader's carrier, which only a real tag has. The harness must refuse `(emu.*, rd.cu)` cells
for those protocols rather than record them as failures.

## 6. Build order

1. `SCOPE.md` verification — confirm on the bench that each Tier-0 protocol has a working
   `(t55.pm3, rd.pm3)` calibration. Anything that fails here is a *bench* problem, and must be fixed
   before any emulation is graded. **This alone is worth the project**, and it is the run C473 should
   have been.
2. Protocol registry for the 16 Tier-0 arms, ported from `pm3grade.sh` + `emugrade.sh`.
3. Campaign runner: topology cues, radio-identity check, null sweeps, `UNGRADED` enforcement.
4. Full Tier-0 matrix. Publish the grid.
5. Gap register populated from (4), with captures attached.
6. Tier 1 (3 variant protocols), then Tier 2 (5 new ones).

## 7. Relationship to the Chameleon project

The Chameleon project keeps its own notes (`LOG.md` append-only, `FINDINGS.md`, `METHOD.md`, and the
new `STATE.md`). What moves here is **the grid and the instrument**, not the reasoning. When this
harness produces a verdict, the Chameleon project cites it by run id; it does not re-argue it.

The two-fold deliverable stays as the operator stated it: (a) firmware they can actually use, across
as many tag types as possible; (b) whatever of it upstream will take, as separate PRs, tracked. This
project serves (b) directly — an upstream maintainer can run the matrix themselves, and a gap-register
row with a capture attached is the strongest form a bug report takes.
