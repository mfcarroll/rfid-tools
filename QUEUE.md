# Work queue — newest decisions at the top of each item

⛔⛔ **BENCH STATE CHANGED 2026-09-16 — cu2 WAS REFLASHED.**
`v2.2.0-920-gdf053dd` — **a committed, clean build** of this tree, carrying the `hw emuhold
--top` instrumentation (ChameleonUltra `17d65d50`). **cu1 was never touched.**
⚠ An experimental level-pattern PSK emitter was flashed on top of this during the round and
then **reverted and reflashed away** (C485) — cu2 is back on the committed build. Verify
FUNCTIONALLY, never by version string (C461): an armed Indala must show **64 entries, `seq
repeats` 15** (`hw emuseq --count 0`), and `hw emuhold -n 1 --top 8` must succeed. Both checked.
⚠ **cu1 WAS PUT INTO READER MODE** (`hw mode -r`) to read Rig A's tag for item 4. Its prior mode was **not recorded first**, so if the operator had left it emulating something, that is gone — reader mode is the safe state (an emulating Chameleon jams the pad) but the change is disclosed rather than glossed. ⛔ cu1 was never flashed.
⚠ **2026-09-16 LATE: cu2 was ARMED AND DISARMED repeatedly** (indala, keri, idteck, nexwatch,
indala224, gproxii) for C490/C491, always through a `finally`, and its mode was **verified as
`Tag Reader` at the end** by asking the device. **Nothing was flashed this round, on either unit.**

⚠ `enterdfu.py` failed to trigger twice in a row before succeeding on the third try, with
nothing flashed either time — it says so explicitly and distinguishes a trigger failure from a
flash failure. **Retry it; do not go looking for a broken device.**

## ⭐⭐⭐ 2026-09-16, LATE: THE SIX "SILENT" ARMS ARE NOT SILENT — READ THIS BEFORE ITEM 3

**Repo for the detail: `ChameleonUltra` C489-C495** — the architecture answer, the live A/B,
the cross-arm run, the beat's period, `indala224`, the n=24 rates, and `fdxb emu.pm3`.

⭐⭐ **The Proxmark reads our Indala emulation byte-exact, live, 23 of 26.** `lf indala reader`
is silent because it reads **30,000 samples** (`cmdlfindala.c:633`, 240 ms); `lf read -s 4096`
followed by `lf indala demod` returns `a0000000e6bd0e92` / Fmt 26 FC 52 Card 63612. Same session,
same field, same arm, alternated. ⛔ Controls: cu2 disarmed silent 3/3 live, a PAC capture asked
for Indala silent, the same samples at 40,000 silent, and Rig B is tagless.

⭐⭐ **And FIVE of the six arms decode through the READER COMMAND THE MATRIX GRADES ON** — at
n=24: `keri` **8/24**, `gproxii` **8/24**, `nexwatch` **6/24**, `idteck` **4/24**, against **0 of 36**
with nothing armed. ⚠ **Read those as non-zero, NOT as an ordering** (C497): the hit rate
wanders — the same arm gave **88%, 60%, 38% and 75%** in one evening — and those arms were
measured one after another. Only an INTERLEAVED run compares two of them (`METHOD.md` M59).

⭐⭐⭐ **THE ONE CROSS-ARM TABLE THAT IS METHODOLOGICALLY SOUND (C498)** — round-robin, one
capture per arm per round, n=8, so the wander moves every arm together. `./shortread.py
--interleave --repeat 8`:

| arm | its own reader | a fitted short read |
|---|---|---|
| `gproxii` | 0/8 | **8 of 8** (`-s 12288`) |
| `indala` | 0/8 | **6/8** (`-s 4096`) |
| `keri` | **3/8** | 0/8 (`-s 4096`) |
| `nexwatch` | 1/8 | 1/8 |
| `idteck` | 0/8 | 0/8 |
| `indala224` | 0/8 | 0/8 |

⛔ **SO THE RULE IS NOT "USE A SHORT READ".** `keri` is BETTER on its own 10,000-sample read
than on 4,096. Each arm has a window that works, bounded below by needing whole frames and above
by the ~61 ms fading period — `lf indala reader`'s 30,000 is far outside it, `lf keri reader`'s
10,000 is inside. ⭐ **`gproxii` is the headline**: 8 of 8 through a fitted read against 0 of 8
through its own, which is C487 confirmed live and interleaved — that arm is not marginal at all
once the read fits. Only `indala` (0/26) and `indala224` (0/24) never do. They are **intermittent,
not silent**, and a cell graded from ONE read lands on SILENT most of the time — which is exactly
what the graded run and C488's one-capture probe saw.

⭐⭐⭐ **AND THE PATTERN IS ONE NUMBER IN THE PROXMARK CLIENT (C494).** Every LF reader calls
`lf_read()` with a different count: indala **30,000**, nexwatch **20,000**, keri **10,000**, pac
**8,212**, idteck **5,000** — a 6x spread nothing documents. Against the emission's own ~61 ms
fading period, Indala's reader is the only one spanning four intervals, and it is the only arm the
short read transforms (0/26 → 23/26). The others were already short, which is why a short read
does nothing for them. ⛔ **So do not generalise "use a short read"** — it is an `indala`
(and partly `gproxii`) effect, and a length sweep on `nexwatch` shows no trend at all.

⛔ **n MATTERS HERE AND IT CAUGHT ME**: the first pass recorded `nexwatch` 0/9 and reasoned from
it; at n=24 it is 6/24. At a true rate near 1 in 3, nine trials return zero about 4% of the time.
See ChameleonUltra `METHOD.md` **M58**.

⛔⛔ **WHAT THIS DOES NOT DO.** It is ungraded — no null sweep, no calibration row, no
licence — and it **licenses no re-grade of anything**. What it licenses is `--repeat` on the
operator's return. ⛔ Do not "fix" the harness to use a short read: the registry's `pm3_read` is
what the matrix's history is graded against, and changing it silently re-bases every past cell.
That is an operator decision, and the gap register now carries the evidence for it.

⚠ **What is retracted**: C488's *the artifact is one arm wide* (both its paths read 40,000
samples), and C489's verdict that the six-gap is closed as a hardware limitation. ⭐ **What
stands**: C486's beat measurement, and C489's hardware facts — no pin on this board can see a
carrier cycle (VD1 rectifies at the coil) and the nRF52 PWM has no external clock input, so
COHERENT emulation is unreachable. It turns out coherence was not required.

⭐⭐ **`indala224` IS THE CLEANEST CONFIRMATION OF THE MECHANISM** (C493, correcting this
section's own first version). Its payload IS ours — **212, 202, 199 and 189 of 224 leading bits
byte-exact**, then the tail collapses to all-ones. A 224-bit frame is **57.3 ms** against a measured
**60.8 ms** null spacing, so it cannot finish inside one interval, and the survival times (48-54 ms)
sit just under that spacing. ⛔ The wrong-frame reading was made without looking at the payload —
see item 8.

## ⭐⭐⭐ 2026-09-16, EVENING — THE READ-LENGTH ROUND, CONSOLIDATED (C499-C504)

**Detail: `ChameleonUltra` C499, C500, C501, C502, C503, C504 and METHOD.md M60.** Six claims from
one evening, all ungraded, all on the tagless Rig B. This block replaces the 21:00 and 22:10 ones.

### What it measured

⭐⭐ **THE UNIT IS THE PROTOCOL'S OWN FRAME, NOT MILLISECONDS** (C499). A per-arm ladder of read
lengths, interleaved and shuffled, two seeds pooled to n=24, tagless null 0 hits. The control that
separates the units was already in the ladder: at **`-s 6144`** — one sample count, one duration,
one session — `indala` is **21/24** (3 frames) and `gproxii` **0/24** (1 frame). The per-arm peak
spans 49-147 ms in time and only 3-4 in frames.

⭐⭐ **THE SHAPE, WHICH REPRODUCED ACROSS TWO SESSIONS:**

| read length | what happens |
|---|---|
| **1 frame** | ⛔ fails on **every** arm — and it does not fail quietly (see precision) |
| **2-6 frames** | works; **3-4 is the best region** |
| beyond ~6 frames | declines — `lf indala reader`'s 30,000 is **14.6 frames** and scores 1/24 |

⛔⛔ **DO NOT QUOTE A SPECIFIC `-s N` PER ARM** (C504). A second session at n=20 moves the argmax
for **four of the five** arms that decode (`indala` 3f→6f, `keri` 4f→3f, `nexwatch` 4f→3f,
`gproxii` 3f→4f; only `idteck` holds at 3f). C499 read a peak off a noisy plateau. **Carry the
range, not the number.** ⭐ The two readers genuinely outside the window are `lf indala` (14.6
frames) and `lf gproxii` (1.6) — that part is solid and is C494's 6x spread explained in one unit.

⭐⭐ **PRECISION IS THE READER'S, NOT THE LENGTH'S** (C502 post-hoc, C503 and C504 with criteria
written first). Every read scores twice — **decoded** (a frame of this protocol at all) and
**exact** (it was ours) — and the gap is a credential reported confidently and wrongly:

| arm | precision above 1 frame | note |
|---|---|---|
| `idteck` | **100%** | 25/25 decodes, and **0 wrong in 24** at n=24 (C503) |
| `gproxii` | **100%** | 62 of 63; the one miss was its single 1-frame decode |
| `keri` | 98% | |
| `nexwatch` | 77% | |
| `indala` | 76% | |
| `indala224` | **0%** | ⛔ **51 decodes, none correct, at every length** |

⛔ **`indala` and `indala224` share `lf indala demod`, and it is the permissive one.** One
demodulator, not two arms.
⭐⭐ **AND AT ONE FRAME PRECISION COLLAPSES ON EVERY ARM** (`indala` 0% of 4, `indala224` 0% of 18,
`gproxii` 0% of 1, `keri` 20% of 5) ⇒ *one frame never decodes* is really ***one frame decodes and
lies***. The demodulator does not go quiet; it locks onto a partial frame and reports it.

⭐⭐ **THAT ALSO DISSOLVES THE EQUAL-GEOMETRY RESIDUAL** (C503, criterion first). `indala`, `keri`
and `idteck` share a 2048-sample frame, so one ladder compares them legitimately. **exact = decode
x precision:** `indala` **92% / 66%**, `keri` 38% / 94%, `idteck` 31% / **100%**. ⇒ **The readers
differ in strictness and that alone accounts for the spread — no difference in our emission need be
invoked.** ⚠ It removes the need for one; it cannot prove there is none.

⭐ **`indala224`** (C501): leading-bit agreement at n=46 is min 33, **median 89, max 154 of 224** —
8.4 / 22.8 / 39.4 ms — and **flat across read length**, so the cut is in the EMISSION, not the
capture. ⛔ C493's 189/199/202/212 do **not** reproduce (all four sit above all 46 of mine; its
computation is not recoverable from L461). ⭐ What stands harder: **the payload IS ours.** And the
smaller window explains the frame-length column better than 48-54 ms did — 16.4 ms frames fit
almost always, 32.8 ms sometimes, 57.3 ms never.

