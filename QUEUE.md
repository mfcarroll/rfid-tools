# Work queue — newest decisions at the top of each item

⭐⭐⭐⭐⭐ **READ IN THIS ORDER**: the bench state below, then the newest `##` section, then
**WHERE THE NEXT TICK STARTS** — everything after them is the round's detail and its method
rules, newest first. ⛔ **Find those by their TITLES, never by a line number** — this line used
to say *both around line 206* and was wrong by 190 lines within a day, which is the same stale
-pointer disease the sections below keep finding elsewhere.

⛔ The blocks further down are HISTORY: several of their claims were **retracted or scoped inside
the same round**, and each carries its own pointer. **Do not quote a level or a rate from them without reading its pointer.**

✅✅ **BENCH STATE 2026-09-17 21:5x — UNCHANGED, AND NOTHING IS OUTSTANDING ON THE HARDWARE.**
⭐ cu2 is on the **burst-500** build (31 frames, asked), mode **`Tag Reader`** (asked). ⛔ **Nothing
flashed, nothing armed and no bench move since 17:3x** — the 20:5x and 21:xx ticks were offline
throughout. **cu1 has never been touched.** ChameleonUltra `indala-psk-read` is clean at
**`9b8b81eb`**, `rfid-tools` on `main`, `./runtests` **488** green.
⚠ **The next hardware step is K34b's flash, and it is deliberately NOT started** — see the K34b
section for the reason and the full pre-registered sequence.

**— the 17:3x block, kept because it is what the restore was verified against —**

✅ **K34a RAN AND THE BENCH IS BACK AS IT WAS.** cu2 was flashed to a burst-1000 build, used for two of the four
caps, and **flashed back**; `hw emudebug` reports **31 frames per burst**, verified after the
restore. ⭐ **cu1 was never touched.** The ChameleonUltra tree is clean at **`762cbf13`**, which
reverts the experimental constant — ⛔ the burst-1000 constant is **not** a proposal and must
never reach a branch as a change.

⭐ Both DFU zips are kept at `/Users/Shared/code/personal/rfid/.tools/builds/`
(`k34a-b500-dfu-app.zip`, `k34a-b1000-dfu-app.zip`, plus `fallback-df053dd-b500-dfu-app.zip`), so a
re-run needs **no rebuild** — flash, then confirm **31 vs 62 frames by asking the device** (C461).
⚠ `enterdfu.py` failed to TRIGGER once in four attempts with nothing flashed; retry, do not
suspect the device.

## ⛔⛔ 2026-09-17 21:08 PDT — **THE STOP HOLDS AT THE NEXT FIRE, AND THE TWO BRIEFS DISAGREE ON ITS NUMBER**

⛔ **`util5=15.0 mins5=170 util7=98.0 mins7=3050`** — logged per §3. Unchanged from the reading that
stopped the previous tick. The clock condition (Sun 2026-09-20 00:00) is still ~50.8 h away, which
`mins7=3050` independently confirms. ⇒ **the round is still stopped, on the same condition, and
this fire did no work beyond recording that.**

⚠⚠ **THE SCHEDULED-TASK FILE AND `AUTOPILOT.md` §3 CARRY DIFFERENT CAP THRESHOLDS, AND AT 98.0 THEY
GIVE OPPOSITE ANSWERS.** This is not a rounding quibble — it decides whether a fire works or stands
down, and it will keep deciding it at every fire until the operator reconciles it:

| source | threshold | verdict at `util7=98.0` |
|---|---|---|
| `AUTOPILOT.md` §3 table | `util7 >= 98` | **terminal — stop** |
| the routine's own tick prompt, STEP 3 | `util7 > 99` | keep working |

✅ **Resolved in favour of §3, the stricter one, and here is the reasoning rather than a coin toss:**

1. ⭐ **§3 gives its threshold a stated purpose** — *"the last 2% is reserved so the routine and its
   wakeups cannot themselves fail for want of capacity."* The prompt's `> 99` states a number and
   no rationale. A reserve with a reason behind it outranks a bare figure when the two collide and
   nobody can be asked.
2. ⭐⭐ **The previous tick already DECLARED this stop and committed it** (`fa85bab`). §3 is explicit
   that terminal means *"do not wait for more capacity and do not check again"* — **there is no
   second phase.** A later fire that reopens a declared terminal stop on a looser threshold is the
   re-arming failure §3 is written to prevent, just arriving through the prompt instead of through
   the 7-day reset.
3. ⚠ **The asymmetry favours stopping.** Standing down wrongly costs some ticks in a window that
   resets Sunday, before the operator returns ~22 Sep. Working wrongly spends the reserve that
   keeps the routine's own wakeups alive — and §3 already says reaching the ceiling *"is the
   intended outcome, not a fault."* There is nothing on the list that is urgent enough to buy with
   the reserve: item 1 (K34b) is explicitly *"do not start without room to finish it"*, item 2 is
   deliberately the operator's, and item 4 needs hands.

⭐ **FOR THE OPERATOR — this needs one edit, not a judgement call each fire.** Either raise §3's
table to `> 99` or lower the routine's STEP 3 to `>= 98`, in whichever direction you actually meant.
⛔ Until then every fire burns a little capacity re-deriving the above, which is the exact cost the
reserve exists to avoid.

⚠ **Minor, noted in passing, no action taken: this file's section timestamps run ~1 h ahead of the
system clock.** The section below is headed *22:1x* and its commit `fa85bab` is stamped
`21:07:41 -0700`; this fire's `date` says `Thu Sep 17 21:08:59 PDT 2026`. ⇒ **the "newest at the
top" ordering cannot be checked against `git log` while the two disagree**, and a future tick
comparing a header to a commit time will think it has found an hour-long gap that never existed.
The headings, not the commits, are the ones that drifted.

### ⭐ WHERE THE NEXT FIRE STARTS

⛔ **It does not start.** Read `util7`, compare it to §3, and if it is still `>= 98` say so in one
line and stand down — **the work list below is unchanged and still correct**, and nothing above
supersedes it. The round resumes only on the operator's word, not on a window reset: the clock
condition at Sun 2026-09-20 00:00 is precisely what keeps the reset from restarting it.

## ⛔⛔⛔ 2026-09-17 22:1x — **ROUND STOPPED: `util7` REACHED 98. TERMINAL, NOT A PAUSE (§3)**

⛔ **`util7=98.0` at 22:1x** (96 at tick start, 97 for most of the tick). AUTOPILOT §3: *the week's
allowance is spent*, the last 2% is reserved so the routine and its wakeups cannot themselves fail
for want of capacity. ⛔ **Do not wait for capacity and do not check again.** ⚠ The other terminal
condition — the clock passing **Sun 2026-09-20 00:00** — has NOT been reached, and it is what keeps
the cap from re-arming when the 7-day window resets. **Both still bind.**

⭐ **Everything below was committed as it was finished; nothing is left uncommitted in any of the
three repos.** `rfid-tools` on `main`, `./runtests` **488** green · ChameleonUltra
`indala-psk-read` at `e14f355e`, `gate` and `checkdocs` clean · Momentum-Firmware
`t5577-deep-read` at `c384392f0`, its `./runtests` **143** green. ⛔ **Nothing pushed** — a push to
any of those branches was not checked against an open PR and the operator is not reachable to ask.

### ⭐⭐ THE WORK LIST, FORWARD — in the order a tick with headroom should take it

1. ⭐⭐⭐ **K34b's FLASH AND CAPTURE.** Fully designed, costed, gated, and implementation-checked
   this tick — **the only thing it lacks is headroom.** Its section above carries the pre-registered
   ladder **verbatim**, the three-number gate, both no-verdict meanings, the flash sequence in
   order, and the arithmetic for why the pinned 5 ms design could never have returned ELAPSED.
   ⛔ **Do not re-derive any of it, and do not start the sequence without room to finish it** — a
   cut after the flash leaves cu2 on a non-standard build for the rest of the absence.
2. ⚠ **The `bench state` licensing question** — measured, blast radius zero today, and ⛔ **left for
   the operator on purpose**: it is a licensing decision, which is the one class this project exists
   to be careful about. Its section has the numbers and both candidate remedies.
3. ⭐ **The T5577 project's own queue**, entered through **its own `AUTOPILOT.md` then its
   `QUEUE.md`** (⛔ not through this file's §1/§3/§4 — §5 has been corrected). **Its pinned next unit
   is now the PROBE**: `analyse_fold_reach.sh` compiles ~35 functions out of the shipped firmware
   source, so covering the last six `analyse_*.py` needs a compiler and no bench. ✅ The trap that
   would have fired on that path — a test asserting the probe's *absence* — was removed this tick.
   ⚠ **Two of those six have no test at all**: `analyse_corpus_reads`, `analyse_ladder_settles`.
4. ⛔ **§2a / §2b / §2c are the operator's**: the emitter architecture is priced and awaiting their
   cost/benefit; the two `⁇` cells and `fdxb emu.pm3 → rd.cu2` need hands.

### ⚠ WHAT THIS TICK DID NOT DO, SAID PLAINLY

⛔ **No bench work of any kind.** Nothing flashed, nothing armed, no device opened, no capture
taken, cu1 never touched, Rig A's tag never touched, nothing moved. ⇒ **not one graded cell moved,
and none could have** — `git diff` over the whole tick touches no `expect`, no decode marker, no
`flip_key` and not one line of `outcomes.py`, and the largest banked session regrades at this head
with *"No outcome moved."* ⭐ Every result above is a host test, an arithmetic check, an offline
simulation or a re-analysis of banked captures. **None of them is a bench verdict.**

## ✅ 2026-09-17 22:0x — **§2e's PLAN CHECKS OUT, AND §5's HANDOFF PREMISE DID NOT**

⭐ Both offline, both the same job: **the brief's own pointers, checked against the tree instead of
believed.** This tick found four stale surfaces in the harness; these are two more in the notes.

1. ✅ **§2e — the upstream plan's numbers all hold**, re-derived from `data_cmd.h` rather than from
   the note: **3033-3062 = 30 ids**, **5014-5031 = 18**, **both contiguous with no gaps, 48 total**;
   `LF_EMU_DEBUG` 3037 · `LF_RADIO_DEBUG` 3038 · `LF_READER_CAPTURE` 3060 are exactly the three
   instrumentation ids named; **shippable subset 41.** ⛔ **The one defect is the pointer a
   maintainer would actually open** — `NEXT.md` said the gate is `Makefile:431` and the
   `-DLF_RESEARCH_CMDS_ENABLED=1` is at **432** (431 is its comment). ✅ Rewritten to quote the
   line's **text**, not its number. ⇒ **an off-by-one on the single pointer attached to a 48-id
   patch is the cheapest possible way to look careless.**
   ⚠ **And my first scan of `data_cmd.h` returned ZERO ids** — the regex expected `= 5014` where
   the file writes `#define NAME (5014)`. I nearly reported the ranges as gone. **Suspect the
   instrument first.**

2. ⛔⛔ **§5's HANDOFF PREMISE WAS STALE AND IS NOW CORRECTED IN `AUTOPILOT.md` ITSELF.** It said
   the T5577 deep-read project *"has its own tracking … but **no offline process**"* and told the
   next tick to carry §1/§3/§4 across. **It has its own now**, and has been worked since the
   2026-09-16 handoff: its **own `AUTOPILOT.md`** (153 lines), its **own `QUEUE.md`** (269), its own
   **`./runtests` — 143 tests in 6.0 s**, its own `usage_check.sh`, a `run_gates.sh` and roughly
   130 `verify_*.sh` beside ~25 `analyse_*.py`. ⇒ ⭐ **the handoff is now *read that directory's
   brief, then its queue, and work ITS list under ITS rules*** — ⛔ **do not import this file's
   sections over a project that has written its own, which is how two briefs come to disagree with
   nobody noticing.**
   ⚠ **Carry this when you go there:** its `QUEUE.md` still opens with *"Nothing in this file has
   been worked yet"* and then contradicts itself further down (item 1 is ✅ STARTED, `./runtests`
   built at `ba05cc6a3`). **Believe the item, not the header**, and tidying that header is a
   worthwhile first unit there.

⇒ ⭐⭐ **WHERE THAT LEAVES THE LIST.** §2a is the operator's cost/benefit; §2b and §2c are
operator-return; §2d and §2e are done to the point where the next step needs hardware or a human;
**K34b is fully designed, costed, gated and implementation-checked and is parked on the FLASH for
want of headroom** (see its section). ⇒ **the genuinely available offline work now is the T5577
project's own queue**, entered through its own brief.

## ⚠⚠⚠ 2026-09-17 21:5x — **A LATENT DEFECT IN `bench state` WITH A BLAST RADIUS OF ZERO TODAY — MEASURED, RECORDED, AND DELIBERATELY NOT ACTED ON**

⭐ A **regrade sweep of all 20 banked sessions** (no bench, no device — AUTOPILOT's own
"real measurement, no hardware" loop). ⛔ **A regrade is not a bench verdict and moves no cell.**

✅✅ **FIRST, THE CHECK THIS TICK OWED ITSELF, AND IT PASSES BY CONSTRUCTION RATHER THAN BY
ASSERTION: nothing this tick did can move a cell.** `git diff a0e169d..HEAD` touches **no**
`expect=`, **no** `_decode_marker=`, **no** `flip_key=` and **not one line of `outcomes.py`** — and
the largest banked session regrades at this head with **"No outcome moved."** ⇒ the harness changes
are refusal-path and validation only.

⛔⛔ **THE DEFECT, WHICH IS REAL: `state.gather` READS EACH CELL'S OUTCOME AS FILED AND SKIPS
`UNGRADED` WITH `continue` — *"the run could not judge it; it is not an answer"*.** That was true on
the day and is exactly what `--regrade` refutes: the transcripts **can** now be judged, because the
registry gained what was missing. ⇒ **a cell a later registry correction made judgeable is invisible
to the state view for ever**, and the state view is what AUTOPILOT quotes when it says what our
emulation does.

⭐ **THE SWEEP, WITH BOTH DIRECTIONS, BECAUSE ONE OF THEM INFLATES:**

| direction | readings | what it is |
|---|---|---|
| `UNGRADED` → `EXACT` | **27** | corrections since made the session's own gold row readable |
| `UNGRADED` → `SILENT` | **6** | same, and they are the known emitter gaps |
| `UNGRADED` → `WRONG` | 1 | same |
| ⚠ **`EXACT` → `UNGRADED`** | **2** | ⛔ **`fdxb t55.pm3→rd.cu1` and `t55.cu1→rd.cu1`** — the corrected fdxb marker/expectation **retracts two published passes** |

⇒ **34 readings over 6 sessions, 30 distinct cells** — and ⭐ **the 2-reading direction is the
dangerous one**, because reading as-filed would keep asserting a pass the registry has since
withdrawn. **An under-report hides work already paid for; an over-report publishes a result that is
no longer true.**

✅✅ **AND THE BLAST RADIUS TODAY IS ZERO — CHECKED CELL BY CELL, NOT ASSUMED:**
1. **29 of the 34 are about `cu1`**, whose firmware has changed since, so `gather`'s own rule
   (*a reading whose devices are no longer running what they were is dropped*) already discards
   them — including **both** `fdxb` over-reports.
2. Of the 5 that survive the firmware rule, **4 do not move** under a regrade at all.
3. The one that does — **`viking t55.pm3 → rd.cu2`, EXACT was UNGRADED** — sits in
   `20260916_085441_**ABORTED**`, which `gather` skips by name, **and the cell is already EXACT in
   state from the later non-aborted `20260916_161528`.**

⇒ ⛔⛔ **SO IT IS PROTECTED ONLY INCIDENTALLY, BY TWO GUARDS AIMED AT SOMETHING ELSE.** It bites the
moment either changes: a cu1 restored to its old build, or a fresh run that banks `UNGRADED` cells
which a later correction makes judgeable. ⚠ **Nothing warns when that happens**, and the sweep that
found it is four shell lines.

⛔⛔ **AND IT IS DELIBERATELY NOT FIXED HERE — THIS IS A LICENSING QUESTION AND THEREFORE THE
OPERATOR'S.** The fix looks obvious (make `gather` regrade, or republish the `.json` in place) and
the argument for it is sound — the licence comes from **that session's own** gold row and null
sweeps, so nothing is carried across sessions; only its *interpretation* was missing. ⛔ **But
AUTOPILOT §1 names *a licence carried across a multi-day block* as precisely the defect the project
exists to prevent, and this project was created because cells were published without a calibration
row.** A tick that quietly re-licensed 30 cells to make a number look better would be that failure
wearing a better argument. ⇒ ⭐ **put it to the operator as a decision, with the numbers above; do
not implement it on a tick's authority.**

