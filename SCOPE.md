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

### A. Three-way intersection — our current 16 arms

Our grid is *exactly* the set both reference tools speak. That is not a coincidence and it is not a
plan; it is where the arms landed by accident.

`em410x` · `viking` · `jablotron` · `pac` · `hidprox (H10301)` · `ioprox (XSF)` · `awid` · `indala (26)`
· `keri` · `nexwatch` · `idteck` · `gallagher` · `securakey` · `noralsy` · `gproxii` · `fdxb`

### B. Flipper has it, we don't — 10 protocols

These are the immediate scope gap. All ten have at least one reference decoder on this bench, so
every one of them is testable *today* with no new tooling.

| Flipper protocol | pm3 equivalent | Notes |
|---|---|---|
| `EM4100/16` | `lf em 410x` (clock variant) | bit-rate variant of a protocol we already emit |
| `EM4100/32` | `lf em 410x` (clock variant) | same |
| `Electra` | — no dedicated pm3 command | EM4100-family variant; pm3 coverage unconfirmed |
| `Indala224` | `lf indala` | we emit Indala26 only |
| `Paradox` | `lf paradox` | full pm3 support |
| `Pyramid` | `lf pyramid` | full pm3 support |
| `FDX-A` | `lf destron` | pm3 names it Destron |
| `HidGeneric` | `lf hid` (raw/arbitrary length) | generalises our H10301-only arm |
| `HidExGeneric` | `lf hid` (raw/arbitrary length) | same |
| `InstaFob` | — no dedicated pm3 command | pm3 coverage unconfirmed |

**⇒ Flipper total = 16 + 10 = 26.** Our coverage of the Flipper's set is **16/26 (62%)**.

Three of the ten (`EM4100/16`, `EM4100/32`, `Indala224`) are *variants of modulation we already
produce*. If the underlying emitters are sound, they are close to free. The other seven are new work.

### C. Proxmark has it, neither Flipper nor we do — 9 (+1 disabled)

`cotag` · `hitag` · `motorola` (Flexpass) · `nedap` · `pcf7931` · `presco` · `ti` · `trovan` ·
`visa2000` · *(`zx8211`, commented out in the pm3 table)*

Several of these are **chips with their own protocol and challenge/response** (`hitag`, `pcf7931`,
`ti`, `cotag`), not simple one-way LF ID broadcasts. They are a different class of work from
everything in A and B and should not be mixed into the same grid. `motorola`, `nedap`, `presco`,
`trovan`, `visa2000` are plain ID protocols and are legitimate future scope.

Excluded deliberately: `t55xx` (a writable chip, not a protocol — it is a *source*, not a test
target) and the general commands (`config`, `read`, `search`, `sim*`, `sniff`, `tune`, `cmdread`,
`relay`).

### D. Chameleon-only

None. There is nothing we attempt that neither reference tool can judge — which is the one piece of
good news in this table, because it means **every arm we have is gradeable against an independent
judge**, and the uncalibrated-grid failure was therefore entirely avoidable.

## Scope decision this drives

| Tier | Contents | Count | Why |
|---|---|---|---|
| **0 — regression** | the current 16 arms | 16 | must never break; every one has two judges |
| **1 — cheap adds** | EM4100/16, EM4100/32, Indala224 | 3 | variants of emitters we already have |
| **2 — real adds** | Paradox, Pyramid, FDX-A, HidGeneric, HidExGeneric | 5 | pm3 decodes all five; new emitter work |
| **3 — unconfirmed** | Electra, InstaFob | 2 | need a pm3-side judge identified first |
| **4 — future** | motorola, nedap, presco, trovan, visa2000 | 5 | pm3-only, plain ID protocols |
| **5 — out of class** | cotag, hitag, pcf7931, ti, zx8211 | 5 | interactive chips, not broadcast protocols |

**The honest headline: the target is 26, we attempt 16, and of those 16 we currently have a
trustworthy verdict on very few.** That is what the matrix is for.

## First bench task

Tier 0 is not "done", it is *unmeasured*. Before adding a single protocol, run the full
SOURCE × READER matrix (`README.md`) over the 16 tier-0 arms with calibration rows enforced. Adding
tier-1 arms on top of an unmeasured tier 0 would repeat the calibration failure at larger scale.