### ⛔⛔ The method rule this round cost, and the audit that followed

**M60 — ORDER IS A VARIABLE.** The first version of the ladder ran ascending, so every length sat
at a fixed position after the arming. It scored `lf keri reader` **2/12** against `lf read -s 10000`
+ `lf keri demod` **10/12** — and `cmdlfkeri.c:222` is `lf_read(false, 10000); demodKeri()`, the
same count through the same demodulator. **Nothing but position could differ.** Shuffled, they
agree, and `gproxii`'s zeros became 8-12/12. ⇒ **The confound was as large as the effect.**

✅ **Audited across every sweep in the tree (C500), and C469 survived by measurement.** The
discriminator is **whether the statistic was PREDICTED or read off the sweep's own shape**.
`holdsweep.py` had the same ascending order, but C469's criterion was fixed before the firmware
existed — re-run **shuffled** (order 2 7 8 5 1 9 4 3 6) every N landed on its prediction, no knee.
`gaintest`/`oversample_test`/`inputtest` are **blocked** and `phasesweep` fixes phase order within a
rep, but all of those sweep a **real T5577**, which is coherent, and score a tag/empty ratio — real
defects, **no claim known to be wrong**, and all need the operator. `offsetsweep`/`sweep`/`airduty`/
`nullframe` re-analyse a file and cannot be affected; `drivesoak` sweeps order on purpose.

### ⛔ What none of it licenses

Ungraded throughout — no null sweep, no calibration row, no licence, **moves no cell**. It licenses
a per-arm `--repeat` on the operator's return. ⛔ It does **not** license re-pointing the registry's
`pm3_read`: that silently re-bases every past cell, and C502 adds a second reason — at 3-4 frames
`indala` decodes 12/12 with **2 of those wrong**, so cells would move to **WRONG** as well as to
EXACT. ✅ **Today's SILENT grades are correct**: at each arm's own graded count the open-failing
arms barely decode at all.


## ✅ 2026-09-16 21:5x — REGRADE-VALIDATION SWEEP (hands-off, util7=75.0)

⭐ **A regrade is not a graded cell** (AUTOPILOT §1/§4) — this moved no cell and touched no device.
It re-derived every outcome in **all 16 non-aborted banked runs** under today's registry (`d09fdb6`)
with `./bench report <id> --regrade`, to validate item 6's registry corrections against the banked
evidence. This is the one measurement loop AUTOPILOT §1 endorses for an operator-absent tick.

⭐⭐ **RESULT: CLEAN. Every move is a deliberate registry correction taking effect on a
pre-correction run; nothing is a current-registry defect, and no *licensed* EXACT cell flipped to
WRONG.**

- **11 runs stable** ("no outcome moved"), including the flagship licensed run **`20260916_161528`**
  (the 11/17-EXACT tagless run) and **every** run measured since the corrections landed.
- **5 older runs move** (2026-09-15 → early 09-16), all moves `UNGRADED ↔ graded`:
  - `20260916_110740` **27 moved**, every one `UNGRADED → EXACT/SILENT` — cells the older registry
    could not license now grade, from markers/calibration added since. Strict improvement.
  - `204348` (+2), `205207` (−2), `104455_resumed` (+1), `125646` (+1) — same shape.
- ⭐ **The one divergence I chased and closed: `fdxb …→ rd.cu1` moves OPPOSITE ways in adjacent
  runs `204348` (→EXACT/WRONG) and `205207` (→UNGRADED).** Not a registry inconsistency. Both runs'
  cu1 read decoded `00339a080402079f8040`**`797788`**`040201`; today's registry raw is
  `...8040`**`3b7598`**`...040201` (`registry.py:475/477`). **The fdxb raw expectation was
  deliberately corrected** since 2026-09-15 (`registry.py:496`, `devices.py:915` "the first registry
  entry where `expect` was corrected", `learned.py:220`), so tags written with the OLD raw correctly
  regrade to WRONG/UNGRADED. The correction working as designed — ⛔ do NOT "fix" it back.
  ⚠ cu1 = Rig A now, so a fresh fdxb cu1 read is an operator item regardless.

⇒ **Nothing to commit but this record.** `./runtests` green (467), git was clean. The registry is
self-consistent with every banked run and the item-6 corrections are confirmed against the evidence.

---

## ⭐⭐ WHERE THE NEXT TICK STARTS

⭐⭐⭐ **UNIT 2 AND UNIT 4 OF THE 02:0x LIST ARE BOTH CLOSED** by the 02:4x block above — the
hump does not travel with the frame (C519/C520), and `nexwatch` is measured. ⛔ **Do not re-open
them**; the open units are the ones that block names, and the first of those is now cheap.

⭐⭐ **THE READ-LENGTH LINE IS CLOSED.** C499-C504 answered it, audited the method that nearly broke
it (M60/C500), and corrected two of its own claims (C499's best-length argmax, C493's leading-bit
magnitudes). Everything the tagless bench can say about read length has been said. ⛔ **Do not
re-measure it** — a further sweep would be C473's method: re-measuring a question already answered.

## ⭐⭐⭐⭐⭐ 2026-09-17 02:4x — THE WORKING POINT IS IN MILLISECONDS, NOT FRAMES. READ THIS FIRST.

util7 **80 → 81** (util5 24 at 02:32). ⛔ **No bench move, nothing flashed on either unit**, cu2
armed and disarmed through the `finally` and verified back in `Tag Reader`; **cu1 untouched**.
**Detail: `ChameleonUltra` C519, C520, M65, M66, `framescale.py`, `burstsync.py` K17, commits
`41dfc800` `a7de9290` `fdd31f49` `feeec8b0` `977ddd49`.**

⭐⭐⭐ **THE HEADLINE: the lead-time hump does NOT travel with the protocol's frame — it sits at
the same 55-65 ms on an arm whose frame is twice as long.** That was the round's unit 2, and it is
now answered from both ends.

| step | what it did |
|---|---|
| **C519**, offline, no device | `gproxii`'s banked K12/K13 ladders refute the frame reading — **80.6% and 78.5%** pooled at its own 2.44 frames, where the band needed <= 30%, and FLAT across 0.41-4.07 frames but for the 60 ms hole |
| **M65**, my own band's defect | ⛔ `gproxii` is the only arm with a different frame **and** the only ASK/biphase one, so C519 alone cannot separate *not frames* from *a PSK effect* |
| **C520**, one capture, tagless Rig B | ⭐ `nexwatch` breaks the confound — PSK, but a 4096-sample frame, so the two readings are **66 ms apart**. **U1 fires in both seeds: +50.8 and +45.8 points**, 4 of 5 window cells above the highest wing |

⛔⛔ **`indala` AND `keri` COULD NEVER HAVE ANSWERED THIS — THEY SHARE A 2048-SAMPLE FRAME.** Their
matching humps at the same 65 ms are what *both* hypotheses predict. Any future cross-arm question
about units has to start by asking which arms can discriminate; two of the six always can't.

⭐ **`nexwatch`'s profile, two seeds at n=8** (and this closes the old item 4 — it was the last arm
entirely unmeasured on this knob):

| lead ms | 40 | 45 | **55** | **60** | **65** | 70 | 75 | 80 | 120 | 125 | 130 | **135** | **140** | 160 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| seed 11 | 12% | 0% | **88%** | **88%** | **75%** | 25% | 0% | 0% | 12% | 12% | 0% | **62%** | **88%** | 25% |
| seed 23 | 0% | 12% | **62%** | **75%** | **88%** | 25% | 0% | 0% | 12% | 0% | 25% | **75%** | **88%** | 12% |

⭐ Both gates passed **before** any band was read: pooled 34.8% / 33.9% against a 15% no-power
floor, K16 split-half **Δ 1.8 and 3.6** against a 15-point drift ceiling, and **P1 at 0.50 arrivals
in every cell including 160 ms**, so the whole ladder sat inside one 500 ms burst.

⚠⚠ **THE SECOND BUMP AT 135-140 ms IS A LEAD, NOT A FINDING, AND THE DISTINCTION IS THE POINT.**
It reproduced in both seeds at the same two cells (62-88% against 0-25% either side) — and **the
band aimed at it did NOT fire** (+22.5 / +33.8 points, 2 of 5 on its shape clause), so by the rule
written before the capture nothing is claimed about a second working point. ⛔ Do not quote
135-140 ms as a working point; quote it as the thing the next ladder is for.

⛔⛔ **M66 IS WHY IT MISSED, AND IT IS THE FIFTH MEMBER OF M62's FAMILY.** **A pooled band over a
window presumes the feature FILLS the window.** U2 pooled five cells and the rise occupied two;
U1's rise was three cells wide and fired on a comparable magnitude. ⚠ And the window was built
from `indala`/`keri`'s **argmax** when their **range** was already known — C504's *carry the range,
not the number* applied to the peak I report but not to the window I test. ⇒ **State the window
from the known range and score a CONTIGUOUS RUN inside it**, not the whole of it.

## ⛔⛔ AND UNIT 1 WAS RUN — THE MEASUREMENT IS GOOD AND **MY BAND WAS NOT** (C521, M67)

**`indala` and `keri` measured above 80 ms for the first time** — 15 cells at 100-170 plus a 65 ms
control, two seeds each, **all four gates passing** (pooled 75.0/64.1% and 40.6/36.7%, split-half
Δ 3.1/6.2/3.1/1.6, P1 at 0.50 arrivals to 170 ms, disarmed in the `finally`).

