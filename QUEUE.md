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

## ⭐⭐⭐ 2026-09-16, 21:00 — THE READ WINDOW IS 3-4 FRAMES, AND MY OWN FIRST SWEEP WAS CONFOUNDED

**Repo for the detail: `ChameleonUltra` C499 and METHOD.md M60** (`0a0c201b`).

⭐⭐ **THE 6x SPREAD IN THE PM3'S SAMPLE COUNTS (C494) HAS A UNIT: FRAMES.** Converted to
multiples of each protocol's own frame length, the client asks for indala **14.6**, keri 4.9,
idteck 2.4, nexwatch 4.9, gproxii **1.6**. A per-arm ladder (1,2,3,4,6x the frame, plus the
reader's own count), every rung inside ONE arming and ONE pm3 session, arms round-robined, **rungs
shuffled**, two seeds pooled to **n=24**, tagless null **0 hits**:

| arm | frame | 1f | 2f | 3f | 4f | 6f | its own reader | ⭐ best |
|---|---|---|---|---|---|---|---|---|
| `indala` | 2048 | **0** | 14 | **21** | 19 | 17 | 1/24 (14.6f) | `-s 6144` |
| `keri` | 2048 | **0** | 6 | 9 | **14** | 9 | 8/24 (4.9f) | `-s 8192` |
| `idteck` | 2048 | **0** | 5 | **9** | 6 | 6 | 7/24 (2.4f) | `-s 6144` |
| `nexwatch` | 4096 | 1 | 7 | 7 | **10** | 3 | 5/24 (4.9f) | `-s 16384` |
| `gproxii` | 6144 | **0** | 15 | **24 of 24** | 18 | 8 | 9/24 (1.6f) | `-s 18432` |
| `indala224` | 7168 | **0** | **0** | **0** | **0** | — | 0/24 (4.2f) | ⛔ none |

⭐⭐⭐ **`gproxii` AT `-s 18432` IS 24 OF 24 — perfect, in both seeds independently.** ⭐⭐ **ONE
FRAME IS 0,0,0,1,0,0 OF 24 ACROSS THE SIX**, and it is the rung that most often returns a decode
marker with the WRONG payload — C490's confident-wrong-answer, reproduced on purpose.

⛔⛔⛔ **AND READ M60 BEFORE YOU SWEEP ANYTHING, BECAUSE IT NEARLY COST THIS FINDING.** The FIRST
version of this run ran the ladder ASCENDING, so every length sat at a fixed position after the
arming and position was perfectly correlated with length. It scored `lf keri reader` **2/12**
against `lf read -s 10000` + `lf keri demod` **10/12** — and `cmdlfkeri.c:222` is `lf_read(false,
10000); demodKeri()`, i.e. the *same count through the same demodulator*. **Nothing but position
could differ.** Shuffled, the two agree, and `gproxii`'s zeros became 8-12/12. ⇒ **The confound was
as large as the effect being measured**, and would have been written up as a knife-edge length
window with n=12 behind it.

⛔ **What that REFUTES**, including two things this repo's own gap register asserted:
- the ~61 ms fading period does **not** cap the usable read — `gproxii` peaks at **147 ms**
  (2.4 null intervals) and is still 18/24 at 197 ms;
- *a read-length sweep on nexwatch shows no trend* — it does, swept in frames (1f 1/24, 4f 10/24);
- the reader command's code path is **not** different from `lf read -s N` + `demod` at the same N,
  so C487's save/load rescue is about save/load and nothing else;
- ⭐ **`idteck` is not a zero** — 9/24 at 3 frames. It was item 2 of the old next-tick list.

## ⭐⭐ WHERE THE NEXT TICK STARTS

1. ~~⭐⭐⭐ **AUDIT EVERY OTHER SWEEP TOOL FOR M60's CONFOUND**~~ — ✅ **DONE, AND C469 SURVIVED IT
   BY MEASUREMENT** (ChameleonUltra **C500**, `c02e34dd`). ⭐ **The discriminator is whether the
   statistic was PREDICTED in advance or read off the sweep's own SHAPE.** `holdsweep.py` has the
   same fixed ascending order `shortread.py` did, but C469's criterion (modal run = N x 256us,
   slope 1) was fixed before the firmware existed — so it was re-run **shuffled, order 2 7 8 5 1 9
   4 3 6**, and every N landed on its prediction, 91.8-97.2% modal share, no knee. ⛔ `gaintest`,
   `oversample_test` and `inputtest` are **BLOCKED** (all repeats of one setting contiguous, which
   is worse than merely ordered) and `phasesweep` fixes phase order within each rep — **but all
   five affected tools sweep a REAL T5577**, which divides the reader's carrier and is coherent, so
   they carry neither the beat nor the wandering rate, and they score a tag/empty ratio that a
   common-mode drift divides out. Real defects, **no claim known to be wrong**, and all five need
   the operator anyway. `offsetsweep`/`sweep`/`airduty`/`nullframe` re-analyse a file on disk and
   cannot be affected; `drivesoak` sweeps order on purpose.

2. ⭐⭐ **`indala224` is now the ONLY arm that never decodes** — 0/24 at all five lengths, both
   seeds, with wrong-payload markers at four of them. C493 explains it geometrically (57.3 ms frame
   against 60.8 ms null spacing, so it cannot finish inside one interval) and the ladder is
   consistent with that: no length helps, because the problem is not the window. ⭐ **The cheap
   open test: does it decode if the frame is SHORTER?** Nothing else in the six can vary its own
   frame length, and `indala224` can — a 224-bit frame is the only one longer than the null spacing.
3. ⭐ **Sharpen the per-arm peak.** The ladder has one rung at 2f, 3f and 4f; the peak is somewhere
   in 2.5-4.5 frames and only three points bracket it. `./shortread.py <arm> --lengths a,b,c
   --repeat 12` per arm, shuffled. ⚠ Worth doing only after item 1 — it is the same instrument.
4. Then `AUTOPILOT.md` §2d (tidying behind the 467 tests) and §2e (upstream prep).
   ⚠ One found in passing and NOT fixed: `benchmatrix/grid.py:313` has `"\|"`, an invalid escape
   sequence that Python already warns about. One character, covered by the tests.

⛔ **Read `METHOD.md` M58, M59 and M60 before measuring anything**: all three were earned this
round, by me, on my own numbers — n too small, comparing across a wandering bench, and sweeping in
a fixed order.

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
- ⭐ **A meter on the board, ahead of VD1.** C489 rests entirely on the schematic putting the rectifier at the coil; that is the one cheap check that could overturn it, and it takes minutes.

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

## 9. ⭐ Why is it intermittent? A hypothesis that costs nothing to test

Each `lf read` raises the field, and the emulation plays a **finite burst per field arrival**
(`m_frames_per_burst`; `playbacks started` counts arrivals, not repeats — C475). So the reader's
capture window and the burst are unsynchronised, which would produce exactly the 1-in-9 to 1-in-3
hit rates C491 measured. ⭐ Testable with no bench move: vary the settle before the capture, or
count playbacks across a read, and see whether the hit rate tracks. ⚠ Write the criterion first.

## 7. When 1–6 are done or blocked

**Repo: whichever owns the code you are tidying.** Upstream prep is `ChameleonUltra`.

Tidy the codebase behind the 467 tests, then upstream prep (`AUTOPILOT.md` §2d/§2e). Then hand off
to the T5577 project (§5).
