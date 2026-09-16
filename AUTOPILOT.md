# Unattended rounds — the standing brief

For a round worked while the **operator is away**. Written 2026-09-16 for an absence starting
Wed 16 Sep and running several days.

⛔⛔ **READ §1 BEFORE PLANNING ANY WORK. The bench cannot produce a single new graded cell while
the operator is away, and a round that does not know this will spend itself discovering it.**

---

## 1. What is physically impossible without hands

Two facts in the code, not opinions:

1. `stations.py:108` — `GOLD_SOURCES = frozenset({"t55.pm3", "oem"})`. **Only a real tag licenses a
   verdict.** `Calibration.from_row` refuses every other source and there is no bypass.
2. `RULES.md §3` — a station takes a null sweep **before and after** its routine, and **a passive
   tag has no idle state, so it must be physically removed** for each sweep.

⇒ Every licensable cell needs a tag in the stack; every tag in a stack needs a hand to lift it out
twice. A tagless layout is genuinely hands-off and **plans zero cells** (`--at PM3+CU1` refuses
everything, by name).

⛔ **DO NOT "SOLVE" THIS.** An `--unattended` flag, a sweep exemption, a licence carried across a
multi-day block, a second gold source — each is the defect RULES.md exists to prevent, with a nicer
name on it. The project was created because seven protocols were graded with no calibration row and
published as a positive result. Reproducing that to keep a loop busy is worse than an idle loop.

✅ **What IS hands-off**, and is therefore the whole of an unattended round:

| available | why |
|---|---|
| firmware development + `ctest` host round-trips | no coil involved |
| `./runtests` (463 tests, 0.2s, no hardware) | the safety net for every refactor |
| `./bench report <session> --regrade` | re-grades **banked transcripts** under today's registry — real measurement, no hardware |
| `./bench plan`, `./bench run --dry-run --no-prompt` | planner and refusal-path work |
| registry rows, docs, refactoring, upstream prep | none of it touches the bench |

⭐ `--regrade` is the one that matters: **every registry correction made this week can be validated
immediately against readings already banked.** That is a genuine measurement loop with no operator.

---

## 2. The work order

Do these in order. Move on when a thing is done **or blocked**, and say which.

### 2a. The measured emitter gaps — the real finding, and the biggest prize

`./bench state` (as of 2026-09-16, cu1 on `v2.2.0-895-gd23839b`) says our emulation is **not
decoded by the Proxmark** for:

`indala` · `keri` · `nexwatch` · `idteck` · `gproxii` · `indala224`

while `em410x`, `viking`, `jablotron`, `pac`, `hidprox`, `ioprox`, `awid`, `gallagher`,
`securakey`, `noralsy`, `fdxb` all pass. These cells are **licensed** — a gold row on `rd.pm3` for
each protocol in the same session — so unlike C473 they are evidence about our emitter.

⭐ This is also exactly the operator's own earlier bench observation (the Proxmark reads Indala,
KERI, IDTECK from a *Flipper* emulation but not ours), now reproduced under the calibration rule.

⭐⭐ **DIAGNOSE IN THIS ORDER — and do NOT re-grade these cells.** The grading answer is already
known, licensed and measured; re-measuring it unattended tells us nothing and is C473's method.
The open question is *why*, which is upstream of any reader and therefore outside the calibration
rule's scope — a capture makes no claim about decodability.

1. ⭐ **`seqdump.py` — NO BENCH AT ALL.** Reads the live PWM entries off an emulating Chameleon over
   USB and diffs them entry by entry against the emitter source's intent. If the emitter builds the
   wrong sequence, this says so with no pad, no tag and no Proxmark, in any bench configuration.
   Needs `DATA_CMD_LF_EMU_SEQDUMP` (3065), which our builds have. **Start here every time.**