⭐ **`keri` has a three-cell feature at 140-150 ms** — **75/88/88%** and **75/100/75%**, the SAME
cells in both seeds, against 0-38% below and 0-25% above. `indala` is high nearly everywhere up
there with a dip at 120-130 and a collapse to 0-25% at 165-170.

⛔⛔⛔ **AND K18's BAND SCORED `keri` AS *NO SECOND FEATURE HERE*.** Clause (a) came to **−3.1 and
−5.7 points**, because `keri`'s wing cells at **100 and 105 ms are 62-88%**: the ladder's EDGES sit
on another elevated region, so eleven mostly-low inner cells pooled against wings containing a peak
give a negative gap. **M67 — a wing fixed by POSITION is only safe if the position is known to be
outside the structure, and an edge is not outside anything; it is wherever the ladder stopped.**
⚠ That is M63 by a different route, **in the round that cited M63 while writing the band.**

⛔⛔ **NOTHING IS CLAIMED, AND DO NOT PROMOTE THE CONJUNCT THAT FIRED.** K18's clause (c) — the run
against the wings — came to **+29.7 (`indala`) and +44.3 (`keri`)** with runs present in both seeds
at overlapping cells. It was a conjunct of V1, and reading it as the verdict now that V1 failed is
M62 exactly. **V1 did not fire. That is the result**, and the captures are banked for a ladder that
is built right.

⚠ **POST-HOC, LABELLED, NOT A PERIOD**: `keri` 140-150, `nexwatch` 135-140, `indala` overlapping
145-160 — three arms with elevated regions inside **135-160 ms**, and all three collapse by
160-170. A lead for a wider ladder.

## ⭐⭐⭐⭐ AND THAT RE-RUN WAS DONE — K19, C522, M68

**K19 dropped designated wings entirely** (M67: a wing must be justified, and 85-90 ms is NOT —
it is one cell 5 ms from a measured low, on profiles whose features are 5-15 ms wide). The
reference is **each arm's own median across the ladder**. **85-200 ms in 5 ms steps**, 24 cells
plus a 65 ms cell excluded from the median, two seeds per arm at `--reps 8`, **all four gates
passing** and **P1 at 0.50 arrivals in every cell to a 200 ms primer** — the whole ladder inside
one 500 ms burst, which the arithmetic could only estimate (C516).

⭐⭐ **`keri`: W1 FIRES — TWO SEPARATED FEATURES, `95,100,105` and `140,145,150` ms**, each in both
seeds, separated by six cells of which two (125, 130) are quiet in both. ⛔ **Location was reported
and never tested** — W1 is a claim about COUNT and SEPARATION and nothing else.

⭐⭐ **`keri`: W2 FAILED, AND THAT IS THE RESULT WITH TEETH.** None of 185, 190, 195, 200 is at a
floor — **190 ms is 62% and 100%**. ⇒ **No wing at this ladder's top edge is licensed for any
future band**, and there is more profile above 200 ms. ⛔ Reaching it needs
`LF_TAG_BURST_TARGET_MS` raised — a firmware change and a cu2 flash — so it is an operator-return
item, not a tick's.

⛔⛔ **`indala`: W1 REFUTED, AND THE REFUTATION IS WORTHLESS — M68.** Its median is **75%**, so
*median + 25* is **100%, the ceiling**, and a feature needed two adjacent cells at exactly 100% in
both seeds. **The band could not have fired whatever the data did.** The arm visibly has structure
— 0-25% at 120-125, 12-25% at 165-175, 12-38% at 200, against a body at 75-100%.

⚠⚠ **AND THE PATTERN BEHIND M68 IS THE THING TO CARRY**: M63 said a control must not presume
flatness ⇒ K18 fixed wings by position ⇒ M67, an edge is not outside anything ⇒ K19 referenced the
arm's own median ⇒ M68, a relative threshold inherits the arm's headroom. **Three consecutive
criteria, each written to repair the last, each broken in a new place.** ⇒ **The repair is not a
better rule. It is a check run against the design before the capture** — compute the threshold
against each arm's known level and say, in advance, what the band can detect there.

⚠ **POST-HOC, LABELLED**: at these lead times `indala` looks like `gproxii` (high with holes) and
`keri` looks like `nexwatch` (low with humps). A description of four profiles, not a mechanism, and
no band tested it.

## ⭐⭐⭐⭐ AND THAT INVERSE DETECTOR WAS RUN TOO — K20, C523

**M68's own prescription, applied**: give an arm the detector its level can support, so on a
75-88% median the feature to look for is a **NOTCH**. ⛔ **The power table was computed BEFORE the
band** — the step whose absence WAS M68 — and it scoped the run by arithmetic, not by a result:
`indala`'s thresholds sit well inside its range; `keri`'s notch threshold would be **its floor**,
so K20 is `indala` only.

⭐⭐ **X1 FIRES: two notches, `115,120,125,130` and `165,170,175` ms**, each in both seeds,
separated by two cells in the body in both. Notches at **0-38%** against a body at **75-100%**.
**X2 met** — 195 ms is 100%/88%, so the profile returns and **this top edge COULD license a wing
for `indala`**, where W2 denied one for `keri`. Gates: pooled 68.5/64.0%, split-half **Δ 5.0 and
0.0**, P1 **0.50 in every cell to a 200 ms primer**.

⭐⭐⭐ **AND IT IS A REPLICATION, WHICH IS THE WHOLE OF ITS VALUE.** K19's `indala` low cells were a
post-hoc observation, so K20 ran on **fresh seeds** with the band pinned against them, and
115-130 and 165-175 come back. ⚠ The 90 and 200 ms cells are notched in both seeds but stand alone
and fail the two-cell rule — reported, not counted.

⭐ **K20 IS THE FIRST BAND IN FOUR THAT DID WHAT IT WAS BUILT TO DO**, and the reason is the one
thing that changed: **its power was computed in advance instead of discovered afterwards.**

## ⚠⚠ THE BIGGEST THING THIS ROUND FOUND IS POST-HOC AND IS THE NEXT CRITERION'S JOB

**THE TWO ARMS' STRUCTURE INTERLEAVES.** `keri` is HIGH at **95-105** and **140-150**; `indala` is
LOW at **115-130** and **165-175**. Consecutive same-type regions sit **~45-50 ms apart on both
arms**, with the arms offset from each other by ~20 ms.

⛔⛔ **NO PERIOD IS CLAIMED AND NONE MAY BE QUOTED.** It is post-hoc; **periodicity is untestable
under the 500 ms burst ceiling** (a third region would sit near 215-240 ms, and K12 saw P1 fail at
220); and **~49 ms is also 3 frames of the 2048-sample frame these two arms share**, which C520
gives no licence to invoke. ⇒ It is a shape to write a criterion FOR, not a finding.

⭐ **What IS supported and is practical**: `indala` is >= 88% at many lead times across 85-200 ms,
so **65 ms is not a unique working point** — it is the one measured to work on all three arms at
once.

⭐⭐ **THE NEXT HANDS-OFF UNITS, in order:**
1. ⭐⭐⭐ **A criterion for the interleaving.** ⛔ It must NOT be scored on `caps/k19_*` or
   `caps/k20_*` — those are the caps the shape was seen in. A fresh seed pair on both arms, same
   ladder, the band naming in advance **which cells each arm must be high and low in**.
   ⚠ Compute the power for BOTH arms first (M68): `keri` needs the forward detector and `indala`
   the inverse, so **one criterion has to carry two different detectors**, and that is new.
   ⛔ It still cannot become a periodicity claim — say so in the band.
2. ⭐⭐ **The mechanism.** Nothing proposed survives — not the beat, not settling, not the frame,
   not the modulation. ⛔ Criterion first.
3. **The 20-85 ms range at 5 ms on `indala` and `keri`** — K19 started at 85 and K14/K15/K16
   stopped at 80, so **20-40 ms has never been measured on either arm** and the two ladders only
   just meet. ⚠ `gproxii`'s notch is at 60 ms and `keri`'s new feature starts at 95, so the
   region between the two ladders is the last unmeasured gap under the burst ceiling.
4. `idteck` and `indala224` remain unmeasured on this knob. ⚠ `indala224`'s precision is 0% (C502),
   so it can only be scored on *decoded*, never on *exact*, and the band must say so.

⛔⛔⛔ **READ THIS BEFORE WRITING ANY BAND. SIX PRE-REGISTERED CRITERIA HAVE NOW MIS-FIRED IN TWO
ROUNDS** — M62 a statistic decided by one cell, M63 a control presuming the shape it polices, M64 a
criterion reading a shape off its argmax, M65 a refutation inheriting its one contrast arm's every
difference, M66 a pooled window presuming the feature fills it, M67 a wing justified by position
alone. **Every one was committed before its capture.** ⇒ Pre-registration is necessary and is
nowhere near sufficient. Ask of every band: *what single cell decides this? what does it presume
about the shape? what else differs between the arms? does the reference region have to be quiet,
and do I KNOW it is?*

⚠ **Banked**: `caps/k17_nexwatch_s11.json`, `caps/k17_nexwatch_s23.json` hold every per-round
score, and `./framescale.py --k17 <caps>` re-derives the whole verdict offline. ⭐ `framescale.py`
also re-derives C519 from K12-K16 with no device at all.

⛔⛔ **STILL LICENSES NOTHING HERE.** Ungraded — no null sweep, no calibration row — so it **moves
no cell**. A fitted lead time in the graded path re-bases every past cell exactly as re-pointing
`pm3_read` would, and remains the **operator's decision**. The gap register carries the evidence.

---


## ⭐⭐⭐⭐ 2026-09-17 02:0x — THE LEAD TIME IS A WORKING POINT. READ THIS FIRST.

util7 **79 → 80** across the whole round (util5 21 at 02:04). ⛔ **No bench move, nothing flashed
on either unit**, and **both** Chameleons verified in `Tag Reader` **by asking the device** at the
end. **Detail: `ChameleonUltra` C515-C518, M62/M63/M64, `burstsync.py` K12-K16.**

⭐⭐⭐ **THE HEADLINE: the field-up lead time before a read is worth 0% → ~95% on three arms, and a
65 ms lead time puts ALL THREE above 75% in every session measured.**

