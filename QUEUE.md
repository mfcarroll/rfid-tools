# Work queue — newest decisions at the top of each item

⛔ **EVERY ITEM NAMES ITS REPO. Read `AUTOPILOT.md` §0b before committing** — three repos, three
gates, and tonight's findings were filed in the wrong one until the operator caught it.

⭐ **A COLD SESSION STARTS HERE, AFTER `AUTOPILOT.md`.** Keep it current: you are the only thing
that carries between ticks (`AUTOPILOT.md` §6). Tick off what you finish, add what you find, and
**commit it before you exit** — an uncommitted queue is a lost one.

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

## 2. `indala224` write hangs — `CMD 3039`

**Repo: `ChameleonUltra`** — firmware. Logged as L442; a fix needs its own entry.

`lf indala write --raw 80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5 --224` →
`TimeoutError: CMD 3039 exec timeout` in ~4 s, reproducible. The registry row is **correct**
(verified). `cmd_processor_indala224_write_to_t55xx` returns no response. ⭐ Pure USB, no bench.
⚠ Rig B has no tag, so the write has nothing to write to — a handler that hangs instead of
reporting "no tag" is still a bug, but keep that confound in the write-up.

## 3. The six emitter gaps — the headline. THE BUFFER IS EXONERATED; THE FRAME IS NEXT

**Repo: `ChameleonUltra`** for the emitter fix and the finding; **`rfid-tools`** for the
gap-register row only.

`indala` · `keri` · `nexwatch` · `idteck` · `gproxii` · `indala224` emit nothing `rd.pm3`
can decode, on **both** Chameleons across **two** builds, licensed both times.

⭐⭐ **SEQDUMP HAS ANSWERED, 6 OF 6 (C476/C477, `194e7fd4`).** Every one of the six builds a
**byte-perfect PWM buffer** — `indala` 64/64, `keri` 64/64, `nexwatch` 96/96, `idteck` 64/64,
`gproxii` 96/96, `indala224` 448/448 — each predicted from the emitter source *before* the
capture, and `seq repeats` (the bit period) is right on all of them. **The sequence builder is not
the defect.**

⛔⛔ **AND THE BUFFER DOES NOT SEPARATE THE SIX FROM THE ELEVEN**: `pac`'s buffer is equally
perfect and the Proxmark decodes it. ⛔ The tidy explanation is already refuted — *the six
are the arms carrying data in the PWM inversion bit* fails, because `em410x`, `viking`, `fdxb`,
`gallagher`, `securakey` and `noralsy` all set that bit and all are decoded.

⇒ **NEXT, AND IT NEEDS NO BENCH: is the FRAME the right bytes?** seqdump predicts from the
same frame the econfig was handed, so a wrong preamble, format or block rotation passes it
unchanged — it tests the modulator, not the credential. ⭐ **There is a known precedent for
exactly this defect: C160.** Keri's air frame is the T5577 **block form** `(id << 3) | 7`; emulating
the reader's `E0000000||id` view instead is the same 64-bit cycle three bits along and gave a stable
WRONG credential 6 times out of 6. **The same class of error in any of the other five would look
exactly like what we see.** ⇒ Compare, source to source, what each of our six emitters sends
against what the Proxmark's own `lf <proto> clone` writes into T5577 blocks
(`/Users/Shared/code/personal/rfid/proxmark3/client/src/cmdlf*.c`). Pure reading, no hardware.

⭐ The air check on the tagless Rig B remains available for any fix: arm cu2, read with the
Proxmark, disarm in a `finally`. A fix that turns one of the six EXACT is real evidence — and
**ungraded**; say so every time.

## 4. Rig A's tag contents are unknown

**Repo: `ChameleonUltra`** notes if it is about cu1; **`Momentum-Firmware`** if it is T5577 work.

Read them before assuming anything, write down what you find. Chameleon 1 writes T5577s and has raw
`lf t55xx` block access, so Rig A is self-sufficient for the successor project. ⛔ Never flash cu1.

## 5. Queued, needs the operator

- `fdxb` `emu.pm3 → rd.cu2` SILENT while `t55.pm3 → rd.cu2` is EXACT — pm3's own `lf fdxb sim`
  or our reader. Ambiguous (run 20260916_161528).
- `em410x` `pm3·emu` and `fdxb` `cu1·emu` read `⁇` — need `--repeat 10`.
- `t55.pm3 → rd.cu2` for everything: gone while Rig B is tagless.

## 6. Registry work, no bench

**Repo: `rfid-tools`** — the registry is the harness. `./runtests`.

- `em410x_electra`: refuse the `rd.pm3` column **permanently** — the Proxmark cannot tell Electra
  from plain em410x and has no flag for it (measured 2026-09-16). Do **not** record `2244668800`
  as its expectation. Our `cu_read` is genuinely missing and is real work.
- `indala224` `cu_decode_marker` is `Indala224 PSK1`; `lf indala write --help` says `--224`
  configures **PSK2**. One of them is wrong — check before trusting either.

## 7. When 1–6 are done or blocked

**Repo: whichever owns the code you are tidying.** Upstream prep is `ChameleonUltra`.

Tidy the codebase behind the 467 tests, then upstream prep (`AUTOPILOT.md` §2d/§2e). Then hand off
to the T5577 project (§5).
