"""The registry, re-checked against device output this bench actually recorded.

⛔⛔ THE LIVE MARKER CHECK HAS A BLIND SPOT AND IT IS NOT FIXABLE IN PLACE. `_check_marker` catches a
bad decode marker only on a BYTE-EXACT read — that is the only moment a marker's failure to fire is
provably the marker's fault. So a protocol whose EXPECTATION is also wrong never produces the read
that would expose the marker, and the two faults conceal each other for as long as both exist.

⭐ THAT IS NOT A COINCIDENCE, WHICH IS WHY IT NEEDS ITS OWN GUARD. A marker and an expectation
written from the source tree instead of from the device are ONE mistake, not two, so they arrive
together — exactly when the live check is blind. `fdxb` carried both from the day it was registered:
`FDX-B / ISO 11784/5 Animal Tag ID Found` is a string the client never prints, and `expect` was the
T5577 BLOCK IMAGE rather than the decoded credential the Proxmark renders. Every pm3 fdxb read came
back SILENT whatever it decoded, and a run concluded from that silence that a write had not landed
while the operator was reading the same tag by hand.

⇒ So this test does not ask the registry about itself. It replays what the devices said — the
evidence already published in `runs/*.json` — against whatever the registry says TODAY. A capture is
a fact and does not rot; an edit that breaks a marker or an expectation now has to get past every
reading that has ever been taken, not just the next one.
"""

import glob
import json
import os
import re
import unittest

from tests.helpers import reg                                        # noqa: F401
from benchmatrix import registry

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(os.path.dirname(HERE), "runs")
FIXTURE = os.path.join(HERE, "captures", "bench_reads.json")


def captures():
    """Every byte-exact reading available, with the text the device actually produced.

    ⛔ THE CHECKED-IN FIXTURE IS THE POINT, NOT `runs/`. Run records are gitignored — they are the
    operator's local artefacts — so a guard reading only them protects exactly one machine and
    silently protects nothing anywhere else. `tests/captures/bench_reads.json` carries the same
    captures into the repository, so the registry is held to them on any clone.

    ⚠ ONLY `EXACT` CELLS. A SILENT one legitimately has no marker in it, and a run's own grading is
    not re-litigated here — what is replayed is the raw text, against today's patterns.
    """
    with open(FIXTURE) as fh:
        for c in json.load(fh)["captures"]:
            yield c["run"], c
    # ⭐ AND ANY LOCAL RUN TOO, so a fresh capture is held to the registry before anyone thinks to
    # copy it into the fixture.
    for path in sorted(glob.glob(os.path.join(RUNS, "run_*.json"))):
        with open(path) as fh:
            run = json.load(fh)
        if run.get("provenance") != "bench":
            continue                                    # a dry run answered from a dictionary
        for c in run.get("cells", []):
            if c.get("outcome") == "EXACT" and c.get("evidence"):
                yield os.path.basename(path), c


class EveryRecordedReadStillAgreesWithTheRegistry(unittest.TestCase):

    def test_there_are_captures_to_check(self):
        """⚠ A GUARD THAT SILENTLY CHECKS NOTHING IS WORSE THAN NO GUARD, because it reads as
        coverage. This fails rather than skips: the fixture is checked in, so an empty one is a
        deleted fixture and not an unused bench."""
        self.assertGreaterEqual(len(list(captures())), 16, "the gold column alone publishes 16")

    def test_the_decode_marker_fires_on_what_the_device_said(self):
        """⛔ THE fdxb FAULT, CAUGHT FROM THE ARCHIVE. A marker that never matches reports a wrong
        decode as SILENT, which is the merge the four outcomes exist to forbid."""
        for run, c in captures():
            p = registry.ALL[c["protocol"]]
            marker = p.marker_for(c["reader"])
            with self.subTest(run=run, protocol=c["protocol"], reader=c["reader"]):
                self.assertIsNotNone(marker, "no decode marker registered")
                self.assertRegex(c["evidence"], re.compile(marker, re.IGNORECASE | re.MULTILINE),
                                 "the registered marker does not match what the device printed")

    def test_the_expectation_appears_in_what_the_device_said(self):
        """⛔ AND THE OTHER HALF. `expect_for` is a substring test, so an expectation the device
        never prints can never match — which is how a block image came to be compared against a
        decoded credential."""
        for run, c in captures():
            p = registry.ALL[c["protocol"]]
            want = p.expect_for(c["reader"])
            with self.subTest(run=run, protocol=c["protocol"], reader=c["reader"]):
                self.assertTrue(want, "no expectation registered")
                self.assertIn(want.lower(), c["evidence"].lower(),
                              "the registered expectation is not in what the device printed")


if __name__ == "__main__":
    unittest.main()