⚠ **The `.json` is what `state` reads and `--regrade -o` writes only `.md`**, so republishing does
**not** reach the state view. Whoever takes this up should know that before choosing a remedy.

## ⭐⭐⭐⭐ 2026-09-17 21:4x — **ONE INSTRUCTION, FOUR SURFACES, FOUND IN THE REVERSE ORDER OF HOW MUCH THEY MATTERED**

⭐ Offline, in this repo, tests green throughout. **`./runtests` 475 → 483.** Nothing flashed,
nothing armed, no bench move.

⛔⛔ **Electra's `rd.pm3` refusal was fixed yesterday in the PLANNER. The instruction it removed —
*go and record the token* — was still being published by three other surfaces, and the one that
would have done the damage was the LAST to be looked at:**

| # | surface | what it said | why it mattered |
|---|---|---|---|
| 1 | `plan._refuse` | fixed 2026-09-17 | the published refusal |
| 2 | `bench scope`'s *expectations known* column | **"— none; `bench learn` them"** | ⚠ advice only |
| 3 | ⛔⛔ **`bench learn` itself** | **nothing — it accepted the request** | ⛔⛔ **it writes the value down** |
| 4 | `plan`'s `unlicensable` remedy | **"`bench learn` … would settle it"** on all four reasons | ⚠ false for three |

⛔⛔⛔ **SURFACE 3 IS THE ONE TO REMEMBER. `_why_not_learnable` has four checks and Electra passed
every one** — the Proxmark has a clone command, a read command and a decode marker — so it returned
`None`, and **a bare `bench learn` with no arguments sweeps all 18 tier-0 arms**, Electra included.
It would have wiped and written the tag, read it, and recorded `2244668800` as Electra's `rd.pm3`
expectation: **byte-identical to plain `em410x`'s, which is the false pass the registry row, the
planner and `bench scope` all forbid.** ⇒ ⭐ **nobody had to name Electra to reach it, and the two
surfaces that refused it were the two that could not write anything.**
✅ Refused now, ordered FIRST for the same reason `plan._refuse` orders its own — **an unmeasured
protocol and an indistinguishable one both arrive with `expect = None`, so every generic check
passes for both and the bare absence cannot tell them apart.** ⭐ And scoped to the reader that
cannot answer: **`rd.flip` stays learnable**, because the Flipper alone distinguishes Electra and a
blanket refusal would throw away the one judge that works.

⛔ **SURFACE 4 GENERALISES THE DEFECT BEYOND ELECTRA: a remedy appended to reasons it cannot
remedy.** For `fdxa` the planner recommended **the very command that refuses the request** (no
clone signature ⇒ `bench learn` has no gold tag to write); for `instafob` it recommended **writing
a T5577 as the remedy for a T5577 being unable to hold it.** ⇒ ⭐ **a remedy offered for a reason it
cannot remedy is worse than no remedy — it sends the next session to spend a bench move proving the
note wrong, with the tool's authority behind it.** ✅ Each branch now names a remedy that fits, and
every branch that cannot be settled by learning says so in **one phrase the product owns** so a
test can key on it instead of sniffing prose.

⭐⭐⭐ **THE CARRYABLE LESSON, AND IT IS A TEST SHAPE RATHER THAN A FACT: EACH SURFACE WAS
INTERNALLY CONSISTENT, SO NOTHING BUT A CROSS-SURFACE INVARIANT COULD FIND THIS.**

> **If a refusal's text recommends an action, the code that performs that action must accept it.**
> `tests/test_plan.py` now sweeps **every rule × 4 readers × 5 sources** and holds it over the
> **170 refusals that do recommend `bench learn`** — asserting the count so it cannot quietly go
> vacuous. ⭐ **Swept: 0 contradictions. There is no fifth surface.**

⚠⚠ **AND IT CAUGHT ITSELF TWICE, WHICH IS THE ONLY REASON TO TRUST IT.** (1) Its first version
failed on the first wording of its own commit — the `instafob` branch said *cannot either* instead
of the agreed phrase. (2) Its first version swept `unlicensable` alone and guarded an **empty**
subset, because every unlicensable protocol sits in a *cannot settle it* branch: **an invariant
that checks nothing is the exact failure mode it was written against**, and it said so in its own
docstring before being widened.

✅✅ **AND THE CONSEQUENCE WAS CHECKED RATHER THAN ASSUMED: `learned.json` holds 14 records,
NONE of them `rd.pm3`, and its single Electra record is the Flipper's CORRECT distinguishing value
`22446688007E1EAA` (session 20260915_233837).** ⇒ **the defect was real and reachable but never
fired.** ⚠ Zero `rd.pm3` records also means every `rd.pm3` expectation in the registry is a
hand-written constant, which is what `test_learn_command.py`'s own docstring says and is a separate
standing weakness — no provenance, nothing to replay against.

⭐⭐⭐ **THEN THE DANGER WAS GENERALISED INTO `reg.validate()`, WHICH IS THE PART THAT OUTLIVES
ELECTRA.** Grading is a byte-exact match, so **two protocols holding the same token for one reader
cannot attribute a decode and each would pass the other's cell.** Nothing refused that in general,
and ⛔ **it needs no bad measurement to arrive — only a plausible one written down.** Two invariants
now fire for **every command**, not just under the test runner:

1. ⭐ **No two protocols may share a byte-exact `expect` / `cu_expect` / `flip_expect`.** Swept:
   **19 · 18 · 4 values, 0 shared.** ⚠ **The world is allowed to share a token; the registry is
   not** — `lf em 410x reader` really does print `2244668800` for both, and the sanctioned way to
   say so is `expect = None` plus `PM3_INDISTINGUISHABLE`. ⇒ **a collision is not *the bench is
   ambiguous*, it is *someone recorded the ambiguity as an answer*.**
2. ⭐ **Membership of `PM3_INDISTINGUISHABLE` and a recorded `expect` are contradictory** and are
   refused as such, because holding both makes the planner's permanent refusal depend on **which
   rule happened to be checked first**. ⛔ **Invariant 1 does not cover this** — it fires only when
   the shared token's other owner is *also* registered, true for Electra today and not guaranteed
   for a future member. This one needs no twin.

✅ **Also corrected while here:** `SCOPE.md` called `em410x_electra` and `indala224` *the cheapest
item in this whole document* and tiered them **0b — FREE**. ⛔ Both were measured since and neither
is cheap — Electra is unanswerable here, `indala224` needs a tag — so a cold tick reading SCOPE.md
would have spent a unit rediscovering it. Struck through in place with pointers, not deleted.
⭐ And `SCOPE.md`'s counts were re-checked against `./bench scope`: **22 protocols, emulate 18 ·
scan 21 · write-to-T55xx 21, still agreeing** — ⚠ against the REGISTRY, which is source-derived;
that is not a bench verification of any single ✔. `bench learn --help` also said *16 tier-0 arms*
where the registry has **18**.

## ⭐⭐⭐⭐⭐ 2026-09-17 21:2x — **K34b's PINNED BAND CANNOT RETURN ELAPSED. THE REPLACEMENT IS COSTED, AND IT IS CHEAPER THAN K34a (C557, M86)**

⭐⭐ **OFFLINE, NO FLASH, NO DEVICE, NOTHING ARMED, NO BENCH MOVE** — and it found a fault that
would have spent the flash and both caps and come back looking like a working experiment.
`k34bsim.py` (new, committed `000dea4a`) is `k34sim.py`'s sibling and does item 3 of the list below.

⛔⛔ **THE FAULT IS ARITHMETIC, NOT POWER: K34b's TWO WINDOWS ARE NOT COMPARABLE.**

    SAMPLES   nominal 140-145.   width 5.0 ms, position EXACT — no stretch enters, because a
              sample count is what the ladder asks for.
    ELAPSED   nominal 140/S..145/S.  width 5/S = 2.7-3.2 ms, and its POSITION is uncertain over
              76.4-93.0 because C556 measured S at 1.559-1.833.

⇒ **the ELAPSED feature is ~2.9 ms wide inside a 16.6 ms window — we are ignorant of where it sits
by 5.6x its own width.** Two faults follow, and the first is fatal on its own:

1. ⛔⛔ **On the pinned 5 ms grid the ELAPSED feature occupies 0 OR 1 cells** — it can fall between
   two ladder points and miss the ladder entirely — **so `>= 2 elevated cells` cannot fire on
   ELAPSED at all.** The band could only ever return SAMPLES or NO VERDICT. ⭐ **A band that can
   return only one of its two answers is not an experiment.**
2. ⛔⛔ **At 2.5 ms it occupies 2 cells only 19.1% of the time, so `k_E = 2` is met — four times in
   five — by ONE region cell plus ONE baseline cell that happened to clear.** It simulates at
   **76.4% power against 3.8% false-fire** and is still broken. ⇒ ⭐⭐⭐ **M86: NEITHER A POWER NOR
   A FALSE-FIRE FIGURE CONTAINS THIS. Both were computed, both looked fine.** What exposes it is
   the **occupancy** — how many cells the feature can occupy at that grid, over the whole range of
   the parameter that places it, **not at the point estimate** (at S=1.71 it reads 1 cell, at
   S=1.80 it reads 2). ⛔ Require `k <= min(occupancy)` to fire at all and `k <= median(occupancy)`
   for the fire to be the feature's rather than the noise's.

✅✅ **THE DESIGN THAT SURVIVES — PRE-REGISTERED HERE, AND IT IS HALF K34a's COST:**

> `idteck` only, `--dec 2`, **1.0 ms grid inside both windows** over a 5 ms background **70-150**
> (39 cells), **`k_E = k_S = 3`** (occupancy 2-4, median 3 ⇒ the region supplies `k_E` itself 92.1%
> of the time), **`--reps 32`**, `--per-arm-shuffle`, **two fresh seeds**.
> ⇒ **2,496 reads against K34a's 4,864.** The finer grid is paid for by dropping `keri` and the
> second condition, neither of which K34b needs.

| region height | false-fire E / S | power E-truth / S-truth | no-verdict |
|---|---|---|---|
| **0.725** (measured, nominal 110, 58/80 pooled) | **2.4% / 0.0%** | ⭐ **95.6% / 99.5%** | 4.4% / 0.5% |
| 0.65 | 2.4% / 0.0% | 91.5% / 99.5% | 8.5% / 0.5% |
| 0.60 | 2.4% / 0.0% | 83.9% / 98.8% | 16.1% / 1.2% |
| **0.55** ⭐ **the gate's bar** | 2.4% / 0.0% | **70.5% / 94.6%** | 29.5% / 5.4% |
| 0.50 | 2.4% / 0.0% | ⛔ 53.0% / 77.9% | 47.0% / 21.9% |
| 0.45 | 2.4% / 0.0% | ⛔ 33.8% / 45.3% | 66.2% / 54.5% |

⛔⛔ **THESE REPLACE THE FIRST SET THIS TICK PUBLISHED, AND THE CORRECTION MATTERS (C558).** The
tool computes its ladder two ways — `ladder()` builds the cells, `occupancy()` counts what the
feature can fill — and **asked whether they agreed, they did not: 662 disagreements of 1,203.**
`ladder()` was anchoring its fine grid on the **window's edge**, emitting cells at 76.4, 81.4,
86.4 — nominal values no ladder would be asked for. ✅ Fixed, re-cross-checked at 0; the ladder is
**35 cells not 39**, the ELAPSED window **17 not 20**, the cost **2,240 reads not 2,496**.
⛔ **The two faults and the design above survive unchanged** — the anchor moves which cells exist,
not the occupancy distribution. **What moved is the cliff, in the uncomfortable direction:** a
narrower window means less false-fire (2.4% not 5.5%) but also less of the noise help that was
flattering the pessimistic cases, so **power at height 0.50 fell 71.5% → 53.0%, from over the bar
to well under it.** ⇒ ⭐ **the gate's bar is the region's height `>= 0.55`, not 0.50.**
⭐⭐⭐ **AND NOTHING IN A RE-RUN WOULD HAVE FOUND IT** — the figures were internally consistent
with the ladder actually simulated. ⇒ **when a tool computes one quantity by two routes, make them
argue** (M86's addition; M45 with the instrument being software).

⛔ **THE 5.5% vs 0.0% ASYMMETRY CANNOT BE EQUALISED AWAY** — raising `k_E` to 4 exceeds the median
occupancy and re-creates fault 1. It is structural: ELAPSED's window is 3.3x wider **because we are
ignorant of S**, not because the physics is broader. ⇒ **state it, do not hide it.**

⭐⭐⭐ **AND THE GATE FALLS OUT OF THE SAME SIMULATION — M85 APPLIED BEFORE THE FLASH INSTEAD OF
AFTER. Everything turns on the region's HEIGHT at dec 2 on the new build, and it cliffs between
0.50 (71%) and 0.40 (26%).** That height is measurable from a **coarse** pair — 5 ms over 70-150,
reps 16, **336 reads** — and `k34bsim.py --from` reads it directly.

> ⭐ **THE SEQUENCE, IN ORDER, AND NO STEP IS OPTIONAL:** flash cu2 to the banked burst-1000 zip ·
> verify **from the AIR** (C461: 62 frames asked, `hw emuseq` 64 entries / `seq repeats` 15, P1
> clean at 0.50) · **re-fit S with `dectime.py --interval` on the new build** (⭐ the ELAPSED window
> is a FUNCTION of it — M79/C547, a new binary is a new condition) · **coarse gate pair** ·
> `./k34bsim.py --from <those caps>` · ⭐ **both powers >= 70% ⇒ capture the 1 ms pair** ·
> ⛔ **< 70% ⇒ do not capture, and that is a statement about the bench that day, not about the
> burst.** ⛔ **Never the same caps for the gate and the verdict.**
> ⛔ Disarm cu2 (`hw mode -r`) in a `finally` on every capture, and `lf config --reset` after
> `dectime.py`.
> ⭐⭐⭐ **THE GATE'S BAR IS THREE NUMBERS, NOT ONE (C559): E-power >= 70% AND S-power >= 70% AND
> E-FALSE-FIRE <= 5%.** The *region height >= 0.55* above is what the first two come to at the
> six-cap grounding; ⛔ **the third is not implied by them and it bites.**

⛔⛔ **AND THE GATE'S OWN CODE PATH WAS BROKEN UNTIL IT WAS EXERCISED — IT WOULD HAVE CRASHED
AFTER THE FLASH, MID-SEQUENCE, WITH cu2 ON A NON-STANDARD BUILD AND NOBODY PRESENT (C559).**
`_cap_sigma()` paired its caps as `(0, 2, 4)` — the six banked dec-2 caps' three same-condition
pairs — so the **two** caps the gate passes raised `IndexError`. ✅ Fixed to pair over whatever is
given, and ⛔ **it now refuses on a single cap rather than returning 0**: a silent 0 deletes the
noise source M84 exists to model and **inflates every power figure**, which is the one direction a
go/no-go must never be wrong in (M78). ⭐ **Found by running `--from` before the flash instead of
during it — M81 for the third time this tick, and the third time it paid.**

⭐⭐⭐ **AND THE SUBSTANTIVE HALF, WHICH IS WHY THE BAR GREW A THIRD NUMBER: THE MARGIN IS A
PROPERTY OF THE GROUNDING, AND THE GROUNDING WANDERS.** Ground the same design in only the `k32`
pair instead of all six caps and the baseline moves **0.188 → 0.282**, its SD **0.115 → 0.150**,
`cap_sigma` **0.061 → 0.092** — and **E's false-fire goes 2.4% → 16.7% while its power stays a
healthy 88.3%.** ⇒ **a power floor alone passes a day on which a fire is worth little.** ⚠ This is
**M70's original lesson arriving by a new route** (Y2: pre-registered, replicated, 41% false-firing
with nobody having computed it) — ⭐ **a band can be re-invented carrying the same hole a hundred
claims later, so compute the false-fire every single time.**

✅✅ **AND M81's CHECK IS DONE — THE DESIGN SURVIVES INTO THE IMPLEMENTATION, VERIFIED OFFLINE
RATHER THAN DISCOVERED AFTER THE FLASH.** M81 is the round's most expensive lesson and this is
exactly its shape: a requirement computed in a design note has to be expressible by the tool.

1. ✅ **`burstsync.py --primers` takes fractional cells and renders integral ones as `"100"` not
   `"100.0"`** (the K32 comment at the parse site says so), so cell keys and scorer matching are
   safe. ⭐ **And at 1 ms every cell of this ladder is an INTEGER anyway** — there are no
   fractional keys at all. ⇒ **the ladder, verbatim, so nobody re-derives it (35 cells):**

       --primers 70,75,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,95,100,105,110,115,120,125,130,135,140,141,142,143,144,145,150

   and ⭐ **the coarse GATE pair (17 cells, 5 ms, reps 16):**

       --primers 70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150

