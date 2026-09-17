# Work queue — newest decisions at the top of each item

⛔⛔ **BENCH STATE CHANGED 2026-09-16 — cu2 WAS REFLASHED.**
`v2.2.0-920-gdf053dd` — **a committed, clean build** of this tree, carrying the `hw emuhold
--top` instrumentation (ChameleonUltra `17d65d50`). **cu1 was never touched.**
⚠ An experimental level-pattern PSK emitter was flashed on top of this during the round and
then **reverted and reflashed away** (C485) — cu2 is back on the committed build. Verify
FUNCTIONALLY, never by version string (C461): an armed Indala must show **64 entries, `seq
repeats` 15** (`hw emuseq --count 0`), and `hw emuhold -n 1 --top 8` must succeed. Both checked.
⚠ `enterdfu.py` failed to trigger twice in a row before succeeding on the third try, with
nothing flashed either time — it says so explicitly and distinguishes a trigger failure from a
flash failure. **Retry it; do not go looking for a broken device.**

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

- `fdxb` `emu.pm3 → rd.cu2` SILENT while `t55.pm3 → rd.cu2` is EXACT — pm3's own `lf fdxb sim`
  or our reader. Ambiguous (run 20260916_161528).
- `em410x` `pm3·emu` and `fdxb` `cu1·emu` read `⁇` — need `--repeat 10`.
- `t55.pm3 → rd.cu2` for everything: gone while Rig B is tagless.

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

## 7. When 1–6 are done or blocked

**Repo: whichever owns the code you are tidying.** Upstream prep is `ChameleonUltra`.

Tidy the codebase behind the 467 tests, then upstream prep (`AUTOPILOT.md` §2d/§2e). Then hand off
to the T5577 project (§5).
