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

### ⇒ THE NEXT EXPERIMENT, AND IT IS WELL-DEFINED

We know *what* is wrong, not *why*. `emit_entry` asks for `counter_top` 16 at a 1 MHz base clock
with duty 8 — a 62.5 kHz square — and the air carries a constant level per entry. Two
candidates, and **nothing on this bench has ever exercised the difference**: the fastest thing any
passing arm emits is its bit rate (2–8 kHz), so **the modulator's bandwidth above that is
simply untested**.

| candidate | how to separate it |
|---|---|
| the PWM is not toggling within an entry (duty ignored, or the pin is driven from the polarity bit alone) | install a synthetic buffer that alternates at a KNOWN rate and capture it |
| the analog modulator cannot follow 62.5 kHz | the same sweep: find the rate at which the air stops following |

⛔ **`hw emuhold` CANNOT do it as it stands** — `lf_tag_em.c:1050` refuses 1MHz types
outright, and it holds levels at `PAC_HOLD_RF_PER_BIT` (256us), so its fastest alternation is ~2
kHz. ⇒ The experiment is a **small, well-scoped firmware change**: let `lf_tag_em_seq_hold` accept
the 1MHz types and take the counter_top as a parameter, then sweep the alternation rate from the
bit rate up through 62.5 kHz and find where `pm3cap` stops seeing it. **Flashing cu2 needs no bench
move** (`enterdfu.py`), and ⛔ never cu1.

⭐ The air check on the tagless Rig B is available for any fix: arm cu2, read with the
Proxmark, disarm in a `finally`. A fix that turns one of the six EXACT is real evidence — and
**ungraded**; say so every time.

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
