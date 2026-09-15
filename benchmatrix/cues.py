"""Spoken operator cues — `t5577_campaign.py`'s `_cue` / `cue_done` with a bench-move vocabulary.

⭐ WHAT CHANGED FROM THE ORIGINAL. `_cue` in the campaign script sniffs the prompt TEXT for markers
(`[PM3]`, `lift & replace`, `position '...'`) and reverse-engineers what to say. That worked because
there were three kinds of prompt. Here the move is already a structured object, so the cue is
generated from `Move.spoken()` and nothing has to be parsed back out of a string.

⚠ KEPT VERBATIM, BECAUSE EACH WAS PAID FOR:
  • `_spoken()` expands units so `say` pronounces "3mm" as words.
  • `cue_done` BLOCKS on `say`. With Popen the summary and the next prompt talk over each other and
    the operator hears neither.
  • Three end-of-run sounds, because "it stopped" is not the useful part — whether the operator is
    needed back at the bench is.
  • A fault is AUDIBLE and sounds different (Basso). Before that, the one event that silently ruins
    a capture was the only one with no sound, and the operator missed two consecutive timeouts.
"""

from __future__ import annotations

import re
import subprocess
import sys

SOUND = True
SPEAK = True
RATE = 220

#: macOS system sounds, by role.
SND_MOVE = "Glass"       # a bench rearrangement
SND_CHECK = "Tink"       # an identity check or a null sweep starting
SND_FAULT = "Basso"      # something that voids what follows — STOP
SND_DONE_OK = "Hero"
SND_DONE_PART = "Sosumi"
SND_DONE_FAIL = "Basso"


def _spoken(s: str) -> str:
    """Expand units so `say` reads them as words rather than letters."""
    s = re.sub(r"([0-9.]+)\s*mm\b", r"\1 millimetres", s)
    s = re.sub(r"\bpm3\b", "P M 3", s, flags=re.IGNORECASE)
    return s


def _play(sound: str) -> None:
    if not SOUND:
        return
    sys.stdout.write("\a")
    sys.stdout.flush()
    try:
        subprocess.Popen(["afplay", "/System/Library/Sounds/%s.aiff" % sound],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _say(words: str, block: bool = False) -> None:
    if not (SPEAK and words):
        return
    argv = ["say", "-r", str(RATE), _spoken(words)]
    try:
        if block:
            subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        else:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def cue_move(words: str) -> None:
    _play(SND_MOVE)
    _say(words)


def cue_check(words: str) -> None:
    _play(SND_CHECK)
    _say(words)


def cue_fault(words: str) -> None:
    """⚠ DOUBLE BELL AND A DIFFERENT VOICE. This one means STOP, not 'move the tag'."""
    if SOUND:
        sys.stdout.write("\a\a")
        sys.stdout.flush()
    _play(SND_FAULT)
    _say(words, block=True)


def cue_done(words: str, ok: bool = True, partial: bool = False) -> None:
    """End-of-run announcement. BLOCKING, so it does not talk over anything that follows.

    ⚠ A 20-CELL MATRIX IS EXACTLY WHEN THE OPERATOR HAS WALKED AWAY, and silence at the end is
    indistinguishable from the run still going — which is how a healthy run gets killed by hand for
    looking like a hang.
    """
    _play(SND_DONE_FAIL if not ok else (SND_DONE_PART if partial else SND_DONE_OK))
    _say(words, block=True)


def ask(prompt: str, spoken: str = "", sound: str = SND_MOVE) -> None:
    """Blocking confirmation with a cue. Returns when the operator presses Enter."""
    _play(sound)
    _say(spoken or prompt)
    try:
        input(prompt)
    except EOFError:
        pass


def ask_choice(prompt: str, choices: str, default: str, spoken: str = "") -> str:
    """Single-letter choice; `default` on empty or EOF."""
    _say(spoken or prompt)
    while True:
        try:
            r = input(prompt).strip().lower()
        except EOFError:
            return default
        if not r:
            return default
        if r[0] in choices:
            return r[0]
        print("  (enter one of: %s)" % ", ".join(choices))


def silence() -> None:
    """Used by --quiet and by the tests, which must not make noise in CI."""
    global SOUND, SPEAK
    SOUND = SPEAK = False