| arm | 40-45 ms | **65 ms** | 60 ms | its baseline |
|---|---|---|---|---|
| `gproxii` | 100% | **100%** | ⛔ **0-8%** | ~50% |
| `indala` | 8-17% | **96% / 83%** | 83% | ~50% |
| `keri` | 0-12% | **92% / 75%** | 88% | ~33% |

⭐ `indala` and `keri` have a **HUMP** (wings collapse, middle 50-70 ms reaches 88-96%) where
`gproxii` has a **HOLE** at 60 ms in a field of 100%. **The arms differ in SIGN at the same lead
time** — one arm's hole is the other two's peak — so no value is merely *safe*: **65 ms works for
all three, 60 ms is catastrophic for one.**

⛔⛔ **CARRY THE RANGE, NOT THE NUMBER.** The peak's position does **not** reproduce (`indala`
65 → 55 ms, `keri` 65 → 60). The working region is **~50-70 ms**. This is C504's read-length
lesson arriving in a new variable, and it was re-learned the hard way (M64).

⛔⛔⛔ **WHAT IT DOES NOT LICENSE, AND THIS IS THE LINE THAT MATTERS.** Ungraded — 7 runs, 3 arms,
no null sweep, no calibration row — so it **moves no cell**. ⛔ **A fitted lead time in the GRADED
path re-bases every past cell**, exactly as re-pointing `pm3_read` would, and is the **operator's
decision**. What this round produced is a number with a control attached, in the gap register.

⚠ **The mechanism is unexplained**: not the beat (C515 — cells 60 and 180 are at the same phase
and score 2/72 vs 42/48), not settling (C515 — Q3 failed in both runs), and now not
protocol-independent either. ⭐ **That is the open question on this line.**

⚠⚠ **THREE METHOD RULES, AND THEY ARE ONE DISEASE: A STATISTIC DECIDED BY A SINGLE CELL.**
**M62** a pooled contrast fired at +21 pts on one notch (bottom TWO cells were above the top
three); **M63** a bench-moved control presumed the flatness it was testing, so two healthy runs
were declared uninterpretable; **M64** a criterion read a shape off its argmax and gave two arms
with equally reproducing shapes opposite verdicts on one 5 ms cell. ⛔⛔ **All three were
pre-registered before their captures.** ⇒ **Pre-registration protects against fitting a criterion
to the data; it does nothing about a criterion that was badly built.** Ask of every band: *what
single cell could decide this?*

⭐ **THE NEXT HANDS-OFF UNITS, in order:**
1. ⭐⭐ **The mechanism.** Nothing proposed so far survives. A 5-25 ms structure that differs in
   sign between arms is the clue; `gproxii` is ASK/biphase and the other two are PSK, which is the
   first thing to line up against it. ⛔ Criterion first.
2. **Is the hole/hump fixed in lead time or in the arm's own frame count?** `gproxii`'s frame is
   1.6 of its probe and the PSK arms' differ — the same arithmetic that turned C494's 6x spread
   into frames (C499). ⭐ Cheap, and it would explain the sign difference if it works.
3. **A 5 ms grid across the full 20-200 ms range** (37 cells) — C515's notch and this hump were
   both found on ladders that could have missed them; a 20 ms grid misses a 5 ms feature ~3 times
   in 4. Expensive (a tick of its own) but it is the only way to say *there are no others*.
4. `nexwatch`, `idteck`, `indala224` are **entirely unmeasured** on this knob.

⚠ **Raw per-round scores for every run are banked** — `caps/k12_gproxii_s17.json`,
`k13_gproxii_s41.json`, `k14_gproxii_s73.json`, `k15_indala_keri_s91.json`,
`k16_indala_keri_s137.json` — so every band can be re-derived offline, and each run's analysis was
exercised against banked data before the capture that used it.

---

## ⭐⭐⭐ 2026-09-17 01:0x — the timing round, as it stood an hour in

util7 **79 → 80** across the round. ⛔ **No bench move, nothing flashed on either unit**, cu2
verified back in `Tag Reader` **by asking the device**, cu1 untouched. Operator checked in over VNC
mid-round. **Repo for the detail: `ChameleonUltra` C515, C516, M62 and `burstsync.py`'s docstring
(K12/K13/K14), commits `d4cf4b53` `1c7e2aa1` `620ce860` `76623450` `9eeca665`.**

⭐⭐⭐ **THE ONE-LINE RESULT: the decode has a 5 ms-wide HOLE in it, at one field-up lead time, and
it reproduced three times.**

| what | where |
|---|---|
| A knob no earlier run used: vary the field-**UP** duration, not the gap between reads | C515 (K12) |
| **Primer 60 ms → 2 of 72. Primers 55 and 65 ms → 24/24 and 24/24.** 40 and 80 → 140/144 | C515 (K14) |
| The no-primer control — a fresh burst, what a single graded read is in — **0 of 72** | C515 |
| ⛔ **Not the beat**: cells 60 and 180 are at the same phase (8.8 vs 7.2 ms), scoring 2/72 vs 42/48 | C515 |
| ⛔ **Not settling** — so C512's post-hoc mechanism story is REFUTED as a description of the profile | C515 (Q3) |
| ⛔⛔ A pre-registered band fired on ONE cell and had to be withdrawn | C515, **M62** |
| A host number was not the air's, by 2.4x — and `LF_TAG_BURST_TARGET_MS`=500 confirmed from the AIR | C516 |

⭐⭐ **WHAT IT IS GOOD FOR.** It turns *this arm is intermittent* into *this arm's decode is a sharp
function of a timing variable nobody was controlling*. C497's wander (88/60/38/75% in one evening)
is the schedule, not the emitter: hold the lead time at 55 or 65 ms and it is 24/24. ⭐ And the knob
is **free** — reader-side, host-side, no firmware, no flash, no solder — against the PSK line's
dither plus C485's 16x buffer, or a hardware mod at `P_LF_ANT_RAW`.

⛔⛔ **WHAT IT DOES NOT DO, AND THIS IS THE PART TO READ TWICE.** Ungraded — no null sweep, no
calibration row — so it **moves no cell**. ⛔ It does **not** license a timed read in the graded
path, any more than C499 licensed re-pointing `pm3_read`: either re-bases every past cell and is
the operator's decision. ⚠ **ONE ARM** — C514 is the standing reason not to generalise, and it was
scoped to `gproxii` in the criterion before the run rather than after it. ⚠ And the mechanism is
**unexplained**: a 5 ms notch inside a 40 ms plateau is a narrow resonance of unknown origin, and
neither hypothesis the experiment was built to test survives.

⚠⚠ **THE METHOD LESSON, AND IT IS THE EXPENSIVE ONE (M62).** K12's P2 was committed before its
capture (`d4cf4b53`) and was **still wrong**: it operationalised *the rate rises* as a three-cell
pooled contrast, which fired at +21 points because the notch fell in its bottom bin — while the
bottom TWO cells were 96%, **above** the top three. ⇒ **Pre-registering a bad statistic
pre-registers a bad answer.** The amendment (a monotonicity clause) was declared before K13, and
K13's own data failed it too, so it was not fitted to the run that prompted it. ⭐ The general form:
**a contrast says how far apart two bins are; only a monotonicity check says there is a trend.**

⭐ **THE NEXT HANDS-OFF UNIT, AND IT IS THE OBVIOUS ONE**: run K12's ladder on **`indala` and
`keri`**. That is the direct answer to the scope limit above — C514 cost exactly this lesson on
C512 — and it is the same rig, the same tagless Rig B, no bench move. ⛔ Write the criterion first;
a notch at a DIFFERENT lead time per arm and a notch at the same one mean very different things,
and that has to be said before the capture, not chosen after it.

⚠ **`caps/k12_gproxii_s17.json`, `k13_gproxii_s41.json`, `k14_gproxii_s73.json`** hold every
per-round score — the analysis can be re-derived offline, and the K13/K14 bands were exercised
against the banked data before either capture ran.

---

## ⭐⭐⭐ 2026-09-17 00:15 — THE OVERNIGHT ROUND, CONSOLIDATED. READ THIS FIRST.

util7 **78 → 79** across the round. Operator checked in over VNC mid-round and is away from home
until **Sunday — no bench changes at all until then**, confirmed by them. ⛔ Everything below was
done with **no bench move, nothing flashed on either unit**, and cu2 verified back in `Tag Reader`.

⭐⭐ **THE ONE-LINE RESULT: the emulate arms' "intermittency" is a SCHEDULING artifact, and the
obvious remedy for it is exactly backwards.**

| what | where |
|---|---|
| Item 9's burst is **not** the intermittency (K1-K4) | C506 |
| The decode is **a function of the read's POSITION**, not a rate — `.X.XX.` in 16 of 16 | C507 |
| It is the AIR, not the client — a host-side `msleep` moves it | C507 (K6) |
| The "meter ahead of VD1" was **never blocked** — the schematic is in the repo | C508 |
| The clock offset is **131.5 ppm and stable to ~1 ppm** ⇒ PSK is blocked by a BUFFER, not physics | C509 |
| Determinism **reproduced** in a third run; survives 9 s randomised gaps | C510 (K7) |
| A lead-in delay moves **nothing** ⇒ the phase reference travels with the first read | C511 (K8) |
| ⛔⛔ **A FRESH BURST SCORES ZERO** — 50% → 0% when each read gets its own … | C512 (K9) |
| … **but only on `gproxii`** — `indala` and `keri` lose nothing. One arm is a scope, not a law | C514 (K11) |
| That caught a constant **I had shipped four hours earlier** | C513 (K10) |

⛔⛔⛔ **THE WARNING THAT MATTERS MOST TO WHOEVER TOUCHES THE HARNESS NEXT (C512), AND ITS SCOPE
(C514).** Giving each read a clean field-down so it is *independent* takes `gproxii` from **50% to
zero** — that arm would grade SILENT with a completely defensible-sounding justification attached.
⛔⛔ **BUT IT IS `gproxii`-ONLY, AND I HAD THIS TOO BROAD FOR AN HOUR.** K11 ran the same design
on `indala` and `keri` with the arrivals control passing on both (0.33 → 1.00, so the bursts did
restart): **`indala` 50% → 67%, `keri` 33% → 54%** against a criterion asking for a halving.
⚠ Those rises are **not significant at n=24 and are not claimed** (M58, a third time); what is
established is that **the collapse does not generalise**. ⇒ **Before changing read timing, measure
the arm you are changing it for** — one arm is a scope, not a law.