2. ⭐⭐ **THE LADDER TOP CHECKS OUT AND IT INDEPENDENTLY REPRODUCES THE PINNED DESIGN'S OWN TWO
   PERCENTAGES**, from `burstsync.py`'s corrected C548 formula `(burst − 85 − probe_ms) / per`,
   with `idteck`'s probe `lf read -s 6144` = 69.3 ms:

   | burst | dec 2 top, `idteck` | where 140-145 sits |
   |---|---|---|
   | 500 | **138.2** nominal ms | ⛔ **101%** — above it, which is M82's failure mode and why K34b was blocked |
   | 1000 | **338.1** nominal ms | ✅ **41-43%** — and this ladder's top, 150, is at **44%** |

   ⇒ **the design note's *101% of the reachable top* and *41% of it* both fall straight out of the
   formula**, which is two independent routes to the same numbers agreeing. ⛔ **And it says the
   gate pair cannot be rehearsed at burst 500 either** — 140,145,150 are above that build's top —
   so the coarse pair must be captured AFTER the flash, exactly as the sequence has it.
   ⚠ One caveat worth carrying: the formula's own dec-2/dec-1 cost ratio is **1.774**, which sits
   at the **upper edge** of C556's measured 1.559-1.833. At the low end the top would be ~356
   rather than 338 — either way 150 is comfortable, so it changes nothing here, but a design that
   pushed toward the top would need the measured interval and not this constant.

⛔ **THE NO-VERDICT BRANCHES, GIVEN MEANINGS IN ADVANCE (M74):** *neither window fires* ⇒ the
feature did not replicate at dec 2 on this build at all — a statement about the run's sensitivity,
and ⛔ **not** evidence for either alignment. *both fire* ⇒ the ladder carries structure the design
does not account for; report the profile and stop, do not pick the stronger.

⚠ **IT DOES NOT REOPEN THE DECIMATION LINE** (closed twice, C545-C548 and C556). It is the **same
quantity** — the stretch's imprecision — biting K34b through the **window** rather than through an
alignment. ⇒ ⛔ **item 4 below said *K34b keeps a threshold band* as though a band escaped C556's
arithmetic. It does not escape it; it inherits it somewhere else, and now that place is costed.**

⚠ **GROUNDING, AND ITS LIMITS (M78/M80).** All of it from the six banked dec-2 caps, the only dec-2
ladders this bench has ever run: baseline **0.188 mean / 0.115 true SD** (binomial-deconvolved, 70
cells), `cap_sigma` **0.061**, and the one cell that replicated in **every** pair (nominal 110) at
**0.725**. ⛔ **All at burst 500, and K34b runs at 1000** — the LEVEL must be re-grounded on the
day; the widths and the grid arithmetic transfer, because they are properties of the stretch and
the ladder. ⚠ The height is **transferred** from nominal 110 to R4's cells, a different region: if
R4 is weaker at dec 2, every power figure above is optimistic.

⛔⛔ **THE FLASH WAS NOT STARTED, AND THAT IS A JUDGEMENT WORTH INHERITING RATHER THAN RE-MAKING.**
At `util7` **97** against §3's ceiling of **98**, the sequence above — flash · air verify ·
`dectime --interval` · gate pair · `--from` · the 2,240-read verdict pair — is **hours** of bench
time and certain to be cut in the middle. ⛔ **A sequence cut after the flash leaves cu2 on a
non-standard build for the rest of the absence**, which is recoverable (the fallback zip is banked)
but is a changed bench the operator did not ask for. ⇒ ⭐ **the flash needs a tick with real
headroom, not the tail of one. Everything that can be done without it has now been done: the
design, its power, its false-fire, its gate, its ladder string, its ladder top, and its gate's code
path.** ⚠ Note §3 expects this round to reach the ceiling well before Sunday and says that is the
intended outcome — so the next tick with headroom may well be the operator's own.

⭐ **Bench state at the end of this tick: UNCHANGED.** cu2 on the burst-500 build, mode `Tag
Reader`, nothing flashed, nothing armed, cu1 never touched, nothing moved. ⭐ util7 **96 → 97**
across the tick. ChameleonUltra `indala-psk-read` at `9b8b81eb` (C557 `000dea4a`, C558 `77bd6411`, C559 `14594869`, `--equalise` bounded `9b8b81eb`), **not pushed** (a push to that
branch was not checked against an open PR and the operator is not reachable to ask).

## ⭐⭐⭐⭐⭐ 2026-09-17 20:5x — **K34a IS ANSWERED. THE BURST DOES NOT MOVE THE REGIONS. K34b IS LICENSED (C554)**

⭐⭐ **AND IT COST NOTHING — no flash, no device, no new capture.** The four K34a caps that D1
called CONTROL FAILED were rescored with **K36**, a level-invariant statistic (design
`5a84084d`, scorer `d49204d5`, **both committed before any cap was scored**). Instead of
thresholding cells it asks whether the two BURSTS agree with each other as well as two SEEDS of one
burst do:

| | within | cross | **delta** |
|---|---|---|---|
| `keri` | +0.633 | +0.657 | **+0.024** |
| `idteck` | +0.709 | +0.740 | **+0.031** |
| **pooled** | **+0.671** | **+0.698** | ⭐ **+0.028** (bar **−0.15**) |

⇒ ✅ **SAME — the burst's length is a REACH knob.** Both arms clear the bar independently, the
margin is 0.18, and the simulated separation is total (SAME 100%, SCALED 0%, SHIFT 0%, FLAT 0.2%).
⭐ Its `within` figures reproduce `repro.py`'s banked numbers exactly — the machinery agreeing with
itself on data it did not compute.

⭐⭐⭐ **IT RUNS AGAINST ITS OWN FOREKNOWLEDGE, WHICH IS WHAT MAKES IT CARRYABLE.** K36 was designed
after K34a's **0-vs-4** hit difference was known — the shape of *the regions moved* — and it says
they did not. By the standing direction rule a SAME here is honestly carried where a NOT-SAME would
have been merely *consistent with what was already visible*.

⭐⭐ **AND IT DISSOLVES C549's CONFOUND RATHER THAN STEPPING AROUND IT.** The 0-vs-4 was confounded
with the level: the condition finding fewer regions was **also the noisier one** (+0.573/+0.667
against +0.693/+0.751). `delta` measures each condition against **its own** replication floor, so
that divides out by construction. ⇒ **the thing that made K34a uninterpretable is the thing this
statistic divides out.**

⛔⛔ **WHAT IT DOES NOT SAY — all pre-stated, none discovered afterwards:**
1. ⛔ **LOCATION, not amplitude.** Rank agreement is level-insensitive on purpose, and `idteck`'s
   burst-1000 pooled level (22.0%) really is lower. *The regions are where they were* is the claim;
   *the burst does not change how strongly they read* is **not**.
2. ⛔ **It does not rescue D1.** D1's verdict stands as CONTROL FAILED; C553's 28.6% power at this
   level is untouched. K36 **replaces the instrument**, it does not re-read the old one.
3. ⛔ **It cannot characterise** — SCALED, SHIFT and FLAT all land far below the bar together.
4. ⚠ Its −0.15 bar is calibrated by simulation on one measured profile, not an empirical null.

✅✅ **AND IT IS VALIDATED ON REAL DATA IN BOTH DIRECTIONS (C555) — a simulated separation is an
argument about a model; these are the banked caps.**

⭐⭐ **THREE NEGATIVE CONTROLS — same burst, different SESSION, TIME OF DAY and `--reps`** — read
**+0.038**, **+0.002**, **−0.035** against the verdict's **+0.028**. ⇒ **the whole real-data null
sits inside ±0.04**, and does so while `within` itself ranges **+0.573 to +0.784** — across exactly
the level wander C497/C549/C550 spent the round chasing. **The self-normalising property is
confirmed on the bench, against the biggest known nuisance on this line.**

⭐⭐⭐ **A POSITIVE CONTROL BUILT FROM THE REAL PROFILES — displace the burst-1000 condition along
the ladder**, which is the right control for a LOCATION claim since a shift moves only where the
profile sits: **one cell (5 ms) already fires NOT-SAME at −0.231**, then **−0.606 / −0.893 /
−1.071** at 2 / 3 / 4 cells. ⇒ ⭐ **C554's SAME means *the same place to within about one ladder
cell*, not *roughly the same place*.**

⛔⛔ **AND ONE REAL WEAKNESS THE SAME EXERCISE FOUND — CARRY IT: a SCRAMBLED condition (structure
destroyed, the FLAT truth) still reads SAME 6.5% of the time** (200 draws, mean −0.298) against the
idealised simulation's 0.2%. ⇒ **`delta` alone is NOT evidence the far condition HAS structure.**
⭐ What excludes FLAT is a different number in the same output — **the long burst's own seed
agreement, +0.722**, which collapses to ~0 under the scramble. `--k36` now prints it beside the
verdict. ⛔ **Read the two together; never quote the delta alone.**

## ⭐⭐⭐⭐⭐ WHERE THE NEXT TICK STARTS — K34b, LICENSED BUT NOT YET RUNNABLE

✅✅ **ITEMS 2, 3 AND 4 ARE ANSWERED BY C557 AT THE TOP OF THIS FILE — READ THAT FIRST AND
RUN ITS SEQUENCE. THIS LIST IS KEPT FOR ITS REASONING, NOT ITS STATUS.** Item 1 (re-fit the
stretch on the new build) and item 5 (the flash route) still stand exactly as written, and
item 1 is now load-bearing in a way this list did not know: ⭐ **the ELAPSED window is a
FUNCTION of the stretch**, so the ladder cannot be placed until `dectime.py --interval` has
run on the flashed build.

⛔⛔ **DO NOT JUST FLASH AND RUN IT.** C554 licenses K34b; it does not make it ready, and every
item below has already cost this line a verdict once:

1. ⭐ **Re-fit the stretch with `dectime.py` ON THE NEW BUILD** — M79/C547: it is known only to ~7%
   and **a new binary is a new condition**. ⛔ Never 1.653, never this build's 1.775.
2. ⭐⭐ **Re-derive the thresholds from the level measured ON THE DAY** (M80/M83) — ⛔ never from
   C538's and never from K34a's. `./k34sim.py --from <the day's caps> --fit-sigma`.
3. ⭐⭐ **Simulate BOTH power and false-fire before the capture** (M70/M75), and ⭐ **give the
   no-verdict branch a meaning in advance** (M74).
4. ⚠ **Consider whether K34b should use K36's statistic too.** Its band is another thresholded one,
   and C552/M84/C553 are three findings in a row about exactly that failure mode on this bench.
   ⛔ That is a design question to settle BEFORE the flash, not after the caps.
5. ⚠ The flash route is proven: both zips banked at `/Users/Shared/code/personal/rfid/.tools/builds/`,
   a flash under a minute, `hw emudebug` confirms 31 vs 62, `enterdfu.py` may need a retry.

⭐⭐⭐ **AND A DESIGN FACT WORKED OUT THIS TICK THAT CHANGES ITEM 4 — K34b AND THE DECIMATION
PROPOSAL ABOVE ARE THE SAME QUESTION.** K34b asks whether `idteck`'s region sits at the *unmoved*
140-145 or the *moved* 84.7-87.7 under dec 2; that is *does the feature keep its ELAPSED position or
its SAMPLE position*, which is C539's question with a longer burst under it. ⇒ **the K36-style
answer is the same alignment comparison**, and K34b has the advantage the banked caps do not: **its
ladder can be CHOSEN**, which removes the interpolation objection and the foreknowledge objection at
a stroke.

⛔⛔ **BUT THE SAME ARITHMETIC KILLS THE EASY VERSION, AND IT MUST BE SETTLED BEFORE THE FLASH
(M81): THE STRETCH IS NOT PRECISE ENOUGH TO ALIGN ANYTHING.** At `1.775 ± 7%` (M79/C547):

| dec-2 nominal | elapsed-equivalent | uncertainty | in dec-1 cells (5 ms grid) |
|---|---|---|---|
| 50 ms | 88.8 ms | ±6.2 | **±1.2** |
| 100 ms | 177.5 ms | ±12.4 | **±2.5** |
| 150 ms | 266.2 ms | ±18.6 | **±3.7** |

⇒ **an alignment built on the current stretch is uncertain by one to four cells, against a statistic
C555 measured resolving ONE cell.** ⛔ So the alignment approach is not merely *available* — it is
**blocked on the stretch's precision**, and that is a prerequisite nobody has costed.

✅✅ **RUN, AND IT ANSWERED — THE ALIGNMENT APPROACH IS DEAD ON ARITHMETIC (C556).** `dectime.py`
gained `--interval` and two independent runs an hour apart (nothing armed, no bench move, `lf config
--reset` in the `finally` both times) give **1.739 (95% CI 1.645-1.833)** and **1.685
(1.559-1.811)**, off five median points whose fit residuals are **2.7-5.7 ms on a ~196 ms span**.
⭐ C540's **1.653** and this build's **1.775** both sit inside both intervals ⇒ **those published
figures never disagreed significantly, and C547's ~7% was right.**

⇒ ⛔⛔ **A dec-2 cell's ELAPSED position is uncertain by ±1.26 cells at 50 ms nominal, ±1.9-2.5 at
100 and ±2.8-3.8 at 150 — against a statistic C555 measured resolving ONE cell.** Tightening inside
this method cannot rescue it: the residuals are already a few ms and the SE is set by five points
against real client jitter, so **even halving it leaves ±1 cell.**

⇒ ⭐⭐ **ITEM 4 IS SETTLED: K34b KEEPS A THRESHOLD BAND** (or needs an instrument nobody has yet),
and ⛔ **the K36-route decimation proposal above is BLOCKED, not merely objectionable — mark it
closed rather than leaving it inviting.** ⚠ The point estimate itself moved **1.739 → 1.685 in one
hour**, a spread like the within-run SE, which is its own argument against trusting a single figure.

⭐⭐ **AND THE METHOD FAULT IS WORTH MORE THAN THE NUMBER (C556):** the first interval was a
**bootstrap** and returned **−1.545 .. 1.854** — a *negative* stretch — off data whose medians are
monotone to 3 ms. It was measuring the **outlier rate**, not the precision: a per-cell median over
10 reads is robust to a pm3 client hiccup and a bootstrap of those same 10 is not. ⇒ **resampling a
statistic chosen for being ROBUST destroys the robustness that justified choosing it.**

~~⇒ ⭐⭐ **THE CONCRETE PREREQUISITE, AND IT IS CHEAP AND FLASH-FREE ON THE CURRENT BUILD: tighten the
stretch.**~~ `dectime.py` already slope-fits it (dec 2 = 1.775, dec 3 = 2.449, dec 4 = 3.117) and
retired dec 3/dec 4 by arithmetic; what it has never been asked for is an **interval**. Run it with
enough points to put a stated uncertainty on 1.775, on the build in front of it. ⛔ **That figure
does not transfer to the burst-1000 build** (M79/C547: a new binary is a new condition) — but the
*method and its achievable precision* do, and if the best it can do is ±7% then the alignment
approach is dead on arithmetic and K34b must keep a threshold band after all. ⇒ **run the interval
FIRST; it decides item 4, it needs no flash, and it is the difference between designing K34b twice
and designing it once.**

## ⛔⛔ CLOSED SAME TICK — K36's MOVE DOES **NOT** REACH THE DECIMATION QUESTION (C556)

⛔ **Objection 2 below turned out to be fatal and it was measured, not argued: the stretch is
`1.685-1.739` with 95% bounds spanning `1.559-1.833`, so a dec-2 cell's elapsed position is
uncertain by ±1.3 cells at 50 ms nominal and ±2.5 at 100, against a statistic that resolves ONE
cell.** ⇒ **the alignment cannot be built, and no amount of care in the other four objections
matters.** ⛔ **Do not reopen this. The decimation line stays closed, and now for a second and
independent reason.** ✅ The standing instruction was right and the round lost nothing by it.

⚠ The section is kept below for its reasoning — in particular *why a closure's rationale can be a
property of the instrument rather than of the question*, which was a good instinct and is worth
having again on a different problem.

## ~~⚠⚠ A PROPOSAL, NOT A DECISION — K36's MOVE MAY REACH THE DECIMATION QUESTION~~ **(SUPERSEDED)**

