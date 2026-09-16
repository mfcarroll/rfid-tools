# LF protocol scope — what we should actually be testing

**Status: drafted from source on 2026-09-15. NOT yet verified on the bench.** Every "✔" below means
*the source tree has a named handler*, not *the device does it*. That distinction is the whole point
of this project; do not let it collapse.

## Sources read

| List | File | Entries |
|---|---|---|
| Flipper (Momentum) | `Momentum-Firmware/lib/lfrfid/protocols/lfrfid_protocols.c` | 26 protocols |
| Proxmark3 | `proxmark3/client/src/cmdlf.c` — `CommandTable[]` | 29 LF tag commands (+1 commented out) |
| ChameleonUltra (ours) | the 16 tier-0 arms in `benchmatrix/registry.py` | 16 arms |

## The reconciliation

⛔ **Capability is not one thing.** The first draft of this file conflated *what `pm3grade.sh`
tests* with *what the firmware implements*, and undercounted the firmware badly. Three different
questions, three different answers:

| capability | source of truth | count |
|---|---|---|
| **emulate** | `lf_tag_em.c` dispatch | **18** |
| **read / clone to T55xx** | `data_cmd.h` `*_SCAN` / `*_WRITE_TO_T55XX` | **22** |
| **currently tested** | `pm3grade.sh` `ORDER` | **16** |

### A. Emulated by the firmware — 18

`em410x` · `em410x_electra` · `hidprox` · `idteck` · `indala` · `indala224` · `ioprox` · `awid` ·
`fdxb` · `viking` · `jablotron` · `pac` · `keri` · `gallagher` · `nexwatch` · `securakey` ·
`gproxii` · `noralsy`

⭐ **Two of these are built and untested: `em410x_electra` and `indala224`.** They are not new work
at all — they are grid rows nobody has ever run. That is the cheapest item in this whole document.

### B. Read / clone but NOT emulated — 4

`fdxa` · `paradox` · `pyramid` (each has `_SCAN` **and** `_WRITE_TO_T55XX`) · `instafob` (`_SCAN`
only, no T55xx write)

⇒ For these the Chameleon can act as a *reader* and as a *cloner* but not as a *card*. That is a
distinct row shape in the matrix, not a missing protocol: `(t55.cu, rd.pm3)` is testable today even
though `(emu.cu, *)` is not. Adding an emitter for the first three is real but bounded work — the
frame builders already exist for the T55xx write path.

### C. Not present at all — 4

`EM4100/16` · `EM4100/32` (bit-rate variants of an emitter we have) · `HidGeneric` ·
`HidExGeneric` (arbitrary-length HID; our arm is H10301-only)

### D. Against the Flipper's 26

| our capability | count | of Flipper's 26 |
|---|---|---|
| emulate | 18 | **69%** |
| read or clone | 22 | **85%** |
| tested | 16 | 62% |

The Flipper set is fully accounted for: 18 emulated + 4 read-only + 4 absent = 26.

### E. Proxmark-only — 9 (+1 disabled)

`cotag` · `hitag` · `motorola` (Flexpass) · `nedap` · `pcf7931` · `presco` · `ti` · `trovan` ·
`visa2000` · *(`zx8211`, commented out)*

Four of these (`cotag`, `hitag`, `pcf7931`, `ti`) are **interactive chips with challenge/response**,
not one-way ID broadcasts. Different class of work; do not mix them into this grid. The other five
are plain ID protocols and are legitimate future scope.

Excluded deliberately: `t55xx` and `em4x05` (writable chips — *sources*, not test targets) and the
pm3 general commands (`config`, `read`, `search`, `sim*`, `sniff`, `tune`, `cmdread`, `relay`).

## Scope decision this drives

| Tier | Contents | Count | Why |
|---|---|---|---|
| **0 — regression** | the 16 tested arms | 16 | must never break; every one has two independent judges |
| **0b — FREE** | `em410x_electra`, `indala224` | 2 | **already emulated, never tested.** Grid rows, not features |
| **1 — read-side rows** | fdxa, paradox, pyramid, instafob | 4 | reader/clone paths exist; test those cells now, emitters later |
| **2 — new emitters** | fdxa, paradox, pyramid | 3 | frame builders exist from the T55xx write path |
| **3 — new protocols** | EM4100/16, EM4100/32, HidGeneric, HidExGeneric | 4 | genuinely absent |
| **4 — future** | motorola, nedap, presco, trovan, visa2000 | 5 | pm3-only, plain ID protocols |
| **5 — out of class** | cotag, hitag, pcf7931, ti, zx8211 | 5 | interactive chips |

**The honest headline: the firmware emulates 18 and we test 16, so the nearest gap is two rows of
configuration, not two features — and of the 16 we test, very few have a trustworthy verdict.** See
the ChameleonUltra project's `ASSESSMENT-BRIEF.md`.

## Research-build-only commands ⛔

`LF_RESEARCH_CMDS_ENABLED` **defaults to 0**; only this branch's `firmware/application/Makefile`
sets it to 1. These exist in our builds ONLY and cannot run against stock or upstream firmware:

`LF_EMU_DEBUG` (3037) · `LF_RADIO_DEBUG` (3038) · `LF_EMU_SEQDUMP` (3065) · `LF_EMU_SEQHOLD` (3066)
· `LF_READER_CAPTURE` · `LF_T55XX_READ_CAPTURE`

⇒ Any harness step using one must be marked research-build-only, or the cross-firmware runs this
project exists to enable will fail in a way that looks like a firmware gap. `hw emuhold` (SEQHOLD)
is **not a protocol** — it plays a synthetic square wave of alternating N-entry runs (N x 256us) to
answer the long-DC question, which C443 showed no shipping arm can ask. It belongs as an optional
instrument-qualification step, never as a grid row.

## First bench task

Tier 0 is not "done", it is *unmeasured*. Run the full SOURCE x READER matrix (`DESIGN.md`) over
tier 0 **plus tier 0b** — 18 arms, since the two free ones cost only configuration — with
calibration rows enforced. Adding anything on top of an unmeasured tier 0 would repeat C473 at
larger scale.
