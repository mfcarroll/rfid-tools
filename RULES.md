# The rules the harness enforces

Nine rules. Each one exists because ignoring it produced a wrong published result on a real bench,
and each is enforced in code rather than left to the operator's discipline. This file is the
reference: the code refers to these rules by name and does not restate the reasoning.

The last section maps each rule to where it was first paid for, for anyone who needs the trail.

---

## 1. The calibration rule

> **A reader's silence about a source means nothing until that reader has decoded the same protocol
> from a known-good source on the same pad in the same session.**

No calibration row ⇒ no verdict. Not a weaker verdict — the cell reads `UNGRADED` and is not scored.

Enforced by type, not by checking. `grade()` cannot be called without a `Calibration`, and a
`Calibration` cannot be built except by `Calibration.from_row()`, which refuses anything but a
byte-exact read of a **real tag**, for **that protocol**, on **that reader**, in **that session**,
on **that pad**. There is no bypass argument anywhere in the package.

A cell that would read `EXACT` still reads `UNGRADED` without a licence. The exception is tempting
and must not exist: a byte-exact hit proves the reader was listening for that one cell and nothing
else, and the moment it is allowed through, licensed and unlicensed rows are back in one grid with
no way to tell them apart.

**Corollary — no aggregation across protocols.** "Reader A missed X, reader B missed Y, so each is
just a decoder gap" is a fallacy. Every statement the grid makes is scoped to one
(protocol, reader) pair. Tallies are printed and labelled as tallies.

## 2. The subcarrier rule

> **Never judge an emulation with a subcarrier-dependent read arm.**

`indala`, `gallagher`, `securakey`, `noralsy` and `gproxii` need a subcarrier phase-locked to the
reader's carrier, which only a real tag has. `(emu.*, rd.cu)` cells for these are **refused at plan
time**, not measured and recorded as failures — a refusal that happens after the read has been taken
is a deletion, not a refusal.

The set is named explicitly rather than derived from modulation family, because four of the five are
ASK on the coil. Deriving the rule from `family` would silently re-admit them; deriving `family`
from the rule would falsify the modulation record. Both are stored, and the disagreement is visible.

## 3. The A/B/A rule

> **A null sweep before and after every block. A closing sweep that differs from the opening one
> voids the block — it does not degrade it.**

Against anything intermittent, A/B is not an experiment. A difference says the bench changed
underneath the block, and there is no way afterwards to know which reads were taken before it
changed and which after, so none of them stand.

A void block **revokes the licences it issued**, including for rows measured in later blocks. A
licence is a claim that the bench was stable while the control was taken; if that block turns out
not to have been stable, the claim does not survive it.

Two things the sweep must get right:

- **Active emitters stay in the stack**, in reader mode. A null taken with the stack pulled apart
  measures a different bench from the one the arms were measured on.
- **A passive tag has no idle state** and must be physically removed. So the tag is the *last* thing
  to go into a stack and the *first* thing to come out: arrange the station empty, take the sweep,
  add the tag, work, remove the tag, close the sweep. Building the whole station and then asking for
  the tag straight back out is three instructions where one will do, and the middle one contradicts
  the one before it — an operator told to undo what they were just told to do stops trusting the
  cues, and the cues are the only thing keeping the bench and the plan in step.

## 4. The identity rule

> **Every move is followed by a radio-identity check, not a question — and every command to a
> Chameleon proves, on the way, that it reached the device it was addressed to.**

The operator's word is the plan; the radio is the record. Each Chameleon is armed with a
device-unique EM410X id and the reader is asked who is actually there.

This is the one check the null sweeps cannot do for you: a null sweep catches a **stray** emitter,
never a **swapped** one, because the wrong device is exactly as silent as the right one in reader
mode. A wrong-device run produces an unfalsifiable null — every arm scored against something that
was never listening.

The probe carries its own protocol key. It borrows the EM410X read command because that is the one
arm every reader decodes from a Chameleon, but a probe read must never be filed as an `em410x`
result, nor an `em410x` script intercept a probe.