⛔⛔ **The standing instruction is explicit: *the decimation line is CLOSED — do not re-open it or
propose a variant*.** So this is written as a proposal with its own objection attached, and ⛔ **the
next tick must not simply run it.** It is recorded because leaving it unrecorded is worse.

⭐ **The idea, and it costs ZERO bench time** — six dec-2 caps are already banked
(`k30_dec2_s{307,311}`, `k31_dec2_s{313,317}`, `k32_dec2_s{331,337}`). C539's question is *is the
lead time fixed in ELAPSED time or in SAMPLES?*, which is a **location** question comparing two
conditions — K36's exact shape. Under ELAPSED a dec-2 cell at nominal `x` matches dec-1 at
`x x 1.775`; under SAMPLES it matches dec-1 at `x`. ⇒ score the dec-2 profile against the dec-1
profile under **both alignments**, each normalised by the within-condition agreement, and ask which
fits better.

⭐⭐ **WHY THE EXISTING CLOSURE MAY NOT COVER IT.** C545-C548 closed decimation on the **burst
ceiling** — `sep = L(1-1/S)` under `L <= B/S` peaks at **45.8 ms at dec 2**, never enough to
separate the two predictions **for an individual cell** against the feature's skirt. ⚠ **That is an
argument about separating CELLS, and this statistic does not separate cells** — it fits all 15-17
at once, and over a 10-120 nominal span the two alignments put the reference at **18-213 ms** and
**10-120 ms**, which are very different ranges even though any single cell's two predictions are
not. ⇒ **the closure's rationale is a property of the old instrument, and C552/M84/C553 are three
findings in a row about exactly that instrument being underpowered here.**

⛔⛔ **THE OBJECTIONS, WHICH ARE NOT SMALL AND MUST BE ANSWERED BEFORE ANYONE RUNS IT:**
1. ⛔ **The dec-2 ladders are NOT the 38-cell common ladder** — 17 cells 10-120 (K30/K31) and 15
   cells 52.5-117.5 (K32) — so the comparison needs **interpolation** of the dec-1 reference, and
   C555 measured this statistic resolving **one 5 ms cell**. An interpolated reference is a new
   instrument and its own controls would have to be built and simulated first (M70/M75).
2. ⛔ **The stretch is 1.775 known to ~7% (M79/C547)**, and the alignment depends on it directly —
   a 7% error over a 120 ms span is ~8 ms, which is more than one cell.
3. ⛔ **The top of the ELAPSED-matched range (213 ms) falls off the dec-1 ladder's 195 ms top**, so
   the two alignments are scored over slightly different support and that asymmetry must be
   handled rather than ignored.
4. ⚠ **Foreknowledge is heavy**: K30/K31/K32 were all read, and C544 named `idteck` 140-145 vs
   84.7-87.7. Any verdict needs the direction rule applied explicitly, as K36 did.
5. ⛔ **It reopens a closed line**, and C545-C548 also said the confound is *honestly uncloseable
   here*. Overturning that is a bigger claim than one re-analysis should make quietly.

⇒ ⭐ **RECOMMENDATION: do not run it on a tick's own authority. Cost the objections above first —
they are all offline — and if they survive, put it to the operator as a reopening, not as a routine
re-score.** ⛔ And if it is ever run, it is a RE-ANALYSIS of banked caps: it cannot license a
capture, and it moves no cell.

⭐ **Bench state at the end of this tick: cu2 on the burst-500 build (31 frames, asked), mode
`Tag Reader` (asked), nothing flashed all tick, cu1 never touched, nothing moved.**

## ✅ 2026-09-17 20:4x — TWO STALE ITEMS IN AUTOPILOT §2c CLOSED, ONE BY MEASUREMENT

⭐ Both were live *work it* items that a future cold tick would have spent a unit rediscovering.

1. ⛔ **`indala224`'s writer "TIMES OUT" is RETRACTED — `CMD 3039` never hung.** C481/L449 had
   already measured this *before §2c was written*; the host's `send_cmd_sync` default is 3 s and
   the call takes ~3.5 s, and the client already passes `timeout=30`. ✅ **Re-measured today rather
   than taken on the note's word: `3.43 s` and `3.54 s` against `1.51 s` for the 64-bit writer next
   door** (C481 had 3.42/3.71 against 1.34). The cost is structural — `passes x blocks x 2 sends`,
   64 against 24, and `indala224` is the only **eight-block** writer in the tree. ⚠ **What survives
   is the only part worth carrying: the 3 s default is a latent trap for any FUTURE multi-block
   writer, because from the host a slow writer and a hung one are indistinguishable.** That is an
   upstream note (§2e), not a bug. ⛔ `cu1·wr` for `indala224` is still genuinely absent and needs a
   tag — operator-return.
2. ✅ **Electra's `rd.pm3` is now refused by the PLANNER, permanently.** §2c asked for exactly this.
   The registry row already carried the evidence; the planner did not, so the published refusal
   still read as a to-do and **told the operator to record the token — which is the false pass the
   registry row forbids.** Now `gap:pm3-indistinguishable`. ⇒ **three states, not two: unlicensable
   · unmeasured · indistinguishable.** `./runtests` 475 (+1).

⚠ **The remaining §2c item, `fdxb emu.pm3 → rd.cu2` SILENT, is NOT workable unattended and should
not be attempted**: separating *the Proxmark's `lf fdxb sim` is wrong* from *our reader cannot take
an emulated fdxb* needs either a real fdxb tag in the Proxmark's stack (Rig B is deliberately
tagless) or the Flipper in the same field (it is on Rig A and will not couple). ⇒ **operator-return,
and say so rather than spending a capture on an ambiguous null.**

## ⛔⛔⛔⛔ 2026-09-17 20:2x — **THE GATE RAN AND PASSED; THE RUN IS STILL REFUSED (C553, M85)**

**The gate was captured as pre-registered — two caps, no flash, `disarm: ok` twice, cu2 verified
`Tag Reader` by asking the device — and it PASSED at the top of its range (+75.0 and +75.0 against
+68).** ⭐⭐ **It also confirmed C552 on the bench instead of in simulation: the pooled level is
indistinguishable from K34a's own day (29.9-34.2% vs 27.6-33.4%) while the peak elevation moved
+46.9/+68.8 → +75.0/+75.0.** ⭐ **And K34a's own failure mode is FIXED — `P(|H500| >= 3)` is 78.4%
against 20.8%.**