2. **`pm3cap.py` — PM3 + CU2, TAGLESS** (a tag's own signal contaminates it). The comparator-free
   raw buffer; nothing in the chain calls a demodulator. Only worth spending a bench move on if (1)
   comes back clean, i.e. the sequence is right and the defect is downstream in the peripheral.
   ⛔ Requires the operator, so it is a queued item, not a tick's work.
3. Bench grading — on the operator's return, never here.

⚠ **FIVE OF THE SIX ARE PSK** (`indala`, `keri`, `nexwatch`, `idteck`, `indala224`); only `gproxii`
is ASK. C471's method — predict the run histogram from the frame's own bits, then match — was built
on PAC, which is NRZ. It transfers to `gproxii` directly and **must be re-derived for PSK**: a phase
flip appears as a single run at 1.5x or 0.5x the subcarrier period, so it is detectable in run
structure, but it is different arithmetic. ⛔ Write the criterion BEFORE the capture (M55), not after.
Deriving it is good hands-off work and is worth a tick of its own.

⇒ Work the emitters on the host: `firmware/application/src/rfid/nfctag/lf/protocols/`, verified by
`ctest/`'s round trip, and queue each fix for bench confirmation on the operator's return. **A host
round trip is not a bench verdict** — say so every time.

### 2b. The two cells that disagree with themselves

`em410x` `pm3·emu` and `fdxb` `cu1·emu` show `⁇` — readings that disagree. Queue `--repeat 10` for
the operator's return; do not reason about them from the disagreement alone.

### 2c. The unmeasured

⛔⛔ **`em410x_electra` — MEASURED 2026-09-16 AND THE ANSWER REFUTES THE GAP REGISTER.** The register
said *"the Proxmark DOES support Electra … and its reader prints the Electra value"*. It was read
from source. **The hardware disagrees:**

| step | result |
|---|---|
| `lf em 410x clone --id 2244668800 --electra` | writes it; prints `Electra 0x7e1eaaaaaaaaaaaa` |
| `lf em 410x reader` | prints **`EM 410x ID 2244668800` and nothing else** |
| `lf em 410x reader -h` | **no Electra flag exists** — clk/invert/amp/break/continuous/verbose only |
| Chameleon `lf em 410x read` | `EM410X/64: 2244668800` — also no Electra distinction |
| Flipper (learned, 20260915_233837) | `22446688007E1EAA` — **it alone distinguishes Electra** |

⛔⛔ **SO DO NOT RECORD `2244668800` AS ELECTRA'S EXPECTATION.** It is byte-identical to plain
`em410x`'s, and a registry holding the same token for both would let an `em410x` emission pass an
`electra` cell and vice versa — a false pass built in by construction. The run's own remedy
("record the token it prints") was written before anyone ran it, and is wrong.

⇒ **On this bench only the Flipper can judge Electra.** That is a gap-register row about the
Proxmark, not a limit of ours: `rd.pm3` cannot distinguish the two protocols at all. Electra's
`rd.pm3` column should be refused by name, permanently, rather than left as "go and measure it".
⚠ `cu_read` is still genuinely absent (`–`), which is ours and is real work.

`indala224` has no `cu1·wr`. **cu2 was measured on 2026-09-16 and its writer TIMES OUT** —
`CMD 3039 INDALA224_WRITE_TO_T55XX`, reproducible in ~4 s with the correct command and arguments
(`lf indala write --raw <56 hex> --224`; the registry row is correct, verified). A firmware command
that hangs rather than returning an error is a bug whatever the tag state. ⭐ **Reproducible over
USB with no bench move — work it.**

⭐ **`fdxb emu.pm3 → rd.cu2` is SILENT** (new, run 20260916_161528) while `t55.pm3 → rd.cu2` is
EXACT. Either the Proxmark's own `lf fdxb sim` is wrong or our reader cannot take an emulated fdxb.
Ambiguous; queued.

### 2d. Codebase tidying — only with the tests green

`./runtests` before and after **every** change. 463 tests at 0.2s means there is no excuse for a
refactor that was not verified. Reduce comments to what is needed; this codebase errs long.

### 2e. Upstream preparation

Branches and PR notes for what has been found. `LF_RESEARCH_CMDS_ENABLED` defaults to 0 and is set
only on our branch — an upstream PR drops that one `-D`. Give thought to how protocol-support PRs
should be split; do not open anything.

---

## 3. Caps and pacing

`sh /Users/Shared/code/personal/utility-scripts/claude/usage_check.sh` prints one line:

    util5=<pct> mins5=<min to reset> util7=<pct> mins7=<min to reset>

⚠ `mins*` is **minutes until that window RESETS**, not minutes used. Verified working 2026-09-16
16:24 (the cookie had been stale since 11 Sep and was rotated by the operator).

**Read it at the START of every tick.** Two stop conditions. **Both are terminal — neither is a
pause, and there is no second phase after either one.**

| stop when | meaning |
|---|---|
| `util7 >= 98` | the week's allowance is spent |
| the clock passes **Sun 2026-09-20 00:00** | the round is over regardless of the figure |

The last 2% is reserved so the routine and its wakeups cannot themselves fail for want of capacity.

⛔⛔ **THE SECOND CONDITION IS NOT BOOKKEEPING — WITHOUT IT THE FIRST ONE RE-ARMS.** The 7-day
window RESETS at exactly Sun 2026-09-20 00:00 (`mins7` counts down to it). A round that stopped on
Thursday at 98% would, on the next tick after that moment, read a healthy `util7` and start again —
spending the capacity the operator is keeping for their return. A cap alone cannot express "and
stay stopped" across a reset, so the clock does.

⇒ On either condition: commit whatever is finished, write the work list forward for a human to pick
up, say in one line which condition stopped it, and stand down. **Do not wait for more capacity and
do not check again.**

⚠ **`util5` can stop you while `util7` is healthy.** The 5-hour window is a separate quota. If
`util5` is near its ceiling, work stalls no matter what the weekly figure says — report it as a
5-hour stall, which passes, never as the weekly cap, which does not.

⛔ **If the script stops answering** (it returns `HTTP 403` once the cookie expires — it had been
stale since 11 Sep before the operator rotated it), the weekly ceiling cannot be measured. **Keep
working and say so once per tick.** The ceiling is the operator's own and they have said that
running out is fine; the thing that actually needs protecting is next week's capacity, and the
**clock condition protects that without the script**. ⛔ Do not invent a substitute figure to pace
against — a number nobody measured is worse than an honest "unmeasured" on every tick.

⭐ **LOG `util7` IN EVERY TICK'S COMMIT OR REPORT.** A cold session cannot remember the last
reading (§6), so the burn rate is only visible if each tick writes it down. At the rate observed on
2026-09-16 the 30 points of headroom is roughly 1.6 days — so the round is expected to reach the
ceiling well before Sunday. **That is the intended outcome, not a fault**: the operator's decision
is that running out is fine and the remainder is theirs for next week.

## 4. Non-negotiables

- Single-threaded. No subagents, no workflows.
- `./runtests` green before every commit here; `./autopilot.sh gate` and `./checkdocs.sh` (no pipe)
  in the ChameleonUltra tree.
- `git commit --no-gpg-sign`, heredoc message, never `--amend`, never `--force`.
- Push only to `origin indala-psk-read` (ChameleonUltra). **Never push to a PR head or a shared
  branch** — the operator's global rule, and they are not reachable to ask.
- Ask the hardware what it runs (M45). Suspect the instrument first.
- ⛔ **Never move the bench, and never claim a cell that needed a move.** The operator is not there
  to move it, and a cue with nobody to hear it is announced and then assumed — `_goto` with
  `interactive=False` does not wait.
- A host test, a dry run and a regrade are each worth saying out loud as what they are. None of
  them is a bench result.

## 5. When the work list is exhausted or blocked

Say so plainly, then hand off to the **T5577 Flipper deep-read** project under
`Momentum-Firmware/T5577_block0_analysis_data/` — it has its own tracking (`README.md`,
`T5577_DATABLOCK_RESULTS.md`, `T5577_DIRECT_READ_CORPUS.md`, the `PREDICTION_*.md` files) but no
offline process. Carry §1, §3 and §4 of this file across unchanged; they are not specific to this
project.

---

## 6. Keeping the round alive, and stopping it

The operator has `claude` running at startup and will drive the cadence with a cron/routine, so
nothing here installs anything.

**Two conventions this round must honour regardless of what fires it:**

⭐ **`STOP` is the kill switch.** If a file named `STOP` exists in this directory, commit what is
finished, say you are standing down, and stop. It is a *file* because the operator is checking in
over VNC — creating one in a file browser must be enough, with no terminal and no remembering a
label.

⭐ **Touch `.loop-heartbeat` as the first action of every tick**, before reading anything. It is the
only external evidence that the round is alive rather than wedged, and it costs nothing.

⚠ **A ROUTINE, NOT A SESSION CRON.** These are not the same thing and only one of them is a
fallback. A cron created inside a session dies with it, so it cannot restart a session that has
ended — the one case worth guarding. A **routine** lives outside any session and launches a new one
on schedule, which closes that hole properly. ⛔ Do not substitute a session cron for it.

⭐ **CONSEQUENCE 1 — every tick may be a COLD session.** A routine starts fresh: no conversation
context, no memory of the last tick, nothing carried but the filesystem and git. ⇒ **This file and
the repo are the only handover.** Anything a tick needs to know must be written down before that
tick ends — a conclusion held only in context is lost at the next launch. Finish every tick with
the work list updated and committed, not with a plan you intend to remember.

⛔ **CONSEQUENCE 2 — TWO ROUNDS CAN NOW RUN AT ONCE.** Ticks inside one session serialise; sessions
launched by a routine do not. If a tick is still working when the next fires, two rounds drive one
bench and commit over each other. **So the heartbeat is a concurrency guard, not just a liveness
signal:**

> **First action of every tick: read `.loop-heartbeat`. If it is NEWER than 25 minutes, another
> round is live — say so in one line and stop. Do not work, do not commit.** Otherwise touch it and
> proceed, and touch it again as each unit of work completes so a long tick does not read as dead.

⚠ That test is deliberately cheap and deliberately conservative: a tick skipped because a sibling
was working costs one interval, and two rounds interleaving commits on one bench costs the day.