⚠⚠ **AND THE ROUND'S OWN WORST MOMENT, KEPT ON PURPOSE.** On C507's evidence I added a random
pause to `--repeat` and set its span to 250 ms from the beat period alone. C512/C513 then measured
that a pause is **not a neutral randomiser** — at 250 ms the rate is 33% against 50%. **The fix
was suppressing the thing it existed to measure**, for four hours, behind a test that pinned only
its lower bound. Now 120 ms, both bounds pinned, break-tested. ⇒ **a constant derived from one
finding is not measured; it is guessed with a citation.**

⚠ **Three things are recorded as NOT holding, and none should be quietly upgraded**: K5 is
**UNREPLICATED** (−15.6 pts against the ≥ 20 it needed); K8 has **NO POWER** for periodicity (its
flat profile fired the branch written for it); and K10's span has **no margin** — 120 ms against a
121.6 ms requirement, a 1.6 ms gap inside a 40 ms resolution.

⭐ **WHAT IS LEFT, AND IT IS ALL THE OPERATOR'S:**
1. **Split the 131.5 ppm between our crystal and this Proxmark's.** `clockoffset.py` measures the
   PAIR, so a trim fitted here is fitted to THIS reader. Needs a **second reader** ⇒ Rig A, ⇒
   Sunday. **This is the next thing on the live line.**
2. The **cost/benefit on a dithered trim**, now fully priced: C485's 16x buffer, and a correction
   that may be reader-specific.
3. `--repeat` over the six arms — now safe to run, and the jitter is measured rather than guessed.
4. Whether the **board** matches the V1.0 schematic C508 read, and what revision the units are.
5. The post-hoc mechanism from C512 (*the emission needs time after field arrival before it is
   decodable*) — **a hypothesis, and it needs its own criterion written first.**

⛔ **Read `METHOD.md` M61 before quoting any rate.** It was earned twice tonight, the second time
on a number I had already committed.

---

⭐⭐⭐ **2026-09-16 23:0x — ITEM 9 IS ANSWERED AND IT WAS THE LAST OPEN HANDS-OFF ITEM.**
util7=77.0 at the start of the tick and 77.0 at 22:59. See item 9 below for C506/C507 in full.
The headline for a cold session: **the burst is not the intermittency, and the decode is not a
rate — it is a function of the read's POSITION**, which a host-side `msleep` moves. ⛔ The
operative consequence is on the `--repeat` queued in §5: back-to-back repeats resample one phase.

**So the next tick works `AUTOPILOT.md` §2 from the top, and that now means §2d and §2e:**

1. ⭐⭐ **§2e — upstream preparation.** ⭐ **The PROXMARK-facing half is DONE and the answer is
   *do not file*** (ChameleonUltra **C505**, `b85c99f0`). The fail-open behaviour has a mechanism
   and it is the **preamble's entropy, which belongs to the FORMAT, not the client**: ones carried
   in each preamble are `idteck` **11/32** → 100% precise, `indala` 3/33 → 76%, `indala224`
   **1/30** → **0%**, while `gproxii`'s 6-bit preamble is backed by 18 enforced parity bits → 100%.
   Our emission fades to a constant level through nulls, and a preamble that is thirty zeros is
   matched by a quiet stretch for free. ⛔ `lf idteck` does not verify a checksum at all (its source
   says `TBD`), so the preamble alone is doing the work — a demodulator cannot do better against a
   format carrying no CRC.
   ⚠⚠ **AND THE SCOPING LIMIT THIS EXPOSED, NOW AT THE HEAD OF THE GAP REGISTER**: every Proxmark
   read-length and precision figure from this round was measured against **our own emulation**,
   which free-runs and fades (C486). **None of it shows the Proxmark reads real tags badly.**
   ⭐⭐ **AND THE CHAMELEONULTRA PR SPLIT WAS ALREADY DONE** — `NEXT.md` §9c (three PRs, not one),
   §9d (the split at FILE level), §9h (the instrumentation split) and §9j (seven fix-PRs first).
   ⛔ **Do not re-derive it.** What it was MISSING has been added (`92c4357d`): **§9b's first
   blocker is now that five PSK emulate arms are graded SILENT on `rd.pm3`**, so the emulate PR
   would ship a feature a Proxmark will not read. It carries C486's cause, C489's reason it is
   unfixable in firmware, and C499's nuance that they are intermittent rather than silent.
   ⚠ Also flagged: an emulate **B** in §9a means ONE reader, and for these arms it was not the
   Proxmark — every emulate cell needs its reader named before a maintainer sees that table.
   ⇒ **§2e is now in good shape. What remains there is execution, which needs the operator.** `LF_RESEARCH_CMDS_ENABLED`
   defaults to 0 and is set only on our branch, so an upstream PR drops that one `-D`. Give thought
   to **how the protocol-support work should be split into PRs** and write it down.
   ⛔ **Open nothing** — the operator's instruction, and they are not reachable to ask.
   ⭐ There is real material to draw on now: `cmdlfkeri.c:176`'s 64-bit `Raw:` against a 32-bit
   internal ID, the 6x spread in `lf_read()` counts with no documentation, and the fail-open
   demodulators — all of them upstream-facing observations about the **Proxmark**, not about us.

2. ⚠⚠ **§2d — TIDYING IS ESSENTIALLY EXHAUSTED, AND THE REMAINING INSTRUCTION SHOULD NOT BE
   FOLLOWED UNATTENDED.** Three scans over all **9,723 lines** of `benchmatrix` this round:
   **no unreferenced module-level function or class** (0 candidates), **no stale comment
   reference** (3 flagged, all three false positives — `tests/` files my scanner did not look for,
   and a legitimate cross-repo `chameleon_cli_unit.py:6304`), and **one** unused import, removed
   (`e3713e5`). Plus `grid.py`'s invalid `"\|"` escape (`3d509c7`).
   ⛔⛔ **The *reduce comments to what is needed* part is the one to leave alone.** The comments in
   this codebase are the institutional memory — `outcomes.py`'s four-outcome rule, `stations.py`'s
   `GOLD_SOURCES`, the ⛔ notes recording what was tried and retracted. **This project exists
   because seven protocols were graded with no calibration row**, and those comments are what stop
   that recurring. A cold unattended session trimming them for length would be deleting the
   guardrail it cannot see the need for. ⇒ **If the operator wants comment reduction, it wants
   them present.** Anything else found here should be a specific defect, not a length target.

3. ⚠ **What is left of the measurement work needs the operator** — see §5 below, which is unchanged:
   `--repeat` over the formerly-silent arms, the `⁇` cells, a third reader for `fdxb emu.pm3`, a
   meter ahead of VD1, and `t55.pm3 → rd.cu2` returning when a tag can go back in the stack.
   ⭐ **And one architecture question outstanding for them** (§3 below): can the PWM clock be slaved
   to the received field? C489 says no pin on this board sees a carrier cycle — check whether that
   is still true of this hardware revision before accepting it.