⛔⛔ **BUT THE RE-DERIVATION THE PASS LICENSED CAME BACK NEGATIVE, SO NOTHING WAS FLASHED AND THE
FOUR CAPS WERE NOT SPENT.** Grounded in the gate's own caps: **D1 power 28.6%** against the
pre-registered 93.6%, **NO VERDICT the most likely outcome at 40.1%**, reps 24 no help, and **D3 now
fires 65-78% under SCALED / SHIFTED / FLAT** (against 7.2% / 1.8% / 100% at C538's level) so a D3
would say almost nothing. ⭐ D1's false-fire is still **0.0%**: ⇒ **unpowered, not broken.**

⛔ **That overrides the pre-registration, and the reason is inside it**: the licence read *PASS ⇒
run, thresholds re-derived from these caps*, and a licence conditional on a re-derivation is void
when the re-derivation fails. Running a band known to be 28.6% powered is what M70/M75 forbid.

⭐⭐⭐ **M85 — AND IT IS MY ERROR, NOT THE BENCH'S: I GATED ON THE PREVIOUS FAILURE MODE INSTEAD OF
ON THE QUANTITY THAT DECIDES THE VERDICT.** Peak elevation was a **proxy** for D1's power, and D1's
power is computable **directly from the gate's own two caps** by `./k34sim.py --from` — so the proxy
was never needed, and it added a way to be wrong (it was +60 for an hour and +60 was wrong).

⭐⭐⭐⭐ **⇒ THE CORRECTED GATE, AND IT IS WHAT THE NEXT TICK USES. Peak elevation leaves the design.**

> **Capture the cheap pair** (standing burst-500 build, no flash — `keri`+`idteck`, 38-cell 10-195
> ladder, dec 1, `--per-arm-shuffle`, `--reps 8`, two fresh seeds), then run
> `./k34sim.py <draws> --from <those two caps> --fit-sigma --reps 16`.
> ⭐ **D1's power >= 70% ⇒ flash and run K34a's four caps that session, ABBA order kept.**
> ⛔ **< 70% ⇒ do not flash and do not capture.** ⚠ A statement about the bench that day, **not** a
> result about the burst.

✅ **The two caps already taken are NOT wasted — `gate1_s389` and `gate2_s397` are exactly what the
corrected gate reads**, and they say **28.6%**. ⇒ ⛔ **on the bench as it stands tonight, K34a is
refused. Do not re-capture the pair tonight hoping for a different number.**

⚠⚠ **AND THE DESIGN QUESTION THE NEXT TICK INHERITS, WHICH IS THE REAL OBSTACLE NOW THAT THE
CONTROL IS HEALTHY:** D1 asks for `keep >= 0.75 x |H500|`. It was built where `|H500|` was **8-9 and
stable**; today it is **3-5**, so *keep 75%* means keeping **3 of 4 exactly** and one region failing
to replicate ends the fire. ⇒ **a threshold written as a FRACTION of a measured quantity got
stricter when the measurement shrank, and nobody changed the band.** ⛔ **Do not redesign it and run
it in the same session** — that is fitting. Re-cost it first, pre-register the new form, and simulate
its false-fire before any capture.

## ⛔⛔⛔⛔ 2026-09-17 18:5x — **K34a's RE-RUN IS REFUSED BY ITS OWN ARITHMETIC (C552, M84)**

**The re-run was this tick's pinned unit. It was not run, and that is the result.** M83 required its
thresholds to come from the level measured on the day; re-derived that way, the control passes only
**20.8-30.9%** of the time at reps 16 — against the **100.0% at every reps** that C538's grounding
gives — so K34a was ~4:1 against a verdict before it was ever flashed. ⛔ **More reps makes it
worse and never recovers** (11-16% out to reps 128): the binding variance is between caps, which
reps cannot touch. ⇒ **the next unit is a cheap no-flash GATE on peak elevation** — see *WHERE THE
NEXT TICK STARTS*. ⭐ Nothing was flashed, armed or moved this tick; it was offline throughout.

## ⛔⛔⛔⛔ K34a: **CONTROL FAILED — NO VERDICT — K34b IS NOT LICENSED** (C549, M83)

Four caps, `keri`+`idteck`, the C538 common 38-cell 10-195 ms ladder, dec 1, `--per-arm-shuffle`,
`--reps 16`, seeds 353/359/367/373, **ABBA (1000,500,500,1000)**. **All eight gates passed.**
Score it with `./framescale.py --k34 caps/k34a_*.json`.

**The burst-500 control hit 0 of 10 regions against a pre-registered floor of 3.** ⇒ the run
cannot say whether the regions moved, because the condition they had to move FROM showed none.

⚠⚠ **AND THE RAW SHAPE READS BACKWARDS, WHICH IS WHY THE FLOOR EXISTS: burst 1000 hit FOUR
regions (`keri` R2,R3,R4 and `idteck` R4) where burst 500 hit none.** ⛔⛔ **DO NOT READ THAT AS
A BURST EFFECT.** Seed-to-seed profile agreement was **also** lower at burst 500 today (`keri`
**+0.573**, `idteck` **+0.667**) than at burst 1000 (**+0.693**, **+0.751**), and lower than
C538's own burst-500 pair (**+0.784**, **+0.733**) — the two differences run the same way and
this run cannot separate them.

⭐⭐ **M83 — the lesson is about the SIMULATION, not the bench.** `k34sim.py` put
control-failure at **0.0%** over 10,000 draws, correctly *given C538's per-cell rates*. Today's
pooled levels are **22.0-35.4%** against C538's **38.5-43.1%**, one day apart on an unmoved bench,
and C497 already measured that this level wanders. ⇒ a power figure is a property of the band
**at the level it was grounded in**. ⭐ Against M82 — where an unmeasured assumption would have
fired a clean, pre-registered, WRONG verdict — **here the floor turned the same class of error
into an honest no-verdict. The guard did its job and cost one line.**

## ✅ THE OFFLINE AUDIT IS DONE — AND IT ANSWERED (L540, `repro.py`)

⛔ **K34a's control failure was NOT a fluke.** `./repro.py` scores seed-to-seed rank agreement
for every banked cap pair. ⭐ Reading only the **38-cell dec-1** rows, which is the one sound
comparison (M73):

| when | pairs | agreement |
|---|---|---|
| morning | k26, k27, k28, k29 | **+0.679 to +0.863**, mostly ~**0.82** |
| afternoon | K34a burst 500 | **+0.573**, **+0.667** |
| afternoon | K34a burst 1000 | **+0.693**, **+0.751** |

⚠⚠ **AND THE DIRECTION IS THE INFORMATIVE PART: K34a used `--reps 16` against the morning's
`8`**, which cuts per-cell sampling noise and should have **RAISED** agreement. It fell.
⇒ **the decline is in the wrong direction for a sampling artefact**, and it agrees with the
pooled levels (**22.0-35.4%** against C538's **38.5-43.1%**).

## ✅✅ K35 RAN AND FIRED — `--reps` IS EXONERATED, AND TIME IS NOW A KNOWN CONFOUND (C550)

C549 left the morning/afternoon level step confounded: every morning cap was `--reps 8` and every
afternoon cap `--reps 16`, with no contrast in `caps/` to break it. **K35 broke it** by running the
MORNING configuration at an EVENING hour — `keri`, 38-cell 10-195 ladder, dec 1, `--reps 8`, two
fresh seeds, burst 500, 17:46-18:2x, **no flash, no bench move**.

| | pooled | seed agreement |
|---|---|---|
| morning reference | 40.6% | +0.827 / +0.784 |
| afternoon reference | 33.5% | +0.573 / +0.693 |
| **K35 (evening, reps 8)** | **36.5%** of 608 | **+0.677** |

⇒ **E2 FIRES**: `reps 8` did **not** restore the morning condition ⇒ ⛔ **`--reps 16` is NOT the
driver, and K34a's reps choice is exonerated as the cause of its control failure.**

⚠⚠ **IT FIRED MARGINALLY ON THE LEVEL MARKER — quote this with the verdict, never the verdict
alone.** 36.5% is **0.5 points** under the 37.0 threshold against a **~2.0 point** binomial SE at
n=608, so the level is **not distinguishable from the midpoint**; the fire is carried by the
AGREEMENT marker, which does sit cleanly in the afternoon range. ⇒ read it as ***reps is not the
driver*** (both markers agree) and ⛔ **not** as *the level returned to the afternoon's*.
⚠ And 36.5% sitting between the blocks is equally consistent with a **continuum** rather than the
discrete step the band assumed. Nothing tests that yet.

## ⭐⭐⭐⭐⭐ WHERE THE NEXT TICK STARTS — THE AUDIT IS DONE; K34a's RE-RUN IS THE UNIT

⭐⭐⭐ **THE STANDING CONSEQUENCE, AND IT IS THE BIGGEST THING THIS ROUND HAS PRODUCED ABOUT
METHOD: the level follows the CLOCK or the SESSION, so a band whose two conditions ran one after
the other has time folded into its contrast.** K34a's **ABBA** order already had that protection —
which is precisely why its 0-vs-4 hit difference could be identified as confounded instead of
published — and ⛔ **the earlier A-then-B bands do not.**

✅✅ **UNIT 1 IS DONE — THE EXPOSURE IS NARROW AND THE HEADLINE IS SAFE (C551).**
⭐⭐ **Structural protection covers almost everything**: every lead-time claim is scored on
LADDER CELLS, and `k12()` reshuffles the cell list **within every round** (M60), so a cell's
position in time is randomised against its value by construction. Every band but K34a has all its
caps inside **4-35 minutes**.
⭐⭐⭐ **C538/B1 — the round's headline — is PROTECTED: its three arms sit in the SAME CAP**,
so the clock enters all three identically. ⛔ The mirror of M69 (a shared PLAN across arms was
fatal; a shared TIME across arms is harmless).
⚠ **One exposed family: dec-1 vs dec-2** (K30/K31/K32) read caps of 10:42-12:37 against dec-1
regions of 07:07-10:08 — ✅ **already closed in closed form by the burst ceiling (C545-C548),
which is arithmetic and not a level comparison**, so nothing still standing is affected.
⛔⛔ **An audit, not a retraction. Nothing was withdrawn and nothing may be without re-scoring.**

⛔⛔⛔ **UNIT 2 IS DONE, AND ITS ANSWER IS THAT THE RE-RUN MUST NOT BE RUN AS PINNED (C552, M84,
commit `e25c7313`).** The thresholds were re-derived from the level measured on the day, as M80/M83
required, and the re-derivation refuses the design.

⭐⭐ **THE NUMBER: `P(|H500| >= 3)` is 100.0% at EVERY reps under C538's grounding and 30.9% at
reps 16 under the day's** (20.8% once the second noise source is modelled). ⇒ **K34a was about 4:1
against having a verdict before it was flashed.** Its control failure was the expected outcome.

⛔⛔ **AND THE OBVIOUS REMEDY IS BACKWARDS — MORE REPS MAKES IT WORSE**: 40 / 23 / 11 / 16 % at reps
8 / 16 / 24 / 32, and it **never recovers, plateauing at 11-16% out to reps 128** — eight times what
K34a already cost. The binding variance is **BETWEEN caps**, and reps within a cap cannot reduce it
by construction. ⇒ ⭐ **the remedy is more SEEDS and a k-of-n replication rule, never more reps.**
⚠ Retuning the elevation threshold rescues the control (96.7%) and **not** the band: D1's power is
still 30.9%, reps 32 buys only 40.2%, and D1's false-fire stays **0.0%** throughout — ⇒ the band is
**unpowered, not broken**, so it is worth gating rather than redesigning.

⛔ **SUPERSEDED — THIS GATE RAN, PASSED, AND WAS THE WRONG SHAPE. READ C553/M85 AT THE TOP; the
corrected gate is D1's power itself and peak elevation has left the design. The block below is kept
for the reasoning that produced the statistic, not for its status.**

⭐⭐⭐⭐ **SO THE NEXT TICK'S FIRST UNIT IS THE GATE, AND IT NEEDS NO FLASH.** Across the range where
D1's power runs **0.8% → 91.2%**, the pooled level moves only **32.9% → 38.0%** while the largest
region elevation moves **+40.6 → +75 points**. ⇒ ⛔ **pooled level is nearly blind to the thing that
decides the band** — the round had been watching the wrong statistic — and **max region elevation
above the cap's own ladder median** is the one that responds.

> **THE GATE, PRE-REGISTERED AND NOW IMPLEMENTED AS `./framescale.py --gate`:** one cap pair on the
> **standing burst-500 build** (cu2 answers **31 frames**, asked 2026-09-17 18:5x — no flash needed),
> `keri`+`idteck`, the C538 common 38-cell 10-195 ladder, dec 1, `--per-arm-shuffle`, `--reps 8`
> (⛔ **8, not 16** — the curve above), two fresh seeds. The statistic is the **max, over both arms
> and all five K29 regions, of (the region's best cell − that arm's own ladder median)**, required in
> **BOTH** caps — ⛔ both, not pooled and not the better one, because one cap reaching it is exactly
> the single-seed evidence K29's two-seed rule exists to refuse.
> ⭐ **>= +68 points ⇒ the flash and K34a's four caps are licensed that session**, thresholds
> re-derived by `./k34sim.py --from` those two caps (M80/M83) and the ABBA order kept.
> ⛔ **< +68 ⇒ do not flash and do not capture** — the bench is not at a level that can answer K34a.
> ⚠ That is a statement about the bench today, **not** a result about the burst.
> ⚠ The gate is a *feasibility* measurement, not a band: it fires nothing, licenses no cell, and a
> pass does not predict K34a's verdict.

⛔⛔ **THE THRESHOLD WAS +60 FOR ABOUT AN HOUR AND +60 WAS WRONG — CORRECTED BEFORE ANY GATE CAP
EXISTED, FROM BANKED CAPS AND SIMULATION ONLY (M55, and it is M84's own lesson landing on me).**
C552 derived +60 from the **pooled** profile's contrast; the scorer reads a **per-cap** maximum at
**reps 8**, and a per-cap max is inflated by exactly the sampling noise that pooling removes. ⇒ the
number was calibrated on a different statistic from the one it gates. Re-simulated on the right one:

| contrast gain | D1 power @reps 16 | P(gate >= +56) | >= +62 | **>= +68** | >= +75 |
|---|---|---|---|---|---|
| 1.00 — **the day's own level, D1 useless** | 0.8% | 57% | 48% | ⭐ **6%** | 3% |
| 1.50 | 39.5% | 98% | 94% | 60% | 41% |
| 2.00 | 77.2% | 100% | 100% | ⭐ **92%** | 69% |

⛔ **+60 would have passed a condition whose D1 power is 0.8% about HALF the time** — it would have
licensed the flash on exactly the bench K34a already failed on. **+68 gives 6% false-pass and 92%
pass where K34a would actually work.** ⚠ The statistic is coarse at reps 8 (rates quantise to 1/8,
it saturates at +75) so do not read fine differences in it; reps 16 sharpens it to 4%/100% at +62
and was **not** taken, because 6%/92% is adequate and the gate's whole point is being cheap.

✅ **VALIDATED RETROSPECTIVELY: the gate REFUSES K34a's own control pair** (+68.8 and **+46.9**,
weakest +46.9 against +68) ⇒ had it existed, it would have stopped K34a before the flash and the
four caps.

⭐ The flash route stays proven and cheap — both zips banked, a flash under a minute, `hw emudebug`
confirms 31 vs 62 — so **the flash was never the expensive part, and it is now the part that is
conditional.** ABBA order still applies to K34a itself if the gate ever opens.

⚠⚠ **DO NOT READ C552 AS RETRACTING K35.** C550's exoneration of `--reps` is carried by its
agreement marker and both its markers agreed; what C552 says is that pooled level is the wrong
**gate** for this band's power, not that it was the wrong evidence there.

⚠ **Open and NOT answered**: *time of day* versus *session boundary* (cold start, fresh USB
enumeration, power cycle) — K35 confounds them by construction. A cheap discriminator would be
two cap-pairs at the SAME hour, one straight after a power cycle and one deep into a session.
⚠ **Descriptive and NOT to be upgraded**: R4 (140-145) was hit by **both** arms at burst 1000 and
neither at burst 500. Named so a later band can pre-register on it; it carries no licence.

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

## ⭐⭐⭐⭐⭐ THE ROUND'S HEADLINE, AND IT IS THE STRONGEST RESULT THIS LINE HAS PRODUCED (C538)

⭐⭐⭐ **THE LEAD-TIME REGIONS ARE THE SAME REGIONS ON THREE ARMS AND TWO FRAME LENGTHS — ONE
PRE-REGISTERED CROSS-ARM STATISTIC, B1 FIRES AT 12 OF 15.** `keri`, `idteck` and `nexwatch`
measured **together** on the common 38-cell 10-195 ms ladder, two fresh seeds, per-arm shuffled,
**all six gates passing and tight** (split-half **0.0, 0.7, 2.0, 3.9, 5.9, 0.0**; P1 0.50 in every
cell of every arm).

| region | `keri` | `idteck` | `nexwatch` |
|---|---|---|---|
| **R2 55-65 ms** | **HIT** | **HIT** | **HIT** |
| **R5 180-190 ms** | **HIT** | **HIT** | **HIT** |
| R1 15-20 | HIT | no | HIT |
| R3 100-105 | HIT | no | HIT |
| R4 140-145 | HIT | **HIT** | no |

⭐⭐ **Simulated BEFORE the capture: 11+ occurs 98.8-100% when 4-5 of the 5 regions are genuinely
shared, and 0.0% when each arm carries independent structure of its own.** The observed **12 is
exactly the simulation's median for *4 of 5 shared*.** ⭐ The five reference regions were **derived
mechanically by `--inventory` from the banked caps and not from any write-up** (M76 — the mistake
that cost K26's A2), and this ran on seeds none of them used.

⭐⭐⭐ **TWO REGIONS ARE HIT BY ALL THREE ARMS, AND ONE OF THOSE ARMS HAS A 4096-SAMPLE FRAME
AGAINST THE OTHERS' 2048.** ⇒ **the decode's dependence on lead time sits at the same MILLISECONDS
across three protocols, three demodulators, three reader commands and two frame lengths.**
⚠ C536 already showed milliseconds-not-frames for `nexwatch` at two regions, so this **strengthens
rather than establishes**; what is new is that it is now **one** cross-arm statistic instead of four
per-arm ones.

⚠ **DESCRIPTIVE, NOT UPGRADED: all three misses were ONE CELL SHORT** — `idteck` had 1 of the 2
cells needed in R1 and R3, `nexwatch` 1 in R4 — marginal rather than absent, and the band counted
them as misses.

⛔⛔ **WHAT IT DOES NOT DO: it says nothing about WHY**, it **excludes `indala` by construction**
(C537 — its 75% median puts the forward threshold at the ceiling), and a REFUTED B1 could not have
told *each arm's own structure* from *no structure*, which is why it is read beside the per-arm A1
verdicts — **all three of which fired** (C533, C536, C537).

⚠⚠ **AND THE INFERENCE, LABELLED AS ONE AND NOT A BAND: a structure fixed in milliseconds and
shared across arms that differ in protocol, demodulator, reader command AND frame length is very
hard to locate in the EMISSION's own timing — it points at the READER or the FIELD.**
⛔ **Nothing tests that yet.** ⭐ **It is the first direction this line has had**: the beat, settling,
the frame and the modulation are all dead, and this is the first positive constraint pointing
anywhere. ⇒ **That is what the next criterion is for.**

## ⭐⭐⭐⭐⭐ 2026-09-17 12:4x-13:2x — THE DECIMATION APPROACH IS CLOSED, AND THE HARNESS'S OWN
## CEILING FORMULA WAS WRONG IN ITS FORM. READ THIS BEFORE THE SECTION BELOW IT.

util7 **85 → 86**. **Repo for the detail: `ChameleonUltra` C545-C548, M82, L533-L536.** One tick,
four findings, **one capture and one host-timing run — no band was spent.**

⭐⭐ **K33 — the successor C544 named by arithmetic — IS NOT RUNNABLE, and its pilot said so before
the capture rather than after.** `idteck`'s burst ends between **130 and 140 nominal at dec 2**, not
at the computed 157, so C544's unmoved window (140-145) is entirely past the ceiling.
⚠⚠ **And K33 could not have failed safe**: starvation depresses the *unmoved* window only, so it
would have fired **ELAPSED** — pre-registered, clean and wrong ⇒ **M82**.

⭐⭐⭐ **THE APPROACH IS CLOSED IN CLOSED FORM, NOT BY SWEEPING.** `dectime.py` slope-fits the
stretch M79 has been owed since C540 (**dec 2 = 1.775, dec 3 = 2.449, dec 4 = 3.117**; ⛔ dec 4's
crude ratio implied ~2.05 and was **wrong by half**), and then `sep = L(1-1/S)` under `L <= B/S`
peaks at **S = 2 exactly**. ⇒ widest reachable separation **45.8 ms at dec 2, R3 — which is exactly
what K32 ran and found BRIDGED** — against a bound of 61.3 over all stretches. **dec 3 and dec 4
retired without running either.**

⛔⛔ **AND THE OBVIOUS SUCCESSOR IS ALREADY REFUTED**: an `msleep` lever escapes the cap but means
the field is **DOWN**, which K10 measured restarts the burst past ~120 ms — **the very reason K12
switched to the primer knob** (C515). ⇒ **C539's confound stays OPEN and is uncloseable on this
bench.** Say so plainly; do not reach for a fourth variant. **The one lever that would reopen it is
`LF_TAG_BURST_TARGET_MS` — see item 3b, and read the warning there before touching it.**

⭐⭐⭐⭐ **THE INCIDENTAL FINDING IS THE BIGGEST ONE, AND IT CORRECTS THE HARNESS (C548).**
`_top = (500 - 192 - probe_ACQUISITION)/stretch` **charges a read at its acquisition, and a read's
ELAPSED is not its acquisition** — C540 measured the ~47% USB-readback surcharge and `_top` never
adopted it. One nominal ms of primer really costs **1.41 ms at dec 1 and 2.50 at dec 2**, and the
uncounted term **SCALES with the primer**, which is why no constant could absorb it: **`K12_OVERHEAD_MS
= 192` IS that failed absorption**, and the client's real cost is **~85 ms**, exactly what the comment
beside the constant always said. ⭐⭐ **Fitted on one boundary and TESTED on another**: `idteck` dec 2
(clean 130 / broken 140) computes **138.2**; `nexwatch` dec 1 (clean 195 / failed 200, measured long
before for another reason) computes **196.0** — **both inside their brackets**, where the old form
said 157 and 210. ✅ **Nothing banked moves**; `burstsync.py` now carries the corrected form.
⚠ **It is still not an arbiter — P1 is** — but for a new reason: it cannot certify within ~10 ms of
the edge, because the burst is clamped to whole ~16.4 ms emission frames.

⚠ **ONE RETRACTION INSIDE THE TICK**: C547's first version claimed the overhead is *202-220 ms,
above the 192 constant*. **Wrong, and wrong in sign** — I assumed the formula's FORM was right and
solved for its constant, which is the same error the formula makes. Retracted by C548/L536. ⭐ What
stands from C547: **the dec-2 stretch is known to ~7%, not three decimals** (1.775 here against
C540's 1.653), so ⛔ no design may lean on it harder than ~10%.

⛔ **Bench**: nothing flashed, on either unit. cu2 armed and disarmed once through `burstsync`'s
`finally`; `lf config --reset` in `dectime`'s. Nothing moved. `./runtests` green (474).

## ⭐⭐⭐⭐⭐ WHERE THE NEXT TICK STARTS — THE MECHANISM, AND IT FINALLY HAS A DIRECTION

⭐⭐⭐⭐⭐ **2026-09-17 13:3x — THE NEXT TICK'S FIRST UNIT IS `K34a`, AND IT IS PINNED AND PRICED.**
Read `burstsync.py`'s **K34** section (commit `4bf718ee`) in full before planning it, then item 3b
below. **The decimation line is CLOSED — do not re-open it or propose a variant** (item 3).

⛔ **K34a NEEDS A cu2 FLASH, AND THAT IS DELIBERATELY LEFT TO A FRESH SESSION.** This tick pinned the
design rather than executing it, because a flash plus its functional verification plus a two-arm
two-seed capture is a large unit and AUTOPILOT §6 is explicit that a cramped session re-deriving
badly costs more than losing an hour. ⭐ **It is not a deferral for its own sake: everything K34
needs is written down** — the arithmetic, the two stages, the licensing rule between them, the
retry behaviour of `enterdfu.py`, and the **air-side** check that the constant actually took effect.
⇒ **A tick starting fresh should flash and run K34a, not re-litigate whether to.**


✅ ~~**Run the three-arm shared-regions band**~~ **DONE — C538. ⛔ Do not re-run it.**
✅ ~~**The client-side / decimation test**~~ **CLOSED 2026-09-17 — C545-C548. ⛔ Do not re-run it, and
do not propose a variant: item 3 below carries why every variant is closed too.**

⭐⭐⭐ **THE ONE OPEN UNIT IS THE MECHANISM, AND C538 POINTS IT SOMEWHERE FOR THE FIRST TIME.**
Everything proposed so far is dead — **not the beat** (C515), **not settling** (C515), **not the
frame** (C520/C529/C536), **not the modulation**, **not a protocol property** (C538). And the
positive constraint is now strong: **the structure is at fixed MILLISECONDS, shared across three
arms differing in protocol, demodulator, reader command AND frame length, bounded at 5-10 ms below
and not bounded above by anything but the burst.**

⇒ ⭐⭐ **THAT POINTS AT THE READER OR THE FIELD, NOT AT THE EMISSION** — ⚠ **but item 3 below must go FIRST**, because it excludes the CLIENT, which nothing has ruled out and which a verified knob can now test. The reader and the field are separable
on this bench, which is the thing to exploit:
1. ⭐⭐⭐ **IF IT IS THE READER**, it should move when the READER's own timing moves and not when
   the emission's does. The primer is already a reader-side knob; a second reader-side knob that
   changes the field WITHOUT changing the emission would separate them. ⚠ Design it against
   `--inventory`'s regions, and **simulate a false-fire rate AND a power figure before capturing**
   (M70/M75).
2. ⭐⭐ **IF IT IS THE FIELD**, the regions should be a property of the PAIR and should move with
   the pad or the coupling — ⛔ **which needs the operator**, so it is a return item and not a
   tick's. ⭐ Name it in the handover so the operator can decide whether to spend a bench move on
   it; it is now a well-posed question rather than a fishing trip.
3. ⛔⛔⛔⛔ **THE CLIENT-SIDE TEST IS CLOSED, AND SO IS EVERY VARIANT OF IT — THE BURST CEILING
   ENDS IT, NOT A FAILED CAPTURE (C545-C548, 2026-09-17).** K33 was specified by C544 as `idteck`,
   unmoved 140-145 against moved 84.7-87.7. ⭐⭐ **Its pilot measured the one number it depended on
   and had never measured: `idteck`'s burst ends between 130 and 140 nominal at dec 2**, not at the
   computed 157 — arrivals **0.50 at 110/120/130** then **0.81 / 0.94 / 0.75 / 0.69 / 0.75 / 0.88**
   across 140-170, with the decode level **0% at 145, 150, 155 and 160**. ⇒ **K33's whole unmoved
   window is past the ceiling.**
   ⚠⚠ **AND IT COULD NOT HAVE FAILED SAFE, which is the part worth carrying**: starvation depresses
   the **unmoved** window and leaves the **moved** one alone, so K33 would not have returned *no
   verdict* — it would have fired **ELAPSED**, pre-registered and clean and wrong, with nothing
   downstream able to catch it ⇒ **M82: when a design buys its power at the top of a budget, the
   budget stops being a constraint and becomes a quantity under test. Measure it first.**
   ⭐⭐⭐ **AND ONE MEASUREMENT RETIRED dec 3 AND dec 4 WITHOUT RUNNING EITHER.** `dectime.py` (new,
   nothing armed) slope-fits the stretch M79 has been owed since C540: **dec 2 = 1.775, dec 3 =
   2.449, dec 4 = 3.117** — ⛔ **dec 4's crude fixed-N ratio implied ~2.05 and was wrong by half.**
   Then it closes in closed form: `sep = L(1-1/S)` under `L <= B/S` maximises at `B(S-1)/S²`, **peak
   at S = 2 exactly**. ⇒ the widest separation reachable inside the burst is **45.8 ms at dec 2, R3
   — precisely the configuration K32 already ran and found BRIDGED** — and the bound over *all*
   stretches is **61.3 ms**. **No decimation this bench can set buys a usable separation.**
   ⛔ **DO NOT PROPOSE THE OBVIOUS SUCCESSOR EITHER — IT IS ALREADY REFUTED.** An `msleep` between
   primer and probe would add lead time at *zero* sample cost and so escape the `B/4` cap
   entirely. ⛔ **But a gap means the field is DOWN**, which K10 measured **restarts the burst past
   ~120 ms**, and below that it changes the emission's own condition rather than only the lead time
   — **which is exactly why K12 switched from the gap knob to the primer knob in the first place**
   (C515). It is not a cleaner instrument; it is a second confound.
   ⇒ ⭐ **SO THE CONFOUND C539 RAISED STAYS OPEN AND IS HONESTLY UNCLOSEABLE HERE**: *fixed
   milliseconds* has always meant *fixed `-s N`*, and no knob on this bench separates them widely
   enough to beat the feature's skirt. **Say that plainly rather than reaching for a fourth variant.**

3b. ⭐⭐⭐⭐ **PINNED AS K34 (`burstsync.py` docstring, commit `4bf718ee`) — READ IT BEFORE
   TOUCHING THIS. THE ONE LEVER THAT WOULD REOPEN IT IS OURS, AND IT IS A FIRMWARE CONSTANT** —
   `LF_TAG_BURST_TARGET_MS (500)` at `lf_tag_em.c:75`. Every bound above is proportional to it: at
   1000 ms the budget triples to ~600 dec-1 nominal ms, the cap goes to ~150 ms, and **R4 and R5
   both come into reach at dec 2 with 63 and 83 ms of separation** — clear of the skirt with room.
   ⚠⚠ **BUT THE BURST IS NOT A NEUTRAL KNOB AND MUST NOT BE TREATED AS ONE: C511/C512 make the
   burst's START the phase reference this entire line measures lead time FROM.** Lengthening it may
   move the regions rather than merely reveal more of them — ⭐ **which is itself a sharp test** (if
   the regions are fixed lead times from burst start they should not move at all), but it is a
   *different experiment* and needs its own pre-registration, not a quiet re-run of K33.
   ⛔ **And it needs a cu2 FLASH.** That is permitted (`enterdfu.py`, no bench move, **cu2 only,
   never cu1**) but it is the largest step this round would take unattended, and AUTOPILOT's warning
   stands: a flash that goes wrong with nobody present ends the week. ⇒ ⭐⭐ **THE DESIGN IS NOW PINNED AND IT IS TWO STAGES: K34a asks whether a longer burst MOVES the
   regions (the control), and only a *same lead times* answer licenses K34b, which is K33 finally
   runnable at 41% of the reachable top instead of 101% of it.** ⛔ If the regions MOVE, that is the
   bigger finding and **K34b must not be run at all**. ⛔ **Stage 2 alone is not a valid experiment.**
   ⇒ **The next tick's decision is the FLASH, and K34 prices it**: permitted, cu2 only, `enterdfu.py`
   retries on a trigger failure, a bad flash costs Rig B but not the bench (cu1 untouched), and the
   new build must be verified **functionally and from the AIR** — a primer that broke P1 at burst 500
   must come back clean at 0.50, because a version string is not evidence (C461).

⛔⛔ **AND THE RULES ANY OF THOSE MUST SATISFY, ALL EARNED THIS ROUND:** derive every reference
from `--inventory` and never from a write-up (**M76**); compute the power **per arm** first
(**M68**); simulate **both** a false-fire rate and a power figure before the capture (**M70/M75**);
**give the no-verdict branch a MEANING in advance** (**M74**, and K29 shows it is cheap); name the
arm each clause was measured on (**M71**); name the ladder and n **in the same string** as every
rate (**M73**); compute the ladder's top **per arm** (**M77**); and before withdrawing a band,
work out **which way its defect pushes** (**M78**); and ask what a threshold assumes about **the condition you are about to vary**, because *absolute* hides that assumption rather than removing it (**M80**); and **when a design changes shape, re-read the note that produced its numbers and check each requirement against the NEW shape** (**M81** — the round's most expensive lesson, because it cost two captures and only the bench could catch it).

---


## ⭐⭐⭐⭐⭐ 2026-09-17 03:5x-05:0x — THE INTERLEAVING IS WITHDRAWN AND THE REGIONS ARE REAL. READ THIS FIRST.

util7 **81 → 84** across the whole round, 03:5x-11:5x. **TWENTY-TWO units closed: K21 (C524), K22 (C525), K23 (C526), the `keri` re-run (C528) the drift gate's own price (C527) the frame-locked notch (C529, closed offline with no capture) a correction to C527's own scope (C530/M73) and Y1's costed remedy spent to a decisive end (C531/M74 — *interleaving* is EXCLUDED) the replacement estimation band withdrawn before it ran (C532/M75), `idteck` measured over the full span and `indala224` closed as not-measurable (C533), M76's fix built as the `--inventory` tool (C534), the burst ceiling located on the air and traced to the PROBE (C535/M77) **the frame reading refuted at a second unambiguous region on `nexwatch`** (C536) the common ladder measured, which settles that the cross-arm band is a THREE-arm band (C537/M78), ⭐⭐⭐ **THE THREE-ARM BAND RUN AND FIRED — the regions are SHARED across three arms and two frame lengths** (C538), and the client-side confound attacked with a new verified knob (C539-C543/M79-M81: the knob works, its stretch is 1.65x not 2x, the design's arithmetic, and three captures, the last of which fired its own *closes this approach* branch and named a one-arm successor by arithmetic).

⚠⚠ **AND THE ROUND'S OWN SCORE ON ONE DISEASE, WHICH IS THE MOST USEFUL LINE IN IT: FIVE OVER-REACHES, ALL CAUGHT AND ALL WALKED BACK INSIDE THE ROUND** — **M71** a gate justified on the wrong **ARM** · **C526** a level from one session **PAIR** · **C530** a rate from one **LADDER** · **C532** a point estimate quoted for an **INTERVAL** · **M76** a reference list from the **WRITE-UPS** instead of the data. ⇒ **Every one is a reference or a scope taken from the wrong place** — plus **M78**, where A2 was called *unsound* when its defect could only bias it toward REFUTED, so a FIRING verdict was thrown away that did not need to be. ⭐ **That one gives something back, and it is the same error in the other direction: a conclusion drawn without checking which way the evidence could bend.** ⭐ Each was found by a check this round itself added, not by the next round paying for it. ⇒ **the checks are working and the instinct is not: assume every number quoted from one configuration is wrong until its configuration is named beside it, in the SAME STRING and not a nearby header** (M73). ⛔ C526 RETRACTS a number C525 published an hour earlier — read that retraction before quoting any level — and C527 makes every *NO VERDICT, DRIFTED* on this line one-in-four likely to be noise.** ⛔ **No bench move, nothing flashed on
either unit**, cu2 armed and disarmed through the `finally` on **both** capture runs — `disarm: ok`
twice, and its mode verified as `Tag Reader` **by asking the device** before the first arm — and
**cu1 untouched**. **Detail: `ChameleonUltra` C524, M69, M70, `burstsync.py` K21/K22,
`framescale.py` `--k21`/`--k22`, commits `aaa641d0` `d20f15d6` `394834a0` `6146ab5f` `ecd7e557`.**

⭐⭐⭐ **THE HEADLINE, AND IT RETIRES THE PREVIOUS ROUND'S BIGGEST POST-HOC OBSERVATION.** The last
block below ends with *the two arms' structure INTERLEAVES* and calls it the next criterion's job.
**That criterion was written, its power computed, and it was run on fresh seeds. The four regions
replicate at the cells named for them. The interleaving does not.**

| band | result |
|---|---|
| **Y3 — do the named regions come back?** | ⭐ **FIRES.** `keri` high at **95,100,105** in both seeds and 140-150; `indala` notched at **120,125,130** and **165,170,175** in both. **The first LOCATION band in this project**, legitimate only because K19/K20 named the cells first and these seeds are fresh |
| **Y1 — one profile or two?** | ⛔ **NO VERDICT** — but the cross-arm Spearman is **+0.402 and +0.664**, POSITIVE in both runs, against a band needing **<= −0.52** for *interleaving*. **The wrong sign, twice** |
| **Y2 — the offset** | ⛔ **WITHDRAWN BEFORE THE CAPTURE** for want of power (M70). No offset of any size may be quoted in either direction |

⛔ **`indala`'s 115 ms cell met the notch threshold in NEITHER fresh seed**, so the first notch is
**120-130**, not 115-130. Reported, not tested.

⛔⛔ **WHAT MAY BE SAID AND WHAT MAY NOT.** *Interleaving* requires the arms to be OPPOSED, and they
are not — so **the interleaving claim is withdrawn from the gap register**, and its appearance is
explained by the thing the band named in advance: **K19 scored `keri` with a FORWARD detector
(median 25-31%, only a hump is detectable) and K20 scored `indala` with an INVERSE one (median 75%,
only a notch is), and ONE SHARED PROFILE yields an interleaved-looking pair by construction.**
⚠⚠ **But *one shared profile* is NOT established either.** Only one run clears +0.52, so the
pre-registered answer is NO VERDICT and that is the answer. ⛔ **Do not upgrade it.** The
disattenuated values (+0.56, +0.92), the pooled-seed figure (+0.523) and the per-arm reliabilities
(`indala` +0.780, `keri` +0.662) are all **post-hoc and none is the band's statistic** — the band
asked for ±0.52 in EACH run and got it in one.

⭐⭐ **AND THE NO VERDICT CAME WITH ITS OWN PROBABILITY ATTACHED, WHICH HAS NOT HAPPENED HERE
BEFORE.** Y1's power was simulated before the capture: **77% SHARED under one shared profile, 77%
OPPOSED under anti-alignment, ~2% errors each way, and a real 20 ms offset landing in NO VERDICT
98% of the time.** ⇒ **this is the 23% branch firing, not a band that was badly built** — and the
remedy was priced in the same breath: **`--reps 12` takes Y1 to 90%.** That is unit 1 below.

## ⭐⭐⭐ TWO DEFECTS FOUND BEFORE THE BENCH WAS TOUCHED, AND THAT IS THE ROUND'S REAL LESSON

⛔⛔ **M69 — ONE SHUFFLE FOR EVERY ARM WAS A CROSS-ARM CONFOUND.** `burstsync.k12()` built ONE
shuffled plan and ran **every arm through it**, so both arms saw the identical cell→position
mapping in every round. M60 established that **position is a variable on this bench**, so whatever
it contributes entered both arms' profiles **identically and manufactured a positive cross-arm
correlation out of nothing.** ⚠ **It touches no WITHIN-arm verdict** — K12 through K20 are all
within-arm and all stand — but it is fatal to a cross-arm one. ⇒ `--per-arm-shuffle` derives and
records a seed per arm, every cap now carries `_plan`, and the scorer **REFUSES an unshuffled cap
by name.** ⭐ The only banked both-arm caps (`k15`, `k16`) are refused by that path, which is the
guard working. ⇒ **Before comparing two arms, enumerate what the harness gives them in common.**

⛔⛔⛔ **M70 — A BAND KILLED BY SIMULATION BEFORE ITS CAPTURE, THE FIRST TIME THAT HAS HAPPENED
HERE.** Y2 asked whether the profiles are offset: cross-correlate at lags 0, ±5..±25 ms, fire when
the best non-zero lag beats lag 0 by >= 0.30 in both runs with the sign agreeing. Pre-registered,
replicated across two seeds, **and broken**:

- **41% FALSE-FIRE** against a null of two INDEPENDENT profiles. The median null gain is **+0.37**,
  already above its own threshold, because **lag 0 is one correlation and the best of ten lags is
  an order statistic. A maximum's null is not zero.**
- At a 0.3% false-fire bar it needs a gain of 1.10, and there it detects a **real 20 ms offset
  0.3% of the time.** A fixed signed lag removes the argmax and still reaches only **37% power at
  a 5% false-fire rate.**

⚠⚠ **SIX BANDS (M62, M63, M64, M66, M67, M68) WERE ALL PRE-REGISTERED AND ALL SIX WERE FOUND
BROKEN BY THE DATA THEY WERE BUILT TO JUDGE — six captures spent discovering that six criteria
could not carry a verdict. M70 was found by 24,000 simulated draws and cost NO BENCH TIME.**

⇒ ⭐⭐⭐ **THE RULE THIS ROUND ADDS, AND IT SUPERSEDES *ask what single cell decides this*:
SIMULATE EVERY BAND TWICE BEFORE THE CAPTURE — once under NO effect (the false-fire rate) and once
under the effect AS DESCRIBED (the power). If either number is unacceptable the band is not ready,
and finding that out on the bench is paying for it twice.** ⭐ It does not only kill bands: Y1 and
K22's Z1 both passed the same treatment and are the stronger for carrying their numbers.

## ⭐⭐⭐⭐ AND K22 WAS RUN IN THE SAME ROUND — A THIRD REGION AT 20-30 ms (C525)

⭐⭐⭐ **`indala` IS AT 100% IN BOTH SEEDS AT A 20 ms LEAD.** The last unmeasured region under the
burst ceiling — K14/K15/K16 stopped at 40 ms and K19/K20 started at 85 — is now measured, two fresh
seeds (131, 149), both arms per run, per-arm shuffled, all gates passing, **and Z2, the continuity
gate, passing on both arms**, so the known 50-65 ms hump reappeared before the new region was read.

| arm | 20 | 25 | 30 | 35 | 40 | 45 | 50-65 (the known hump) |
|---|---|---|---|---|---|---|---|
| `indala` | **100 / 100** | **88 / 75** | **100 / 62** | 25 / 38 | 12 / 38 | 25 / 25 | 75-100% |
| `keri` | **100 / 75** | 12 / 38 | 25 / 38 | 12 / 0 | 12 / 0 | 12 / 12 | 38-100% |

⭐ **Z1 FIRES for `indala` at `20,25,30`** and **is REFUTED for `keri`**, whose 25-35 cells are
12-38%. ⚠ **`keri`'s 20 ms cell is elevated in BOTH seeds and STANDS ALONE** — the two-cell rule
refuses to call one cell a feature, and it is reported, not counted.
⚠⚠ **A REFUTED Z1 means *no feature as strong as the known hump*, NOT *flat*.** Its power was
simulated before the capture: **96% at two cells of 80%, 47% at 60%, 16% at 50%**, against a
**0.00%** false-fire rate under the measured floor and 0.01% under a lone 90% cell.

⭐⭐ **PRACTICAL: 65 ms IS NOT THE BEST LEAD TIME.** `indala` beats its 96/83% at 65 ms with
**100/100% at 20 ms**. 65 ms remains only *the one measured to work on three arms at once*.

⛔⛔ **AND THE PROFILE IS NOW BOUNDED BY THE INSTRUMENT AT BOTH ENDS.** Z3: the lowest cell at or
above 40% is **the ladder's FIRST cell, 20 ms, in every seed on both arms** — the profile is
already elevated where the measurement begins. ⇒ **No wing at the bottom edge of any ladder is
licensed for `indala` or `keri`**, which is W2's teeth (C522) earned at the other end, and **the
region's downward extent is unknown** exactly as the profile above 200 ms is.

⚠⚠ **POST-HOC AND LABELLED — IT CORRECTS K22's OWN PRE-CAPTURE ARITHMETIC.** K22 declared the
frame-locked notch (`gproxii`'s 1.22 frames is **20 ms** on these arms) UNTESTABLE there, because a
notch needs a body and the expected level was the 0-17% floor. **20 ms is at the CEILING, so a
notch detector there WOULD have power.** ⛔ **No verdict is taken from this run** — choosing a
detector after seeing the level is the thing this project exists not to do. It is unit 2 below.

⚠ `indala`'s seed-149 split-half is **11.5 points**, the closest any run here has come to the
15-point drift gate. It passes and is recorded rather than glossed.

## ⭐⭐⭐⭐ AND K23 RAN TOO — THE REGION IS BOUNDED AT BOTH ENDS, AND IT RETRACTS C525 (C526)

⭐⭐⭐ **`indala`'s 20-30 ms REGION BEGINS BETWEEN 5 AND 10 ms.** The 1-65 ms ladder, two fresh
seeds (151, 167), both arms per run, per-arm shuffled. **V1 FIRES** — and **both** continuity
gates passed before it was read: V2 (the older 50-65 hump) on all four anchor cells in both seeds,
and **V2b, C525's OWN region, on all three in both.** Then 1 and 5 ms come in at **38/25% and
25/25%**, and V3 puts the lowest cell at or above 40% at **10 ms in both seeds**.
⇒ **With C525's top edge between 30 and 35, the region is located at BOTH ends for the first time.**
⚠ A firing V1 licenses *the profile comes down*, never *it reaches a floor* — at a true 62% the
detector fires 14% from noise, and that was stated before the capture.

⛔⛔⛔ **AND IT RETRACTS A NUMBER FROM THE BLOCK ABOVE. C525 SAID `indala` IS AT *100% IN BOTH
SEEDS AT 20 ms*, ABOVE ITS 96/83% AT 65 ms, AND CONCLUDED THAT *65 ms IS NOT THE BEST LEAD TIME*.
THE RANKING DOES NOT REPRODUCE.** In K23's own sessions the same two cells **INVERT**:

| cell | K22 (seeds 131/149) | K23 (seeds 151/167), one hour later |
|---|---|---|
| 20 ms | **100% / 100%** | **75% / 50%** |
| 25 ms | 88% / 75% | 88% / 62% |
| 30 ms | 100% / 62% | 62% / 88% |
| 65 ms | (not in that ladder) | **88% / 100%** |

⇒ ⭐⭐ **THE REGIONS REPRODUCE AND THEIR RELATIVE HEIGHTS DO NOT.** ⛔ **No cell may be ranked
against another cell across sessions on this bench, and *the best lead time* is not a thing this
instrument can identify.** 65 ms keeps its standing for the only reason it ever had one — it is the
value measured to work on three arms at once.
⚠⚠ **This is C504's *carry the range, not the number* for the FOURTH time, and it was broken one
hour after being written into a band.** What survives from C525 is the region's **existence** and
its **location**, both re-confirmed by the V2b gate that was added for precisely this purpose.

⛔ **`keri`: NO VERDICT — its seed-167 run DRIFTED**, split-half **15.9 points** against a
15-point gate, so nothing about `keri` is read from this ladder and **its own bottom edge is still
unmeasured.** ⭐ The drift gate firing on a real run, one round after `indala`'s 11.5 was logged as
the closest call yet, is that control earning its keep and not a nuisance.

⛔⛔ **THE AXIS HAS A FLOOR NO PRIMER REACHES BELOW: ~192 ms of field-up overhead** (`K12_OVERHEAD_MS`).
A 1 ms primer is 193 ms of elapsed time, so *below 20 ms* means *below 212 ms of elapsed*. ⚠ And the
no-primer control is **not** the bottom of that axis — it is a fresh burst (arrivals 1.0 against
0.50), a different condition, and it wandered from 62% to 25% between the two runs.

## ⭐⭐⭐⭐ AND FOUR MORE UNITS RAN — `keri`'s EDGE, AND THE DRIFT GATE'S PRICE (C527, C528, M71, M72)

⭐⭐⭐ **BOTH ARMS' BOTTOM EDGE IS BETWEEN 5 AND 10 ms, MEASURED SEPARATELY.** `keri`: 1 and 5 ms at
**0/12% and 0/0%**, lowest elevated cell **10 ms in both scored seeds** — the same as `indala`'s.
⭐⭐ **PUT BESIDE C526's RETRACTION, THAT IS THE ROUND'S CLEANEST LESSON: V3 reports 10 ms in ALL
FOUR scored seeds across BOTH arms, while C526 had the same cells' LEVELS inverting an hour apart.**
⇒ ⭐ **ASK THIS BENCH WHERE A FEATURE IS, NEVER HOW TALL IT IS.**

⛔⛔ **IT TOOK FOUR SESSION PAIRS AND THREE OF THEM WERE LOST TO OUR OWN CONTROLS, NOT TO THE AIR.**

| pair | why nothing was read |
|---|---|
| s151 / s167 | drift gate (15.9) |
| s181 / s193 | ⛔ **M71 — my gate was wrong** |
| s199 / s211 | drift gate (20.5) |
| **K24: s223 / s227 / s229** | ✅ **V1 FIRES** — three seeds, selection rule pinned first |

⛔⛔ **M71 — A CONTINUITY GATE MUST BE BUILT FROM A FINDING THAT HOLDS ON THE ARM IT GATES.** K23's
V2b asked C525's 20-30 ms region to reappear — **but C525 established that on `indala` and REFUTED
it on `keri`**, whose 20 ms cell was elevated and *stood alone*. `keri` passed all four instrument
gates and V2, then had V1 blocked by a gate asking for something already known not to be there.
**It blocked the one arm the re-run existed to measure.** ⚠⚠ **Seventh member of the same family,
and it arrived through the fix for an earlier one**: M63 → wings by position → M67 → the arm's own
median → M68 → absolute thresholds from prior measurement → **M71, prior measurement ON THE WRONG
ARM.** ⇒ **Name the arm each clause of a gate was measured on.** That is C514 applied to the
CONTROLS, which is where nobody was looking.

⭐⭐⭐ **M72/C527 — AND THE DRIFT GATE ITSELF HAD NEVER BEEN PRICED. IT FAILS ON PURE COUNTING
NOISE 14-16% PER RUN AND 26-30% PER TWO-SEED PAIR.** K16's 15-point threshold was chosen by eye.
40,000 draws, an 11-cell ladder at `--reps 8`, **no drift whatsoever**: the sd of the split-half
difference at n=88 is **10.6 points**, so 15 is **1.4σ** and the 95th percentile is **20.5**.

⭐⭐ **THE CONSEQUENCE IS RETROACTIVE FOR THE SHORT-LADDER RUNS: a *NO VERDICT — DRIFTED* on an
11-cell ladder is about one-in-four likely to be noise, and is NOT evidence that the bench moved.**

⛔⛔ **AND THAT RATE IS THE LADDER'S, NOT THE GATE'S — C530/M73 SCOPES IT, BECAUSE THE FIRST VERSION
OF THIS BLOCK OVER-REACHED.** The statistic is a split-half over **every cell**, so its sd scales
with the run's total n:

| ladder | n per half | sd(Δ) | 15 pts is | P(fail) |
|---|---|---|---|---|
| **11 cells, reps 8** (K22/K23/K24) | 44 | **10.6** | **1.4σ** | **14-16%** |
| **25 cells, reps 8** (K17-K21) | 100 | 6.7-7.0 | **2.2σ** | 2.1-2.7% |
| **25 cells, reps 12** | 150 | 5.5-5.7 | **2.7σ** | 0.6-0.9% |

⇒ ⭐ **EVERY lead-time run above 80 ms went through a properly calibrated 2.2σ control and is NOT
qualified by C527 at all.** ✅ Both drifted verdicts actually on record are short-ladder, so the
caution holds exactly where it was applied. ⚠⚠ **AND THE DISEASE IS THIS ROUND'S OWN, THREE TIMES:
M71 a gate justified on the wrong ARM, C526 a level from one session PAIR, C530 a rate from one
LADDER.** ⇒ **M73 — C514's *one arm is a scope, not a law* was too narrow. Name the configuration
beside every simulated rate, as ONE string**: C527's table did carry its n in a header and the
prose still over-reached. ⚠⚠ **It also dissolves an arm difference that was there to be claimed** — `indala` 0 of 6
over the gate against `keri` 2 of 6, but P(0 of 6) = 0.34 and P(≥2 of 6) = 0.26 at that rate, so
⛔ ***`keri` drifts more* is NOT a finding** (M58, fifth time).

⛔⛔ **THE GATE IS DELIBERATELY NOT CHANGED, AND THAT IS AN OPERATOR DECISION.** It is conservative
rather than wrong: it costs runs and manufactures nothing. **Re-pointing it would re-base how every
K17+ run that passed it is read — the same class of change as re-pointing `pm3_read`.**
⭐ The remedy that does not touch it is seeds, and it is priced: **two give a 71% chance of a usable
pair, three give 93%.** K24 is that, with the selection rule pinned before the capture.

⚠ **TWO DISCLOSURES ON K24.** All three of its seeds passed the gate (Δ 2.3, 6.8, 6.8), so the
selection rule **did no work here** and is reported because it was pinned. And it hit a **tie the
rule did not specify** — ✅ checked rather than hoped: the other tie-break gives the **identical**
verdict. ⛔ The rule must name a tie-break before its next use.

## ⭐⭐⭐⭐⭐ AND THE COSTED REMEDY WAS SPENT — *INTERLEAVING* IS DEAD, AND THE QUESTION WAS WRONG (C531, M74)

⭐⭐⭐ **K25 re-ran Y1's bands UNCHANGED at `--reps 12`** on two fresh seeds (163, 179), both arms
per run, per-arm shuffled, **all gates passing** (split-half **5.6/6.2 and 0.7/5.6**). C524 priced
the move at 77% → **90%** power. ⛔ **Y1 RETURNED NO VERDICT AGAIN: +0.603 and +0.490 against
±0.52** — one clearing, one missing by three hundredths, exactly as at reps 8.

| | cross-arm Spearman |
|---|---|
| reps 8 (K21) | +0.402, +0.664 |
| reps 12 (K25) | +0.603, +0.490 |
| **all four** | **mean +0.540 — ALL POSITIVE, none below the p=0.05 critical 0.402** |

⭐⭐⭐⭐ **WHAT IS NOW FIRM: *INTERLEAVING* IS EXCLUDED.** Y1's OPPOSED branch needed r <= −0.52 in
both runs and had **77% power at reps 8 and 90% at reps 12** by its own pre-capture simulation. It
fired **0 of 4** while **every** measurement came back positive. ⇒ **one arm is NOT high where the
other is low, and that reading is finished** — the claim C524 could only make weakly.
⭐ **A band whose middle is unusable can still have a decisive END, and a write-up that reports
*no verdict* and stops has thrown that away.**

⛔⛔ **AND *ONE SHARED PROFILE* IS STILL NOT ESTABLISHED — BECAUSE THE LIMIT WAS NEVER POWER, IT WAS
THE QUESTION (M74).** Simulating weighted mixes of one shared profile and two private ones at reps
12 gives median r **+0.83 at a shared weight of 1.0 (5th pct +0.66), +0.71 at 0.8, +0.47 at 0.6,
+0.03 at 0.0.** ⇒ the observations sit at **w ≈ 0.6-0.8: substantially but not completely shared**,
and +0.490 is *below a fully-shared truth's 5th percentile*. **Y1's dichotomy has no branch for
that** — a limitation C524 named as a limitation before this run confirmed it.

⛔⛔⛔ **DO NOT MOVE THE THRESHOLD TO +0.45 AND DECLARE SHARED.** It was the p=0.01 permutation
critical value, fixed before any cross-arm number existed; lowering it now is fitting, whatever
justification is attached. **The band stands, its verdict stands, and what changes is the next
band's QUESTION.**

⇒ ⭐⭐ **M74 — THE SEQUENCE, DECIDED IN ADVANCE SO IT IS CHEAP:** a pre-registered band returns NO
VERDICT on consistent-looking data → **raise n ONCE** (legitimate, pre-priceable, answers *was it
power?*) → if it repeats, **replace the dichotomy with an ESTIMATION band** that reports the
quantity with an interval. ⛔ **Never a fourth step of re-tuning the original threshold.**

⭐ **Y3 FIRED A SECOND TIME**, so the four named locations have now held across **three independent
seed pairs** since K19/K20 named them. ⚠ `indala`'s 130 ms cell missed in one seed of this pair;
the region still carries its two cells in both.

## ⭐⭐⭐⭐ AND `idteck` RAN, `indala224` CLOSED AS NOT-MEASURABLE, AND A REFERENCE LIST OF MINE PROVED WRONG (C533, C534, M76)

⭐⭐⭐ **A THIRD ARM HAS LEAD-TIME STRUCTURE.** `idteck` over the **full 10-200 ms span at 5 ms — 39
cells**, two fresh seeds (241, 251), per-arm shuffled, **both gates passing** (pooled 36.5/40.7%,
split-half **1.3 and 4.5**, P1 0.50), median **25%**. **A1 FIRES: three regions — `50-65`,
`135-150` and `180-195` ms**, each >= 3 adjacent cells elevated in BOTH seeds.
⛔ **A detector's run length belongs to the LADDER, not just the detector**: over 39 cells a 2-cell
run false-fires **13-26%** depending on where the median lands on the n=8 grid, so **3** was
required, which holds under 0.8% at any median. Flat-ladder false-fire, simulated first: **0.2%**.

⛔⛔ **`indala224` IS CLOSED AS NOT MEASURABLE ON THIS KNOB, not deferred.** Precision **0%** so
*exact* is a flat zero (C502) — **and its marker is the SAME one `indala` uses**, both going through
`lf indala demod`, so *decoded* cannot tell a 224-bit frame from a 64-bit one. ⛔ And no
length-keyed marker rescues it: the demodulator reports **254-611 against 224** for this arm.
**There is no rate to put on the y-axis.**

⛔⛔⛔ **AND A2 — *is the structure where the other arms' is?* — CAME BACK REFUTED AND THAT VERDICT
IS WITHDRAWN AS UNSOUND. THE FAULT WAS MY REFERENCE LIST.** It scored `180-195` as an orphan ⇒
*this arm's structure is its own*. ⛔ **`indala` measures 75-100% at 180-195 ms across SIX
independent seeds and `keri` 25-92%.** ⚠⚠ **The list was built from the regions a band had TESTED
AND FIRED ON, not from the regions the bench had MEASURED AS HIGH** — and 180-195 was never a named
feature precisely because it is where **C522's W2 FAILED** (*no floor by 200 ms*) and **K20's X2
PASSED** (*195 ms is 100%/88%*). Two bands reported it high and neither made it a feature, because
each asked a different question about it. ⇒ **A2 reads in NEITHER direction.**

⭐⭐⭐ **M76's FIX IS BUILT AND IT IS A TOOL, NOT A NOTE: `./framescale.py --inventory caps/k1*.json
caps/k2*.json`** sweeps **every banked cap — 758 cap-measurements, five arms** — and reports per arm
and per cell how many independent seeds measured it **HIGH (>= 5 of 8)** and **LOW (<= 2 of 8)**.
⛔ Those are the n=8 grid, not a taste, and it is an **inventory, not a band**: it claims nothing.

| arm | HIGH in EVERY seed, runs of >= 2 adjacent measured cells |
|---|---|
| `idteck` | **15-20, 55-65, 95-100, 140-145, 180-190** |
| `indala` | **10-15, 25-30, 50-65, 95-110, 140-160, 190-195** |
| `keri` | **15-20, 60-65, 140-145** |
| `nexwatch` | **55-65, 135-140** |
| `gproxii` | 20-40, 80-180 |

⚠⚠ **FOUR OF THE FIVE ARMS SHARE HIGH REGIONS NEAR 15-20, 55-65, 95-105 AND 140-145 ms — INCLUDING
`nexwatch`, WHOSE FRAME IS TWICE THE OTHERS'.** ⛔⛔ **POST-HOC, from caps already read, and claimed
as NOTHING.** It is the reference list a pre-registered band must be built against — the whole point
of M76 — and **not** evidence for the pattern it displays. ⚠ And read the tool's own caveat:
*adjacent* means adjacent in **that arm's measured cells**, which are not a common grid.

## ⭐⭐⭐⭐⭐ AND THE LAST TWO UNITS ANSWERED THE FRAME QUESTION AGAIN AND FOUND THE CEILING'S CAUSE (C535, C536, M77)

⭐⭐⭐⭐ **`nexwatch` — THE ONE ARM THAT CAN DISCRIMINATE — PUTS ITS REGIONS AT THE SAME MILLISECONDS
AS THE 2048-FRAME ARMS, NOT AT TWICE THEM.** Its frame is **4096 samples against the others' 2048**,
so a frame-locked structure predicts DOUBLE positions. Measured over its own full ladder, two fresh
seeds, all gates passing, P1 clean in every cell, and **A1 — the band already committed for
`idteck`, applied unchanged — FIRES with three regions:**

| `nexwatch` measured | frame-locked predicted | the 2048-arms' own region |
|---|---|---|
| **50-65 ms** | 100-130 ms | 50-65 ms |
| **180-190 ms** | 360-380 ms | 180-190 / 190-195 ms |
| **10-20 ms** | 20-40 ms | 10-15 / 15-20 ms |

⇒ ⭐⭐ **THE WORKING POINTS ARE FIXED IN MILLISECONDS, ON FOUR ARMS AND TWO FRAME LENGTHS.** This
extends C520 — which had only the 55-65 hump — to a second unambiguous region **125 ms away.**
⚠⚠ `nexwatch` is also high at **100-105 ms**, which is **BOTH** where the others are high (95-110)
**AND** the double of their 50-65 ⇒ **ambiguous, excluded from the argument, said so out loud.**
⚠⚠ **AND THE DISCLOSURE: A1 is pre-registered and fired; the FRAME COMPARISON is not a band.** A2 is
that band and it is **unsound** (M76), which K27 pinned in advance. ⭐ It is carried in this
direction only, because **foreknowledge cannot manufacture the ABSENCE of a region at 360-380 ms.**

⛔⛔⛔ **AND THE INSTRUMENT'S OWN CEILING NOW HAS A MEASURED CAUSE — M77, AND IT COST A CAPTURE.**
`nexwatch`'s first ladder (10-200, `idteck`'s exactly) **FAILED P1 on both seeds, on exactly one
cell and the same one: 200 ms** (arrivals 0.94/1.00) while **195 ms sat at exactly 0.50 in both**,
as did the other 38. ⭐⭐ **`idteck` is the control: its 200 ms cell passed cleanly, and the ONLY
difference is the probe — `lf read -s 6144` (49 ms) against `-s 12288` (98 ms).**
⇒ **the 500 ms burst must cover `primer + overhead + THE PROBE ITSELF`, and the probe was never in
the arithmetic.** ⇒ ⭐ **A ladder's reachable top is `500 − overhead − probe_ms` and is PER ARM —
K19's *~200 ms is the reachable maximum on this rig* was `keri`'s number quoted as the bench's.**
`burstsync` now **computes and prints that top per arm before every run** and flags cells above it.
⚠ **The computed top is OPTIMISTIC** (it says ~210 for `nexwatch`, which failed at 200), so it is an
**upper bound and P1 decides.** ⛔ **K27's first pair is NO VERDICT by the gate as committed** — one
bad cell of 39 ends the arm, and **the gate was NOT loosened after seeing the data**; whether it
should be per-cell is the operator's call.
⭐⭐ **AND THE CONTROL CAUGHT WHAT I DID NOT**: P1 was written for K12 to police a different worry
entirely, and it landed on the one arm and the one cell where a term was missing from the design's
arithmetic. ⇒ **keep a control even when it looks redundant.**

## ⭐⭐⭐⭐⭐ AND THE LAST UNIT SETTLED WHICH CROSS-ARM BAND CAN EXIST AT ALL (C537, M78)

⛔⛔ **FIRST, A DESIGN FACT NOBODY HAD CHECKED: THE ARMS HAD NEVER BEEN MEASURED ON ONE LADDER.**
Only `idteck` (K26) and `nexwatch` (K27) carried the full span in a single run. **`indala` and
`keri`'s coverage was a UNION of four different ladders** — 85-200 twice, 20-80, 1-65 twice — with
different seeds, reps, arms present and cell counts feeding the median every band is read against.
⇒ any cross-arm comparison over those cells compared a **stitched** profile with a **measured** one,
which is M69's confound in a new place. ⭐ Found by checking the caps mechanically (M76's habit
turned on the DESIGN rather than on a reference).

⭐⭐ **K28 fixed it: `indala` and `keri` on the same 38-cell 10-195 ms ladder, two fresh seeds, all
four gates passing** (pooled 63.5/63.8% and 40.5/38.2%, split-half 3.3/3.9 and 5.9/3.9, P1 0.50).

| arm | median | A1 |
|---|---|---|
| `keri` | **25% / 25%** | ⭐ **FIRES — `10-25`, `95-105`, `140-150` ms** |
| `indala` | **75% / 75%** | ⛔ **REFUTED, AND WORTHLESS — *median+25* is 100%, THE CEILING** |

⭐ **That is M68 reproducing exactly where K28's own pre-capture note said it would**, and the
difference from M68's original is that the no-power outcome was **predicted before the capture**.

⇒ ⭐⭐⭐ **SO THE NEXT BAND IS FULLY SPECIFIED BY ARITHMETIC, AND IT IS NOT A FOUR-ARM BAND:**
**`keri` + `idteck` + `nexwatch`** (medians 25-38%), **all three on the forward detector, all three
on the common 10-195 ladder** — and it **keeps `nexwatch`, the only arm whose frame differs and so
the only frame discriminator** (M65/C520/C536). ⛔ **`indala` is scoped OUT by arithmetic**, which is
K20's move a second time. ⚠ For `indala` the detectable feature is a **notch**, so any comparison
involving it compares a low region with a high one — and C531 already established the two PSK arms'
profiles **correlate positively**, so that comparison is as answered as this instrument can make it.

⛔⛔ **AND C533's WORDING IS CORRECTED — THE ONE SELF-CORRECTION THIS ROUND THAT GIVES SOMETHING
BACK (M78).** C533 called A2 *unsound*, flatly. **But its defect is an OMISSION from its reference
list, and an omission can only turn a real match into an ORPHAN: it manufactures *REFUTED* and
CANNOT manufacture a FIRE.** ⇒ **`idteck`'s and `nexwatch`'s REFUTED A2 verdicts stay withdrawn; a
FIRING A2 is not compromised at all.** ⭐ And **`keri`'s A2 FIRES — three of four named regions
found, NO orphans** ⇒ **the first cross-arm location result here that is both pre-registered and
sound.** ⚠ Its 50-65 region missed the three-cell rule in this pair though the inventory has it HIGH
in every seed at 60-65 — the two-cell width A1's false-fire budget deliberately refuses.
⇒ ⭐ **M78: before withdrawing a band, work out which way its defect PUSHES. The verdicts on the
other side of that direction survive.**

## ⭐⭐ THE NEXT HANDS-OFF UNITS, IN ORDER — ITEMS 0 AND 1 ARE K22'S OWN CONSEQUENCES

0. ✅ ~~**K22, the sub-20 ms ladder, and `keri`'s re-run**~~ **ALL RUN THIS ROUND —
   C525, C526, C528.** ⛔ **Do not re-run any of them.** Both arms are bounded at both ends and
   the lead-time line has no unmeasured region left under the burst ceiling. ⛔⛔ Going lower is
   **impossible with this knob**: the axis floor is the ~192 ms field-up overhead, not the
   primer, so **the next move down is the overhead itself** — a different experiment needing
   its own criterion. ⭐ And the two things this round hands forward are METHOD, not measurement:
   **M71** (name the arm each clause of a gate was measured on) and **M72** (a control needs its
   null distribution computed too — and add a TIE-BREAK to K24's selection rule before reusing it).
1. ✅ ~~**THE FRAME-LOCKED NOTCH**~~ **CLOSED THIS ROUND, WITH NO CAPTURE — C529.**
   `gproxii`'s notch is 1.22 frames, which on these two arms is **20.0 ms**. Eleven
   independently seeded measurements now carry the 15/20/25 ms cells: mean **82% / 76% / 36%**,
   and **the 20 ms cell never falls below 50%**. ⭐⭐ Read against a SIMULATED scale rather
   than eyeballed: **a `gproxii`-depth notch fires the detector on 11 of 11 caps; no-notch
   profiles give at most 1.3 of 11. Observed 1 of 11.** ⇒ **REFUTED at that depth.**
   ⭐ What licenses a verdict off banked caps is the DIRECTION — foreknowledge cannot
   manufacture the ABSENCE of a collapse — so a fresh band would re-measure an answered
   question (C473's method). ⛔ **Do not run one.** ⚠ A SHALLOWER notch is not excluded and
   the detector was never built to see one. ⚠⚠ **Post-hoc lead, not a finding**: the low cell
   here is **25 ms on `keri`** (0-38% in eight of nine) — and 25 ms is **1.53** frames against
   1.22, so not even a *notch at a different frame count* fits. It would need its own band.
   ⛔ And it corrected C528's own descriptive *`keri` elevated 10-25* to **10-20**, a level
   quoted from one pair one round after C526 said levels do not survive that.
2. ✅ ~~**K22 — the 20-40 ms region**~~ **RUN AND SCORED THIS ROUND (C525).** Its design, its
   power table and its two caps are in the ChameleonUltra tree; `./framescale.py --k22 caps/k22_*`
   re-derives the whole verdict offline. ⛔ **Do not re-run it and do not re-derive its design** — what is
   open is items 0 and 1 above, which are its consequences.
3. ✅ ~~**Y1 AT `--reps 12`, AND THE ESTIMATION BAND THAT WAS TO REPLACE IT**~~ **BOTH DONE —
   C531 AND C532. ⛔ THE *ONE PROFILE OR TWO* LINE IS EXHAUSTED BY THIS LADDER, NOT PENDING.**
   The remedy was spent (reps 12, 90% power) and the answer did not move; then the estimation
   band that was to replace the dichotomy was **computed before being run and is not viable**
   — one run constrains the shared weight to a **0.55-0.80 wide** 90% range on a 0-1 scale,
   and **pooling all four runs still leaves 0.20..0.85, width 0.65**, non-contiguous. ⛔ Do not
   run it: an interval two-thirds as wide as its own scale is the NO POWER trap in an
   estimate's clothes. ⭐ **What the data supports and no more**: four positive cross-arm
   measurements, **OPPOSED excluded at 77-90% power**, SHARED not established, fully-shared
   disfavoured **~70x** and independent **~11x**, the middle unresolvable.
   ⇒ ⭐⭐ **A SHARPER INSTRUMENT IS A NEW DESIGN, NOT A RE-RUN**: both bands failed for one
   reason — a 24-cell **RANK** correlation at 8-12 reps is blunt here — so it needs either
   far more reps per cell or a statistic using the cell **LEVELS** rather than their ranks.
   ⛔ Criterion first, and **simulate its precision before the capture** (M70/M75).
4. ⭐⭐⭐ **THE MECHANISM — STILL OPEN, STILL THE BIGGEST PRIZE, AND NOW MUCH BETTER CONSTRAINED.**
   ⭐ What this round added to the constraint set, all of it measured: the working points are fixed
   in **MILLISECONDS** on **four arms and two frame lengths** (C536 extends C520 to a second
   unambiguous region 125 ms away); **four of five arms share high regions near 15-20, 55-65,
   95-105 and 140-145 ms** (`--inventory`, post-hoc); both arms' lowest region **begins between 5
   and 10 ms** (C526/C528); there is **no frame-locked notch at 20 ms** (C529); and the two PSK
   arms' profiles **correlate positively in all four measurements** while *interleaving* is
   **excluded** (C531).
   ⛔⛔ **WHAT IS STILL DEAD: not the beat (C515), not settling (C515), not the frame (C520/C536),
   not the modulation, not a protocol property** — and a structure at fixed milliseconds shared
   across four arms and two frame lengths points at something in the READER or the FIELD, not in
   the emission's own timing. ⭐ **That is the first time this line has had a direction.**
   ⛔ Criterion first, and **simulate its false-fire rate AND its power before the capture**
   (M70/M75), **derive every reference from `--inventory` and not from a write-up** (M76), **name
   the arm each clause was measured on** (M71), **name the ladder and n beside every rate** (M73),
   and **compute the ladder's top per arm** (M77).
5. ✅ ~~`idteck` and `indala224` on this knob~~ **BOTH CLOSED — C533.** `idteck` RAN and has three
   regions; `indala224` is **not measurable on this knob at all** and is closed rather than
   deferred (no usable rate exists for it — see the block above).
   ⇒ ⭐⭐⭐ **WHAT REPLACES BOTH, AND IT IS NOW THE CHEAPEST ATTACK LEFT ON THE MECHANISM:**
   **a band pre-registered against the `--inventory` table, on fresh seeds, asking whether the
   shared regions are shared — with `nexwatch` IN IT.** That arm is the only one whose frame
   differs, so it is the only one that can separate *a property of the emission* from *a property
   of the frame* (M65/C520), and the inventory shows it high at **55-65 and 135-140** where three
   2048-frame arms are high at 55-65 and 140-145.
   ⛔ **Derive the reference from `--inventory` and NEVER from a write-up** (M76). ⛔ Compute the
   power **per arm** first (M68), and **name the ladder and n beside every rate** (M73).
   ✅ ~~`nexwatch` needs its own full ladder first~~ **DONE THIS ROUND — C535/C536.** It now has
   **39 measured cells over 182 cap-measurements** and its own A1 verdict, so the cross-arm band
   can be built. ⛔ **Top its ladder at 195 ms, not 200** — M77, measured, twice.
⛔⛔ **STILL LICENSES NOTHING HERE.** Ungraded — no null sweep, no calibration row — so it **moves
no cell**. The gap register carries the evidence and now carries the withdrawal too.

---

⭐⭐⭐ **UNIT 2 AND UNIT 4 OF THE 02:0x LIST ARE BOTH CLOSED** by the 02:4x block above — the
hump does not travel with the frame (C519/C520), and `nexwatch` is measured. ⛔ **Do not re-open
them**; the open units are the ones that block names, and the first of those is now cheap.

⭐⭐ **THE READ-LENGTH LINE IS CLOSED.** C499-C504 answered it, audited the method that nearly broke
it (M60/C500), and corrected two of its own claims (C499's best-length argmax, C493's leading-bit
magnitudes). Everything the tagless bench can say about read length has been said. ⛔ **Do not
re-measure it** — a further sweep would be C473's method: re-measuring a question already answered.

## ⭐⭐⭐⭐⭐ 2026-09-17 02:0x-04:0x — THE LEAD-TIME PROFILE IS STRUCTURED ALL THE WAY OUT. READ THIS FIRST.

util7 **80 → 81** across the whole round (util5 reset to 0 at 03:5x). ⛔ **No bench move, nothing
flashed on either unit**, cu2 armed and disarmed through the `finally` on **every** run — `disarm:
ok` fourteen times — and **cu1 untouched**.
**Detail: `ChameleonUltra` C519-C523, M65-M68, `framescale.py`, `burstsync.py` K17/K18/K19/K20,
commits `41dfc800` `a7de9290` `fdd31f49` `feeec8b0` `977ddd49` `04abbcce` `ff50a85e` `6ce77cbd`
`b1dd4513` `b6a76e9b` `9d218619`.**

⭐⭐ **FOUR UNITS, IN ORDER, EACH ONE SET UP BY THE LAST.** C519 refuted the frame reading offline;
M65 showed that refutation was confounded; C520 broke the confound on `nexwatch`; M66/M67/M68 are
three bands that mis-fired while trying to measure what C520 left open; C522 and C523 are what the
corrected bands found. ⛔ **Every band was committed before its capture and four of them were still
wrong** — the running list is at the end of this block and it is the most useful thing here.

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
⛔⛔⛔ **UNIT 1 BELOW IS CLOSED — the criterion was written and run (C524) and THE INTERLEAVING IS
WITHDRAWN. Unit 3 is written and pinned as K22 but UNRUN. See the 03:5x-05:0x block at the top;
do not re-open unit 1 and do not re-derive unit 3's design.**
1. ✅ ~~⭐⭐⭐ **A criterion for the interleaving.**~~ **DONE — C524.** ⛔ It must NOT be scored on `caps/k19_*` or
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
5. `idteck` and `indala224` remain unmeasured on this knob. ⚠ `indala224`'s precision is 0% (C502),
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
