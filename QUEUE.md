# Work queue — newest decisions at the top of each item

⭐ **A COLD SESSION STARTS HERE, AFTER `AUTOPILOT.md`.** Keep it current: you are the only thing
that carries between ticks (`AUTOPILOT.md` §6). Tick off what you finish, add what you find, and
**commit it before you exit** — an uncommitted queue is a lost one.

## 1. `seqdump.py` arms 1 of 5 steps and has therefore never worked ⭐ START HERE

`research/indala-psk-read/seqdump.py` runs only the `econfig`. A slot emits only when **all five**
are done, in order (`benchmatrix/devices.py:589`):

    hw slot type -s <slot> -t <TYPE>
    hw slot enable -s <slot> --lf
    <the econfig>
    hw slot change -s <slot>
    hw mode -e            (then settle ~1s)

Every `⛔ VOID — no reader field reached the device` it has ever printed is this, not the field.
⇒ Fix it, then extend its `arms` table beyond `pac`/`gprox` to the six. It needs a reader field
present while it reads: `pm3 -c "lf tune -n 90 --value"` backgrounded works (21 V sustained).
⛔ Disarm in a `finally`.

## 2. `indala224` write hangs — `CMD 3039`

`lf indala write --raw 80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5 --224` →
`TimeoutError: CMD 3039 exec timeout` in ~4 s, reproducible. The registry row is **correct**
(verified). `cmd_processor_indala224_write_to_t55xx` returns no response. ⭐ Pure USB, no bench.
⚠ Rig B has no tag, so the write has nothing to write to — a handler that hangs instead of
reporting "no tag" is still a bug, but keep that confound in the write-up.

## 3. The six emitter gaps — the headline

`indala` · `keri` · `nexwatch` · `idteck` · `gproxii` · `indala224` emit nothing `rd.pm3` can
decode, on **both** Chameleons across **two** builds, licensed both times ⇒ it is the emitter code.
Five are PSK, `gproxii` is ASK. Diagnose per `AUTOPILOT.md` §2a: seqdump first, then the air check
on the tagless Rig B. A fix that turns one EXACT is real — and **ungraded**; say so every time.

## 4. Rig A's tag contents are unknown

Read them before assuming anything, write down what you find. Chameleon 1 writes T5577s and has raw
`lf t55xx` block access, so Rig A is self-sufficient for the successor project. ⛔ Never flash cu1.

## 5. Queued, needs the operator

- `fdxb` `emu.pm3 → rd.cu2` SILENT while `t55.pm3 → rd.cu2` is EXACT — pm3's own `lf fdxb sim`
  or our reader. Ambiguous (run 20260916_161528).
- `em410x` `pm3·emu` and `fdxb` `cu1·emu` read `⁇` — need `--repeat 10`.
- `t55.pm3 → rd.cu2` for everything: gone while Rig B is tagless.

## 6. Registry work, no bench

- `em410x_electra`: refuse the `rd.pm3` column **permanently** — the Proxmark cannot tell Electra
  from plain em410x and has no flag for it (measured 2026-09-16). Do **not** record `2244668800`
  as its expectation. Our `cu_read` is genuinely missing and is real work.
- `indala224` `cu_decode_marker` is `Indala224 PSK1`; `lf indala write --help` says `--224`
  configures **PSK2**. One of them is wrong — check before trusting either.

## 7. When 1–6 are done or blocked

Tidy the codebase behind the 467 tests, then upstream prep (`AUTOPILOT.md` §2d/§2e). Then hand off
to the T5577 project (§5).