4. ✅ **THE HANDOFF IS DONE — `AUTOPILOT.md` §5 EXECUTED** (`Momentum-Firmware` `56f37bf2b`, branch
   `t5577-deep-read`). That project had its tracking but **no offline process**; it now has
   `T5577_block0_analysis_data/AUTOPILOT.md` and `QUEUE.md`, with §1, §3 and §4 carried across.
   ⭐⭐ **Two things the assessment found, and the next tick should know both before going there:**
   - ⛔⛔ **It is MORE blocked than this project, not less.** Its independent variable **is the
     placement** — settle time, air gap, re-seats are what its results turn on (`IT WAS THE SETTLE.
     AGAIN.`, `0 mm FLAT CONTACT`, `SETTLE IS TIME-SINCE-POWER-UP`), and none of them can be changed
     over USB. **A round there cannot produce a new capture.**
   - ⛔⛔ **THERE IS NO TEST SUITE THERE.** 126 scripts, no `tests/`, no `runtests` ⇒ **§4's
     *tests green before every commit* cannot be satisfied at all.** In a codebase whose own record
     holds a regression found only by bisect and a **silent-wrong-answer** decoder (`4B4B4B4B`
     returned confidently against a truth of `A5A5A5A5`), that is the blocker before everything
     else. ⭐ **Building one, over the pure `analyse_*.py` functions against the 264 KB already
     banked in `addrprobe_captures/`, is its item 1** — hands-off, and it unblocks every later tick.
   ✅✅ **AND ITS ITEM 1 CORE IS NOW COMPLETE (2026-09-16 late, this round)**: `./runtests` there is
   **143 offline tests over ALL 13 pure `analyse_*.py` scripts** (+2 slow BASELINE/SAFETY controls
   behind `T5577_SLOW=1`), every assertion break-tested. The ten added this round:
   `analyse_odd_parity_candidates`, `_modulation_mislabel`, `_diphase_bitmodel`, `_q11_rate_min`,
   `_rate_height`, `_st_falls_frame`, `_capture_provenance`, `_stprobe_sweep`, `_settle_reposition`,
   `_psk_span_safety`. Values pinned come from OUTSIDE the code (datasheet rate/mod tables, shipped
   firmware constants, the F16/F18 anchor words, D16/D17 findings), cross-checked between scripts.
   ⭐⭐ **Two things writing them produced:** a **crash fixed** in `analyse_rate_height` (its
   documented `campaign_2026*` invocation died on the `"?"` unknown-gap sentinel — `float("")`
   ValueError; the sort key now sends `"?"`/`"flat"` last), and a **6th empty-as-success script
   found** (`analyse_capture_provenance`, invoked by `verify_harness_parsers.sh`, so recorded as an
   `expectedFailure` not fixed — same class the item 1b table tracks).
   ⇒ **What is LEFT of item 1 is only the IMPURE scripts** (serial/subprocess/input), which drive
   hardware or shell gates — operator territory, not a hands-off tick's. See that project's `QUEUE.md`.
   ~~Earlier this round it stood at 23 tests / 2 files:~~ it covered `decode_blockread.py` (pinned
   against a **Proxmark**-read word) and `analyse_frame_parity.py`; that is now 13 files.
   ⭐⭐ **Two defects found by writing them, both recorded there:**
   - ⛔ **The working directory is a trap.** 23 of the 126 scripts hardcode repo-root-relative
     paths, so run from the project directory they see nothing. Seven refuse loudly; **five print
     an empty table and exit 0** — and two of those read as a clean bill of health (*"no re-verify
     mismatches recorded"*, *"read 0 of 0, **WRONG 0**"*). They are `expectedFailure` tests, so a
     fix flags itself; not fixed unattended because two are called by shell scripts that cannot be
     run offline and the convention is the operator's.
   - ⭐ **The `$TMPDIR/t5577_fold_reach/probe` six are a STRENGTH once understood**: that probe is
     compiled from the shipped `lib/lfrfid/tools/t5577.c`, so those analyses measure the real
     firmware C, not a Python re-implementation. It just said so nowhere and died on a
     `/var/folders` path; it now names the build step. ⚠ `$TMPDIR` is per-boot, so the probe
     evaporates on reboot.
   ⚠ **The science there is still entirely blocked** — no capture can be taken until the operator
   returns.

⛔ **Read `METHOD.md` M58, M59, M60 and M61 before measuring anything.** All four were earned
this round, on my own numbers: n too small, comparing across a wandering bench, sweeping in a fixed
order, and quoting a rate over reads that were merely consecutive. M60 cost the most and was caught
only by a control that could have failed. ⚠⚠ **M61 is the one to read twice, because it fails in
the DANGEROUS direction**: M58/M59/M60 give you numbers that are noisy or shifted, and M61 gives
you TIGHT ones — ten agreeing reads and a confident rate, with the confidence as the artifact.


## 1. ~~`seqdump.py` arms 1 of 5 steps~~ — DONE, AND THE DIAGNOSIS WAS WRONG (C475/L443)

**Repo: `ChameleonUltra`** — fixed in `0ecba2df`, both gates clean.

⛔ **"It arms 1 of 5 steps" was false.** `arm()` had run all five in order since it was
written; it is `benchmatrix/devices.py:589` line for line. On cu2 every step answers `success` and
the slot plays back. The claim was read off the source and never run — **the tool was never
executed against the device it was being judged on.**

⛔ **The real fault: the only field source was the Flipper (Rig A, cu1).** Pointed at cu2 —
Rig B, whose reader is the Proxmark — it raised a field on the *other rig*. Every `VOID` it
printed was correct and said exactly that. Now `--field auto|pm3|flipper|none`, taken from the
port's rig.

⭐ **It works**: `--field pm3` on cu2 gives **128/128** PAC entries matching `pac.c:365` and
**96/96** gproxii matching `gproxii.c:91` — C462 reproduced on the other device under a
Proxmark field, with a control that could have failed.

⭐ Two facts worth carrying: `playbacks started` counts field **arrivals**, not repeats
(46→47 in 4 s, then flat 25 s at 19 V) — so the guard must straddle the field coming up;
and `pm3` is a **wrapper script** whose `client/proxmark3` orphans and holds the serial port unless
killed by **process group** (it stranded the port mid-round). Disarm now runs in a `finally`.

⇒ **What is left of this item:** the `arms` table still covers only `pac` and `gprox`.
Extending it to the six is item 3's work, not a defect in the tool.

## 2. ~~`indala224` write hangs~~ — IT NEVER HUNG (C481/L449, `4a8d9b3c`)

**Repo: `ChameleonUltra`** — fixed host-side in `software/script/chameleon_cmd.py`. **No flash.**

⛔ **`CMD 3039` returns — 0.4 s later than the host was willing to wait.** Measured on cu2
with a **fresh link per call**: `STATUS_LF_TAG_OK` in **3.42 s and 3.71 s**, against **1.34 s** for
the 64-bit write beside it. `send_cmd_sync` defaults to **3 s**. L442 recorded it as a handler that
returns no response; it is a handler that is slow.

⭐ **Structural, not bad luck**: `write_t55xx()` runs one pass per old key plus a final open
pass (4 with the default `old_keys`), and `t55xx_write_blocks()` sends every block **twice**. So
the cost is `4 × blocks × 2` — and Indala224 is the **only eight-block writer** in the
tree: **64 sends against 24**, ratio 2.67, measured 2.6.

✅ Fixed: that call passes `timeout=30`. The CLI command from this item now runs end to end and
says *CANNOT TELL — nothing readable before or after*, which is **correct on a tagless rig** and
is **not** a write verdict.

⚠ **Method note worth keeping**: the first attempt issued the command twice on ONE link and
reported a nonsense 0.37 s, because both calls carry the same cmd id and a late response to the
first is matched to the second. **One slow command per link, or you measure the previous one.**

⚠ **THE 3 s DEFAULT IS A LATENT TRAP** for any future multi-block writer — from the host,
a handler that never answers and one that answers late are the same event. No other writer exceeds
7 blocks today, so nothing else is affected yet.

## 3. The six emitter gaps — ⭐ ROOT CAUSE FOUND FOR FIVE: WE EMIT NRZ, NOT PSK

**Repo: `ChameleonUltra`** for the emitter fix and the finding; **`rfid-tools`** for the
gap-register row only.

⭐⭐⭐ **C479/L447 (`16d3a9fb`) — THE PSK ARMS PUT THE PHASE ON THE AIR AS A HELD DC
LEVEL, NOT AS A PHASE-REVERSED SUBCARRIER.** The Proxmark's raw buffer with `indala` armed shows
level runs at 256/512/768/1024us — multiples of the bit — and **no 8us alternation**,
which a 62.5 kHz subcarrier sampled once per carrier cycle must show (L03). On that same buffer
`data rawdemod --p1` returns **nothing** and `--nr` returns our credential `a0000000e6bd0e92`,
stable and repeating. ⇒ `lf indala reader` asks for PSK1 and is handed NRZ, so it is silent while
every bit of the credential is sitting there. **That is how a byte-perfect buffer (C476/C477) and
a silent reader were both true at once.**

⭐ **The control could have failed**: PSK1's `phase[k] = bit[k] XOR bit[N-1]` predicts the
recovered polarity — `indala` (last bit 0) came back upright, `keri` (last bit 1) came back
INVERTED, rotation 0, exact. Disarmed cu2 gives zero frames; KERI's stream does not contain
Indala's frame.

⚠ **FIVE OF THE SIX, NOT SIX.** `gproxii` is ASK/biphase on the 125 kHz clock and carries its
data in levels the hardware demonstrably emits — its silence is a **separate open question**.

### ⛔⛔⛔ THE DUTY EXPLANATION IS REFUTED — THE FIX WAS BUILT AND CHANGES NOTHING (C485)

⚠ **Read this before trusting anything below it about mechanism.** During this round the PSK
emitter was rewritten to C484's proven idiom (`counter_top` 8, alternating **held-level** entries,
32 per bit, 2,048 entries, `repeats` 0), built, flashed to cu2 and verified on the device with `hw
emuseq --raw`. **`lf indala/keri/idteck reader` are all still silent.** The change was reverted and
cu2 reflashed to the committed build.

⭐⭐ **THE RUN THAT ACTUALLY DISCRIMINATES** — one variable, same field, same minutes:

| emission | phase flips | measured |
|---|---|---|
| `emuhold -n 1 --top 8`, 256 entries | none | 33,097 runs of **8us**, p-p 36 |
| new emitter, **all-zeros** frame, 2048 entries | none | 33,039 runs of **8us**, p-p 36 |
| new emitter, **all-ones** frame, 2048 entries | none | 33,029 runs of **8us**, p-p 36 |
| new emitter, **real credential**, 2048 entries | 22 | 424 runs of **256us**, p-p 230 |

⇒ The subcarrier genuinely reaches the air and the length is fine. **The phase flips change the
capture's entire character** — and an emitter that provably emits a true subcarrier produces
**the same signature** the old duty-based one did.

⛔ **SO THE C479 CAPTURE NEVER DISCRIMINATED** between *we emit NRZ* and *we emit PSK the
instrument cannot resolve*, and it was read as the first. The arithmetic: the Proxmark samples once
per carrier cycle, so an fc/2 subcarrier sits at exactly **fs/2**, where samples are
`A·cos(φ)` alternating and a 180° flip **inverts** them — so the phase walk
appears as a big bit-rate component (the 256/512/768/1024us runs) while the subcarrier stays a
small ripple. Both emitters alias to the same picture.

### ⭐⭐⭐ ROOT CAUSE, MEASURED: OUR SUBCARRIER IS NOT COHERENT WITH THE READER (C486, `7a5eced1`)

`hw emuhold -n 1 --top 8` emits a **pure 62.5 kHz square with NO DATA**, so anything that varies
across a capture is the relationship between two **clocks** and nothing else. The Proxmark samples
once per carrier cycle, so an fc/2 subcarrier sits at exactly fs/2 and the samples are
`A·cos(φ)` alternating. Predictions written first: **coherent ⇒ constant amplitude;
free-running ⇒ beats through nulls.**

**Measured over 320 ms, per 2 ms window: min 2.3, max 20.6 — a 9.0× swing, 9 of 160
windows under a quarter of peak, a deep null roughly every 80 ms.** Offset of order **10 Hz on
62.5 kHz (~100-200 ppm)**. ⇒ **Free-running. Flat would have refuted it.**

⭐⭐ **WHY THAT KILLS PSK AND LEAVES EVERYTHING ELSE ALONE.** A frame is 16.4 ms against an
~80 ms beat, so φ rotates **70-80° across a single frame** — on top of the 180°
flips that ARE the data — and periodically the signal vanishes. ASK and FSK carry data in
envelope amplitude and timing, which a rotating subcarrier phase does not touch. **That is exactly
the passing/failing partition of the emulate column**, and it explains the thing every earlier
hypothesis had to explain away: the buffer is byte-perfect (C476/C477) and it does not help,
because the defect is not in what we build — it is in what we build it against.

⛔ **THE FIRMWARE ALREADY SAID SO, AND DREW THE WRONG CONCLUSION FROM IT.** `lf_tag_em.c:258`:
*"the tag-mode antenna taps on this board are envelope-only, which rules out coherent demodulation
or phase-lock-based approaches"* — then reasons this *"does not preclude the differential-phase
encodings supported here"*. **That last step is what C486 contradicts**: a reader sampling at fs/2
needs the subcarrier coherent whether the encoding is differential or not.