**Two layers, because the radio check rests on the other one.** It arms `cu1` and asks who is
there — but `cu1` means whatever port the command went to, so crossed ports make it confirm the lie.
So every Chameleon command is issued together with `hw chipid` and its answer checked before the
reply is used. A cable moved mid-session is caught at the exact action it would have corrupted, and
a port that no longer holds the expected device is simply re-resolved: the label is bound to the
silicon, never to the cable.

**Only a physical instruction is spoken.** A sweep or an identity check asks the operator for
nothing, so it chimes and says nothing. Narrating the harness's own housekeeping trains the operator
to ignore the voice, which is exactly the channel a move cue depends on.

**And a run that stops early still leaves the bench idle.** Every exit — a fault, a refused
calibration, Ctrl-C — puts each device back into reader mode before returning. A device left
emulating contaminates whatever runs next, and the operator cannot see it: the only symptom is a
null sweep failing at the start of the following session for no visible reason.

## 5. The liveness rule

> **Prove the instrument answered before measuring anything with it.**

A silent reader and a silent emitter produce identical numbers. Every channel is checked before the
run and aborts it on failure.

Proof of life is two-sided on purpose. A blocklist of known failure strings is checked first because
it names the cause — but the absence of a known failure is **not** success, so a positive proof the
device answered is then required. Every marker in that blocklist was added after a failure got
through it; enumerating the ways a device can fail to answer is a losing game, and requiring
evidence that it did answer is not.

## 6. The name-match rule

> **Match an anchored decode line, never a protocol name.**

A protocol's name appears in usage banners and in "available protocols" listings, so counting
substring hits of it can report more successes than there were attempts. Matching is against the
anchored `<name> <HEX>` success line and nothing else, and the name may contain a space.

## 7. The crowded-stack rule

> **A stack with more devices in it than the operation needs can confirm a success. It can never
> confirm a failure.**

Devices left in the field detune and load the active coil even when idle. A byte-exact decode of the
armed credential cannot be manufactured by a parasitic coil, so a success in a crowded stack is a
success. A silence or a wrong decode might be the crowding.

So a non-`EXACT` result in a crowded stack is **not a verdict**. It is a screening result that
queues an isolated re-measurement, and only that re-measurement can produce `SILENT` or `WRONG`.

**One energised device per stack at a time.** The concern is passive detuning, not competing
carriers, so co-located devices are fine as long as the harness sequences them.

## 8. The self-licensing rule

> **An expectation learned in a session cannot license a control in that same session.**

Where a reader's expected output is unknown, it can be learned from a real tag written by the
Proxmark. But if the expectation is learned from the same read that is supposed to license the
reader, the calibration row cannot fail — it is being compared against itself. That is not a weaker
control, it is a control quietly inverted into a tautology, and it would be invisible in the grid:
every licence green, every licence worthless.

## 9. The write-state rule

> **A read of a tag is attributed to whoever last wrote it — and a write must say for itself that
> it happened.**

There are three writers — Proxmark, Chameleon, Flipper — and a T5577 holds one credential at a time.
The source of a tag read is not a property of the tag, it is a property of the last write. Modelling
the write as a detail of the read would read whatever the tag still held from the previous step and
file it under the current protocol: a wrong cell with a plausible-looking cause, which is the worst
kind.

A refused write is the same failure wearing a different hat. If a `clone` command is rejected, the
tag keeps its previous credential, the read that follows decodes nothing, and the run reports *"this
reader cannot judge this protocol"* — a bench verdict for a one-line registry error. So a write is
confirmed by **evidence that it happened**, never by the absence of an error, and a write that
cannot confirm itself skips the reads that depended on it rather than letting them be scored.

---

## Where each rule was paid for

These reference the ChameleonUltra `indala-psk-read` project's own claim and method numbering. They
are provenance only — nothing in this repository depends on them, and the rules above stand on their
own.

| Rule | First paid for |
|---|---|
| 1. calibration | C378/C431, C473 (retracted by C474), C465 |
| 2. subcarrier | M52 |
| 3. A/B/A | M35, C328 |
| 4. identity | C461, C472 |
| 5. liveness | C373/C374, C377, C466, D61 |
| 6. name-match | M28 |
| 7. crowded stack | operator bench practice |
| 8. self-licensing | found while building this harness |
| 9. write-state | found while building this harness |
