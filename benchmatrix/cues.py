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

import os
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


#: ⛔ WHAT THE PRINTED TEXT SAYS AND WHAT THE VOICE SHOULD SAY ARE NOT THE SAME STRING. `say` reads
#: "T5577" as "T five thousand five hundred seventy seven" — wrong, and long enough that the
#: operator has stopped listening before the instruction arrives. A part number is precise on screen
#: and noise in the ear, so the voice gets the plain word.
#:
#: ⚠ APPLIED HERE RATHER THAN AT THE CALL SITES, because a cue's wording is assembled in several
#: places: the move planner has a spoken vocabulary of its own, but the null-sweep repositioning
#: prompts build their text from the printed names. One rewrite at the point of speaking covers all
#: of them, whatever a caller does.
_SAY_SUBS = (
    (r"([0-9.]+)\s*mm\b", r"\1 millimetres"),
    (r"\bT5577\s+tag\b", "tag"),        # "the T5577 tag" -> "the tag", not "the tag tag"
    (r"\bT5577\b", "tag"),
    (r"\bT55\b", "tag"),
    (r"\bpm3\b", "P M 3"),
    (r"\bOEM\b", "O E M"),
    (r"\bcu1\b", "Chameleon one"),
    (r"\bcu2\b", "Chameleon two"),
)


def _spoken(s: str) -> str:
    """Rewrite a printed cue into something a voice can read aloud."""
    for pattern, repl in _SAY_SUBS:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    return s


def _play(sound: str) -> None:
    if not SOUND:
        return
    sys.stdout.write("\a")
    sys.stdout.flush()
    try:
        subprocess.Popen(["afplay", "/System/Library/Sounds/%s.aiff" % sound],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


#: The `say` process currently talking, if any. See `_say`.
_TALKING = None


def _say(words: str, block: bool = False) -> None:
    """Speak, and make sure nothing else is speaking at the same time.

    ⛔⛔ ONE VOICE AT A TIME, ALWAYS. Two `say` processes started within a few hundred milliseconds
    of each other talk over one another and the operator hears neither clearly — which is worse than
    silence, because it sounds like a working cue. `cue_done` blocks for exactly this reason, and
    that was not enough: a prompt that plays an attention cue AND then speaks its question issues two
    utterances that overlap, and what the operator hears is a garbled first half and a clean second.
    Device-observed during `bench setup`.

    ⇒ Rather than leave it to every caller to sequence its own audio, anything already talking is
    stopped here. The newest utterance is always the operative instruction — if something else was
    still speaking, it has been superseded.
    """
    global _TALKING
    if _TALKING is not None and _TALKING.poll() is None:
        try:
            _TALKING.terminate()
        except Exception:
            pass
    _TALKING = None
    if not (SPEAK and words):
        return
    argv = ["say", "-r", str(RATE), _spoken(words)]
    try:
        if block:
            subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=25)
        else:
            _TALKING = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def cue_move(words: str) -> None:
    _play(SND_MOVE)
    _say(words)


def cue_check(label: str = "") -> None:
    """A chime, and no speech.

    ⛔ ONLY A PHYSICAL INSTRUCTION IS SPOKEN. A null sweep and an identity check ask the operator for
    nothing — they are the harness working — so saying "null before" out loud is noise that trains
    the operator to ignore the voice, which is precisely the channel a move cue depends on. The
    chime stays: it marks the boundary between the automated stretch and the next thing that will
    need hands. `label` is for the caller's own logging and is not read aloud.
    """
    _play(SND_CHECK)


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


try:
    import termios
except ImportError:                                        # pragma: no cover - not POSIX
    termios = None


def _sane() -> None:
    """Put the terminal into a state `input()` can work in. SETS the flags; does not restore a copy.

    ⛔⛔ THE SYMPTOM IS AN OPERATOR WHO CANNOT ANSWER A PROMPT. Enter arrives as a literal `^M`, the
    line never terminates, and the only way out of a run is Ctrl-C — which aborts it. Twice observed
    at the first station of a real run.

    ⛔ AND THE CAUSE IS NOT REACHABLE FROM HERE. `stdin=DEVNULL` on every child was not enough: a
    readline- or prompt_toolkit-based client opens `/dev/tty` DIRECTLY, so it gets the controlling
    terminal whatever we do with its stdin. The Proxmark client and the Chameleon CLI are both in
    that family.

    ⇒ So this does not try to prevent the damage, and it does not restore a snapshot either — a
    snapshot is only as good as the moment it was taken, and restoring one that was itself wrong
    fails silently and identically. It asserts the three flags a line-oriented prompt actually
    needs: CR translated to newline on input, canonical line buffering, and echo. Anything else a
    child changed is left alone.
    """
    if termios is None:
        return
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
        attrs = termios.tcgetattr(fd)
        attrs[0] |= termios.ICRNL                     # iflag: Enter becomes a newline
        attrs[1] |= termios.OPOST | termios.ONLCR     # oflag: newline returns to column 0
        attrs[3] |= termios.ICANON | termios.ECHO | termios.ECHOE | termios.ISIG
        attrs[6][termios.VMIN] = 1
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except Exception:                                      # noqa: BLE001 - never block a prompt
        pass


def is_canonical() -> bool:
    """Could a prompt be answered right now? Used to report the fault rather than hang on it."""
    if termios is None:
        return True
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return True
        attrs = termios.tcgetattr(fd)
        return bool(attrs[3] & termios.ICANON) and bool(attrs[0] & termios.ICRNL)
    except Exception:                                      # noqa: BLE001
        return True


def _prompt_ready() -> None:
    """Fix the terminal, and if it cannot be fixed, SAY SO rather than hanging on it.

    ⚠ A PROMPT THAT CANNOT BE ANSWERED LOOKS EXACTLY LIKE A PROMPT NOBODY HAS ANSWERED YET. The
    operator presses Enter, sees `^M`, presses it again, and eventually kills a healthy run. One
    line of diagnosis is the difference between that and `stty sane` in another window.
    """
    _sane()
    if not is_canonical():
        sys.stdout.write(
            "\n     ⛔ THIS TERMINAL IS NOT IN LINE MODE, so Enter will arrive as ^M and this\n"
            "        prompt cannot be answered. A client left it that way and the repair did not\n"
            "        take. Run `stty sane` in another window, or re-run with --no-prompt.\n")
        sys.stdout.flush()


def ask(prompt: str, spoken: str = "", sound: str = SND_MOVE) -> None:
    """Blocking confirmation with a cue. Returns when the operator presses Enter."""
    _play(sound)
    _say(spoken or prompt)
    _prompt_ready()
    try:
        input(prompt)
    except EOFError:
        pass


def ask_choice(prompt: str, choices: str, default: str, spoken: str = "",
               sound: str = "") -> str:
    """Single-letter choice; `default` on empty or EOF.

    ⚠ TAKES ITS OWN SOUND, so a caller that wants a chime and a question does not have to issue
    them as two calls — which is how the two utterances came to overlap.
    """
    if sound:
        _play(sound)
    _say(spoken or prompt)
    _prompt_ready()
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


def hush() -> None:
    """Stop any in-flight speech. Called when a run ends early — a cue that is still describing a
    bench move the operator has just abandoned is worse than silence."""
    global _TALKING
    if _TALKING is not None and _TALKING.poll() is None:
        try:
            _TALKING.terminate()
        except Exception:
            pass
    _TALKING = None


def silence() -> None:
    """Used by --quiet and by the tests, which must not make noise in CI."""
    global SOUND, SPEAK
    SOUND = SPEAK = False