### ⇒ WHAT THIS LEAVES FOR THE OPERATOR — AN ARCHITECTURE QUESTION, NOT A BUG

⛔ **Do not queue another emitter rewrite.** Two have now been refuted by experiment (C482
duty-rendering, and the level-pattern emitter built on it), and the buffer has been exonerated
entry-by-entry for all six arms. **Nothing in the sequence we build can fix a clock that is not
locked to the reader's.**

The real question is whether PSK emulation is reachable on this board at all:

- ⭐ **Can the PWM clock be slaved to the received field?** That is the fix in principle. The
  note above says the tag-mode taps are envelope-only — ⇒ **check whether that is still true of
  this hardware revision** before accepting it, because everything rests on it.
- ⚠ **If it cannot**, then PSK emulation cannot work here, and the honest outcome is a
  documented hardware limitation plus a gap-register row — not more emitter work. ⭐ That would
  also retire the six-protocol gap as *understood* rather than *open*, which is worth more than a
  fix that keeps not arriving.
- ⭐ **A second reader would sharpen it further**: the Flipper does not sample synchronously
  with our subcarrier either, but it decoded Indala/KERI/IDTECK from a *Flipper* emulation. ⛔
  Needs the operator — the Flipper is on Rig A.

### ✅ `gproxii` IS ANSWERED TOO — AND IT IS NOT AN EMITTER DEFECT (C487, `42373544`)

⭐⭐ **Our GProxII emission decodes byte-exact.** The Proxmark's own decoder on the captured
emission returns `G-Prox-II - Len: 26 FC: 123 Card: 1337 xor: 141, Raw: fac2a38c2b081af0210b12c2`
— **exactly** the registry's expected raw — and `data rawdemod --ab` recovers the same 96
bits independently.

⛔⛔ **The failure is ONE STEP, isolated in a single session on the same 40,000 samples:**

    lf read -s 40000  →  lf gproxii demod   →  nothing
    data save → data load → lf gproxii demod   →  DECODES

Live `lf gproxii reader`: **0 of 8**. Capture → save → load → demod: **3 of 3**.
⭐ Control: the identical test on `indala` fails **both** ways, so save/load rescues gproxii
specifically and is not a universal get-out.

⇒ **So the six had TWO causes, and both are now measured**: coherence for the five PSK arms
(C486), and a **margin/instrument artifact** for gproxii — our frame is on the air, byte-exact,
and the reader's live read-then-demod path will not lock onto it.

⚠⚠ **AND THIS TOUCHES THE HARNESS.** `lf <proto> reader` IS the path every emulate cell is
graded on, so **a SILENT grade is not by itself evidence that the emitter is silent.** ⛔ It
does NOT follow that other SILENT cells are artifacts — gold-tag readings decode live on that
same path, so whatever the mechanism, it bites a marginal signal and not a real tag's.
✅ **AND THAT UNIT IS DONE — THE ARTIFACT IS ONE ARM WIDE (C488, `c580f74d`).** Every
emulate arm armed on cu2 in turn, one capture each, demodulated live and then after save/load.
⚠ Grades nothing; it is about the instrument.

