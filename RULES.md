# The rules the harness enforces

Eleven rules. Each one exists because ignoring it produced a wrong published result on a real bench,
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

## 10. The verification rule

> **An action is not done because it returned. It is done when something has observed its effect.**

A T5577 does not acknowledge a write. `Done!` from the Proxmark client means the commands went out
on the air and nothing more — the tag may be holding the new credential, or the one from the
previous step, and the reply cannot tell you which. The same is true of the Chameleon's writer and
the Flipper's.

So the reads that follow a write are settled **together**, once the tag's state has been read by
everything that is going to read it:

- **If no reader read it back**, the tag is not known to hold what was written, and none of those
  reads may be attributed to their readers. A silence there is as likely to be a write that never
  landed as a decoder that cannot see it, and reporting it as "this reader cannot judge this
  protocol" would be a bench verdict for what may be a one-line registry error.
- **A decode that does not match still settles it**, provided the tag was in a state known to differ
  from what was written — cleared, or holding a different protocol. A reader asked for P cannot
  decode a credential that is not there, so the write landed and what came back is a genuine
  `WRONG`. Without this, a registry whose write command and expectation disagree reports an
  ambiguity on a single-reader station instead of naming itself; with it, each tag block opens by
  clearing the tag so the very first write is covered too.
- **If any one reader read it back byte-exact**, that settles it for all of them. A credential we
  chose cannot be conjured out of a tag that does not hold it, so one witness proves the write
  landed — and every *other* reader's silence on the same tag turns from an ambiguity into a genuine
  finding about that reader. Two readers at a station are worth considerably more than twice one.

Every write is therefore followed by a read-back from the writer itself wherever the writer can
read, even when no cell in the plan asks for one. It costs one command at a station that is already
set up, and without it a tag carried to a single deaf reader is unfalsifiable.

**Verification belongs to the tag, not to the station.** A credential is written at one station and
often read at the next — that is the whole point of carrying a tag. Scoping it to a block would make
every carried tag look like a write that never landed.

**You cannot verify a write that writes what is already there.** Every writer in the registry puts
the *same* credential on the tag for a given protocol, so once the Proxmark has written it, a
byte-exact read after the Chameleon's write is exactly what a write that did nothing would leave
behind — the `t55.cu*` and `t55.flip` columns would measure the Proxmark's work and credit it to the
device under test.

So before a writer **under test** writes protocol P, the tag is cleared, and the clearing is itself
confirmed. A read of P afterwards can then only have come from the writer under test. The gold writer
needs no clearing: the tag already holds a different protocol, and what a gold row claims is only
that the tag *carries* the credential, not who put it there.

**Clearing is a wipe where the Proxmark is in the stack**, which does two jobs at once. It leaves the
tag holding no credential at all — a stronger discriminator than holding a different one — and it
restores the default config block, which some writers need. The Flipper will refuse to write a T5577
left in certain configurations, and without a wipe *"cannot write this protocol"* and *"cannot write
this tag"* are the same reading. Where there is no Proxmark in the stack, the writer parks the tag on
a credential of its own instead: sound, since the tag demonstrably changed and only that device
touched it, but it neither restores the config nor isolates the question to P.

⭐ **The wipe is confirmed by `lf t55xx detect`, not by silence and not by its own reply.** The wipe
prints the blocks it sent — what was transmitted, not what the tag now holds. And a silent protocol
decoder afterwards would be weak evidence: a wiped tag, a tag that is not on the pad and a field that
is off all look the same. `detect` answers *positively* — a chip replied, and what it is putting on
the air is the default configuration block.

⚠ **`detect` is not a block read**, and nothing added later should treat it as one. It works the
modulation and bit rate out from the tag's signal, and the block 0 it reports is *interpreted from
that signal* rather than fetched from block 0. The Proxmark needs it because it cannot decode an
addressed block read — block 0 included — without first knowing the signalling. For confirming a wipe
it is exactly the right instrument, because what matters is the configuration the tag is actually
transmitting.

A clearing that cannot be confirmed blocks the write it was meant to protect, and those reads go
UNGRADED saying so rather than being scored against a tag whose state was guessed at.

⛔⛔ **A write can be proved to have landed. It cannot be proved NOT to have landed.** A byte-exact
read is positive evidence; silence is the absence of evidence, and it is the absence of evidence
however many readers produce it. "None of them decoded it, so the credential is not on the tag" is a
verdict drawn from collective ignorance — every reader present may simply be unable to decode that
protocol, and adding more of them changes nothing unless one of them speaks.

Silence becomes attributable only when **a reader present has been shown to decode that protocol**,
from any source. Then its silence is about the tag. Until then the useful next step is not another
reader but another **writer**: the same protocol from a different hand, which if decoded licenses
that reader and settles the first question too. The harness tracks what each reader has been shown
to decode and names the alternative sources by command.

⭐ **And the backing may arrive after the silence.** A reader that says nothing about a protocol at
step three is uninterpretable there; if the same reader decodes that protocol at step forty, the
step-three silence becomes a statement about that tag. The reading never changes — the
interpretation does, as the corpus grows. So the run revisits its own silences once every station
is in, and says how many it was able to license retrospectively.

⚠ The same holds across runs, and is deliberately not built yet. A reader shown to decode a protocol
last week can license a silence recorded today — but only while it is running the same firmware,
because a cell is a claim about a firmware and not about a device (§11). A persisted corpus has to
be keyed on that, and a half-built one that forgets it would license silences with evidence from a
build that no longer exists.

⚠ **With only one reader, a failed read-back is ambiguous and is reported as ambiguous.** The
harness does not pick between "the write did not land" and "this reader is deaf"; it says a second
reader on the same tag would separate them, and leaves the cell UNGRADED.

## 11. The provenance rule

> **A cell is a claim about a firmware, not about a device in general.**

The two Chameleons on this bench run different builds on purpose — that is half of why there are
two — so *"the Chameleon decodes Keri"* means nothing until it says which one and which build. Every
run records what each device reported at proof of life, and publishes it with the grid:

| device | firmware |
|---|---|
| `cu1` | Chameleon Ultra v2.2 (v2.2.0-861-g1866718) |
| `cu2` | Chameleon Ultra v2.2 (v2.2.0-875-g02fc2e2) |
| `pm3` | os Iceman/master/v4.x, client Iceman/master/v4.x |
| `rfid-tools` | the commit these rules came from |

⚠ **The client version is recorded as well as the firmware.** A mismatched Proxmark client fails
every command while looking cheerful, and that pairing has cost a bench session before now.

⚠ **A device that does not report is recorded as not reporting**, flagged in the table rather than
left blank. The Flipper channel is one: `flipper.py` exposes no version query, and reaching past it
to the serial port would put two readers on one `/dev/cu.*`, which is how a session's replies get
eaten.

It costs nothing — proof of life already runs `hw version` on every channel — and without it a grid
cannot be cited later, which is the only thing a grid is for.

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
| 10. verification | operator, after the first bench run |
| 11. provenance | operator, after the first bench run |