| outcome | arms |
|---|---|
| **rescued by save/load** | `gproxii` — **and nothing else** |
| decoded both ways (11) | `em410x`, `viking`, `jablotron`, `pac`, `hidprox`, `ioprox`, `awid`, `gallagher`, `securakey`, `noralsy`, `fdxb` |
| silent both ways | `indala`, `keri`, `nexwatch`, `idteck`, `indala224` (C486's five) + `em410x_electra` |

⇒ **The live path and the calibrated grid agree arm for arm** — the eleven here are exactly
the eleven graded EXACT. **So a SILENT grade is NOT generally an artifact**; the worry is bounded to
the one cell that raised it. ⛔ **Nothing here licenses a re-grade.**

⚠ **A probe bug worth remembering**: the first pass scored `hidprox` silent because the
registry's markers are `^`-anchored and it searched a multi-line blob with `re.search`. **A marker
is matched against a LINE** — matched that way, `hidprox` decodes both ways. It could not
invent a rescue (both columns share the regex) but it can hide one.

## 4. ~~Rig A's tag contents are unknown~~ — READ (C480/L448, `e3e8de6e`)

**Repo: `ChameleonUltra`.**

⭐ **Rig A's T5577 carries a PSK-family credential that none of our five PSK readers can
decode.** cu1 in reader mode, all 21 registered read commands: every ASK/FSK reader returns `LF tag
not found`; `indala`, `keri`, `nexwatch`, `idteck` and `indala224` all return *a tag-like
subcarrier is present but no frame of the requested type could be decoded* — stable, 3 of 3.

⭐ **Two controls, and it needed both.** The same reads on **tagless Rig B** return a plain `LF
tag not found`, so the message is not what the PSK path prints whenever it finds nothing. And the
message offers *an emulated tag* as a cause while Rig A carries a Flipper — so the Flipper was
asked: `loader info` → **`No application is running`**. ⇒ The source is the tag.

⚠ **Why it will not decode is open.** Leading candidate: a **partial write** — raw `lf
t55xx write` is unreliable by design (field up, 1 ms, one attempt, field down) and measured **0 of
11** on this bench (C305), which leaves a valid PSK config block over data blocks that never
landed. A PSK variant our readers do not try is the other.

⛔ **It licenses nothing** — `GOLD_SOURCES = {t55.pm3, oem}` and its provenance is
unrecorded, so it is a source under test, never a reference. ⛔ **And it was deliberately NOT
rewritten**: cu1 could reprogram it with no hands, which would destroy the evidence before the
operator has seen it. **Leave it for them.**

## 5. Queued, needs the operator

- ~~`fdxb` `emu.pm3 → rd.cu2` — ambiguous~~ ✅ **ANSWERED, AND IT NEVER NEEDED AN OPERATOR**
  (ChameleonUltra C495). Both devices are on Rig B and no tag is involved, so nothing had to move.
  Bracketed controls on the same station, same sessions: `lf em 410x sim` → `lf em 410x read`
  **4/4 before and 4/4 after**; `lf fdxb sim` → `lf fdxb read` **0/8 between them**, 1 of 24
  pooled; null with nothing simulating 0/8. ⇒ the station, our reader and the pm3's simulator all
  work — **this one pairing is marginal**, and the single hit rules out a hard incompatibility.
  ⚠ **Attribution is unresolved and no gap row was added**: our decoder reads a REAL fdxb tag
  byte-exact and the pm3's simulator drives em410x into that same decoder 12/12, so neither is
  generally broken. Telling them apart needs a **third reader** on this pairing — that part is
  genuinely the operator's.
- `em410x` `pm3·emu` and `fdxb` `cu1·emu` read `⁇` — need `--repeat 10`.
  ⭐ **Evidence for the em410x half, gathered in passing and UNGRADED**: `lf em 410x sim` read by
  cu2's `lf em 410x read` came back byte-exact **12 of 12** across three sessions on 2026-09-16, with
  0 of 8 when nothing was simulating. It was the CONTROL for C495 rather than the subject, which is
  why it can be trusted as far as it goes and no further — one reader, no sweep, no licence.
  ⇒ whatever the `⁇` is, that pairing is not fragile the way `fdxb`'s is.
- `t55.pm3 → rd.cu2` for everything: gone while Rig B is tagless.
- ⭐⭐ **`--repeat 10` over ALL SIX formerly-silent arms**, not just the two `‽` cells — C491 measured hit rates of 1-in-9 to 1-in-3 through the graded reader command, so one read cannot characterise any of them.
  ⛔⛔ **BUT READ C507 FIRST — IT CHANGES WHAT `--repeat` HAS TO DO.** Reads issued back-to-back
  inside one session do **not** sample independently: the decode is a function of the read's
  POSITION, six identical reads gave `gproxii` the identical pattern in 16 of 16 sessions, and a
  host-side `msleep` alone moves both the pattern and the rate (29.2% → 70.8%). ⇒ A naive
  `--repeat 10` would resample the same phases ten times and report a tight, confident and
  **wrong** rate — the same shape of error as grading with no calibration row. ✅ **DONE — THE REMEDY IS IMPLEMENTED AND TESTED** (`f22feec`). Each repeat after the
  first now waits a random interval from [0, 0.25) s, which spans more than one beat period.
  Seven tests, each break-tested; `--no-repeat-jitter` reproduces the old behaviour.
  ⛔⛔ **AND IT RE-BASES NOTHING — CHECKED, NOT ASSUMED, BECAUSE THAT IS THE WHOLE QUESTION.**
  `repeat` defaults to 1, which never enters the pause, and **0 of the 20 banked runs used
  `repeat > 1`**. ⚠ This is NOT the same class of change as re-pointing the registry's
  `pm3_read`, which really would re-base every past cell and remains an operator decision.
  ⚠ A **constant** pause would not have been a fix: it is just another fixed cadence, which is
  what C507 measured as deterministic. The pause is DRAWN, and a test pins that.
- ~~⭐ **A meter on the board, ahead of VD1.**~~ ⛔⛔ **THIS ITEM WAS NEVER BLOCKED — THE SCHEMATIC
  IS COMMITTED IN THE ChameleonUltra REPO AND NOBODY HAD OPENED IT** (C508, `b8752613`).
  `hardware/ultra/Chameleon_nrf52_ultra_V1.0.pdf`. Read exhaustively, the LF sheet exports five
  ports: `LF_ANT_DRV` and `LF_MOD` are MCU **outputs**, `LF_AMP_PWR` is a power enable, and the
  **only two inputs — `LF_OA_OUT` and `LF_RSSI` — are both downstream of VD1**, one through an
  envelope detector and two opamp stages, the other through a second diode VD2. ⇒ **C489 stands,
  by enumerating the ports rather than inferring from where one diode sits.**
  ⭐ **The probe point has a name now**: `P_LF_ANT_RAW` is on the J1-J4 pad group, the
  main-board↔antenna interconnect (the LF antenna is a separate assembly,
  `Chameleon_nrf52_ultra_ant_V1.0.zip`) — where a scope goes, and where the only hardware-mod
  route to coherence would start.
  ⚠ **What is left of it**: this confirms the SCHEMATIC; checking the BOARD matches it is the
  residual, and the file is **V1.0** so the units' actual revision still matters. ⭐ If the
  instrument is still wanted it is an **oscilloscope, not a multimeter** — a DMM's AC ranges are
  specified for 50/60 Hz and read nonsense at 125 kHz — any >= 20 MHz scope, with a **x10** probe
  (a x1 probe's ~100 pF would detune the resonant tank and change what is being measured).
- ⭐⭐ **THE ARCHITECTURE QUESTION IS RE-POSED: NOT *CAN WE LOCK*, BUT *CAN WE TRIM*.** C489
  answers the lock question no, and C508 now confirms it from the board files. ⛔ **But PSK does
  not need phase lock — it needs the phase to STAY PUT across one frame.** C486's 70-80° across a
  16.4 ms Indala frame is ~12 Hz, ~190 ppm of the 62.5 kHz subcarrier; under ~10° needs **~27
  ppm**. ⭐ The clock source is already the good one — `lf_tag_em.c:250` holds HFXO for **±40
  ppm** rather than HFINT's ±1.5% — and ±40 ppm on our side ALONE already exceeds what the frame
  needs, which is the argument for a per-pair **trim** rather than a better part.
  ⛔ **J1, from source and free: no INTEGER trim exists at any prescaler.** One `counter_top` tick
  is **125,000 ppm** at the 1 MHz base clock in use and **7,800 ppm** at the fastest available —
  it overshoots a tens-of-ppm correction by ~300x. Only a **dither** (fractional-N across entries)
  could work, and for the PSK arms that means expanding the buffer **16x**, which is exactly
  C485's shape — built, flashed and reverted. ⚠ That cost is stated **before** anyone builds.
  ✅✅ **MEASURED — IT IS STABLE, SO THE ANSWER IS A COST AND NOT A PHYSICS BLOCKER** (C509,
  `4199fec0`). cu2 armed once, **19 accepted readings, 0 refused, 25 minutes: min 130.9, max
  131.9, mean 131.5 ppm — spread 0.9 ppm, 1% of the mean**, against J2's STABLE band of 30%.
  About **40x inside its own threshold**. ⇒ the thing a trim would correct sits still.
  ⛔⛔ **J3 refused that result on a guard I wrote, and it was NOT talked away.** The spread is
  under the 28.1 ppm FFT bin, so J3 called it the resolution floor — but `offset_ppm` interpolates
  sub-bin, so the bin is its GRID. **J4 was committed BEFORE being run** (`962332a4`) and settled
  it host-only: synthetic PSK1 at the run's own capture length, **max |error| 0.9 ppm, monotone,
  and inputs 1 ppm apart correctly ordered — ~28x below the grid.** ⇒ J3's refusal was an
  artifact. ⚠ **Claim bounded**: the estimator's own error is also ~0.9 ppm, so it is *stable to
  ~1 ppm*, not better; and the apparent warm-up over the first 10 min is inside that and is **not
  claimed**.
  ⚠⚠ **THE LIMITATION THAT MATTERS IS NOT THE BUFFER**: `clockoffset.py` measures **the PAIR**,
  so 131.5 ppm is ours plus THIS Proxmark's, and a trim fitted here is fitted to this reader.
  Splitting it needs a **second reader** — operator territory, and it is the thing to do next on
  this line.
  ⭐ **What is left is the operator's cost/benefit**, with everything priced: a dither, C485's 16x
  buffer, and a correction that may be reader-specific. ⚠ C485 does **not** refute it — it built
  that buffer shape and changed the SEQUENCE; a dither changes the average CLOCK RATE, which is
  what C486 identified.

## 6. ~~Registry work, no bench~~ — BOTH DONE (`rfid-tools`, 467 tests green)

- ✅ **`em410x_electra`**: the `rd.pm3` refusal is now recorded as **permanent**, with the
  measurement and the reason. The old comment said the column was refused *"until the bench says
  what the Proxmark prints"* — which is what sent a tick to measure it. There is no answer to
  get: `lf em 410x reader` prints `EM 410x ID 2244668800` and nothing else, and `-h` has no Electra
  flag at all. ⛔ The row now says in full why recording `2244668800` would build a false pass
  in by construction. Our `cu_read` is still genuinely missing and is still real work.
- ✅ **`indala224` `cu_decode_marker`**: **checked, and neither "one of them" is wrong in the
  way the question assumed.** The marker `Indala224 PSK1` is CORRECT — a marker's job is to
  match what the device prints, and `lf indala read --224` does print exactly that
  (`chameleon_cli_unit.py:6304`). **The device's LABEL is the thing that is wrong**: the same file
  says `--224` configures PSK2 (6331, 6349), and the emitter agrees — `indala224_modulator`
  builds with `LF_PSK1_PHASE_DIFFERENTIAL`, which is PSK2. ⇒ A cosmetic **ChameleonUltra** bug.
  ⛔ **Deliberately NOT fixed unattended**: the print and the marker are coupled, and if they
  go out of step every `indala224` `rd.cu*` reading silently turns from EXACT into SILENT. It wants
  one commit touching both repos together, with the operator present. The registry row carries that
  warning now so nobody "tidies" the marker on its own.

## 8. ~~`indala224` emits a frame with the WRONG payload~~ — CORRECTED SAME NIGHT (C493)

**Repo: `ChameleonUltra`.** ⛔ **The payload is OURS.** Nobody had looked at what the reader
actually returns; five short reads give **212, 202, 199 and 189 of 224 leading bits byte-exact**,
with the tail collapsing to all-ones and the reported length nonsense (254-611 against 224).
A phase-encoding mismatch cannot produce 212 correct leading bits, so the PSK1/PSK2 lead was
wrong and the arm is **not** a separate defect.

⭐⭐ **It is the beat's cleanest confirmation instead.** An Indala224 frame is 224 x RF/32 =
**57.3 ms** against a measured null spacing of **60.8 ms** — the frame is as long as the gap
between nulls, so it cannot finish inside one, and the survival times (48-54 ms) sit just under
that spacing. ⭐ Frame length then orders the entire column: 16.4 ms arms 9/11, 4/9, 3/9;
32.8 ms (nexwatch) 0/9; 57.3 ms (indala224) 0/9.

⚠ **What is still open here**: the geometric model over-predicts `nexwatch` (it says ~1 in 3,
the bench says 0 of 9), and the spread among the three 16.4 ms arms is unexplained. Neither is
an `indala224` question any more.

## 9. ~~Why is it intermittent?~~ — ANSWERED, AND THE ANSWER IS BIGGER THAN THE QUESTION

**Repo: `ChameleonUltra` C506 and C507** (`36c684c1`), tool `burstsync.py`. ⚠ Ungraded — no null
sweep, no calibration row, **moves no cell and licenses no re-grade.**

✅ **The burst is NOT the intermittency (C506).** Four criteria were committed to git BEFORE the
first capture (`011d475b`, M55). **K4 is arithmetic and cost no bench time at all**:
`recompute_frames_per_burst()` targets 500 ms and every arm's frame is under 250 ms, so every
burst is >= 500 ms against a **240 ms** longest graded read ⇒ a burst cannot expire inside one
read. **K1**: the field does not drop per read either — 12 reads give **5** arrivals (`gproxii`),
**3** (`indala`), **4** (`keri`), identical across two runs and nine sessions. **K2 is the effect
and the effect is absent**: starvation predicts early reads beat late ones and two of three arms
go the other way. **K3** null: **0 of 12** decodes, Δ = 0.

⭐⭐⭐ **AND WHAT WAS BEHIND IT (C507) — THE DECODE IS A FUNCTION OF THE READ'S POSITION, NOT A
RATE.** Six IDENTICAL reads per session, sixteen sessions, one arming: `gproxii` returned the
pattern **`.X.XX.` in 16 of 16** — index 1, 3 and 4 decoded every time, index 0, 2 and 5 never —
and `indala` had **index 5 at 16/16 against index 4 at 0/16**, adjacent reads of the same command.
A ~50% rate cannot produce one fixed six-bit pattern sixteen times.
⛔ That could have been the CLIENT rather than the air, so **K6 was committed before its capture**
(`96546d93`). Inserting `msleep -t D` — `AlwaysAvailable` in `cmdmain.c:365`, touching no device
and raising no field — **moved the pattern on 3 of 4 delays for `gproxii` and 4 of 4 for
`indala`**, and swung `gproxii`'s rate from **29.2% to 70.8%**. A host-side pause cannot change
which read is the nth. ⇒ **the client does not explain it.**

✅✅ **AND THE DETERMINISM IS NOW REPRODUCED IN A THIRD RUN (C510, `975d7a2c`).** K7 asked
whether the session's START PHASE is what makes it deterministic — criterion committed first,
fixed vs randomised inter-session spacing, interleaved. **Fixed 88% modal, random 88% modal**, so
**H_phase is REFUTED by its own band**. But `.X.XX.` came back in **14 of 16** sessions, matching
K5's 16/16 and **surviving randomised gaps of up to 9 s (~100 beat periods)** ⇒ what K6 left at
*no verdict* now holds.
⚠⚠ **AND THE PUZZLE I MANUFACTURED DISSOLVED — M58, AGAIN, ON MY OWN NUMBERS.** K6's D=0 cell
was **2/4**, and all four of its patterns shared the `.X.X` prefix. At n=4 that never conflicted
with 7/8 or 16/16. **There was no K5/K6 difference to explain**; I read a small-n cell as a
discrepancy and spent a whole experiment on a hypothesis about it. Both the refutation and the
fact that the puzzle was never real are recorded — the second mistake is the expensive one.
⭐ **The surviving constraint**: ms between READS moves the pattern; seconds between SESSIONS do
not. ⚠ That is **post-hoc** and needs its own criterion before it is anything more.
⚠ **K5** — a replication of K2's surprise — landed in its own middle band (−15.6 points against
the >= 20 it needed) and is recorded **UNREPLICATED**, not reinterpreted.

## 7. When 1–6 are done or blocked

**Repo: whichever owns the code you are tidying.** Upstream prep is `ChameleonUltra`.

Tidy the codebase behind the 467 tests, then upstream prep (`AUTOPILOT.md` §2d/§2e). Then hand off
to the T5577 project (§5).
