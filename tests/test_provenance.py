"""What was running when a cell was measured.

⛔ A CELL IS A CLAIM ABOUT A FIRMWARE, NOT ABOUT A DEVICE IN GENERAL. The two Chameleons on this
bench run different builds on purpose — that is half of why there are two — so "the Chameleon decodes
Keri" means nothing until it says which one and which build. A grid that cannot answer that cannot be
cited later, which is the only thing a grid is for.
"""

import unittest

from tests.helpers import answers_all_exact, make_devices, quiet, reg, runner, tiny_plan
from benchmatrix import grid
from benchmatrix.devices import Chameleon, Flipper, Pm3, _cu_version, _pm3_version

PM3_OUT = """
[=] Session log ...
[+] Communicating with PM3 over USB-CDC
    Client.... Iceman/master/v4.20469-1234-g0badc0de
    Bootrom... Iceman/master/v4.20469
    OS........ Iceman/master/v4.20469-1234-g0badc0de
[=] Max frame size: 512 bytes
"""
CU_OUT = " - Chameleon Ultra, Version: v2.2 (v2.2.0-875-g02fc2e2)"


class ParsingWhatTheDevicesSay(unittest.TestCase):

    def test_the_proxmark_reports_firmware_and_client(self):
        """⚠ BOTH, not just the firmware. A mismatched client fails every command while looking
        cheerful, and that pairing has cost a bench session before now."""
        got = _pm3_version(PM3_OUT)
        self.assertIn("os Iceman/master/v4.20469-1234-g0badc0de", got)
        self.assertIn("client Iceman/master/v4.20469-1234-g0badc0de", got)

    def test_the_chameleon_reports_its_build(self):
        self.assertEqual(_cu_version(CU_OUT), "Chameleon Ultra v2.2 (v2.2.0-875-g02fc2e2)")

    def test_an_unparseable_reply_says_so_rather_than_inventing_one(self):
        self.assertIn("not reported", _pm3_version("[!] nothing useful here"))
        self.assertIn("not reported", _cu_version("[!] nothing useful here"))

    def test_the_versions_come_from_the_proof_of_life_already_being_run(self):
        """No extra round trip: `alive()` already runs `hw version` on both channels."""
        pm3 = Pm3()
        pm3.exec = lambda *c, **k: PM3_OUT
        ok, why = pm3.alive()
        self.assertTrue(ok)
        self.assertIn("v4.20469", pm3.reported)
        self.assertIn("v4.20469", why, "the operator sees it at proof of life too")

        cham = Chameleon(port="/dev/a", name="cu2")
        cham.exec = lambda *c, **k: CU_OUT
        ok, why = cham.alive()
        self.assertTrue(ok)
        self.assertIn("v2.2.0-875", cham.reported)

    def test_the_flipper_channel_admits_it_does_not_know(self):
        """⚠ `flipper.py` exposes no version query and this harness does not reach past it to the
        serial port — two readers on one /dev/cu.* is how a session's replies get eaten. Unknown is
        recorded as unknown."""
        self.assertIn("not reported", Flipper().reported)


class AGridSaysWhatProducedIt(unittest.TestCase):

    def _run(self):
        protos = reg.resolve(["em410x"])
        plan = tiny_plan(keys=("em410x",), sources=("t55.pm3",), readers=("rd.pm3",))
        res = runner.run(plan, make_devices(answers=answers_all_exact(protos)), interactive=False,
                         session="S", out=quiet)
        return res, protos

    def test_every_device_in_the_run_is_recorded(self):
        res, _ = self._run()
        self.assertEqual(set(res.firmware), {"pm3", "flipper", "cu1", "cu2"})
        self.assertTrue(all(res.firmware.values()))

    def test_the_harness_records_its_own_commit(self):
        """Which version of these rules produced the grid."""
        res, _ = self._run()
        self.assertTrue(res.harness)

    def test_the_markdown_publishes_it(self):
        res, protos = self._run()
        md = grid.render(res, protos)
        self.assertIn("what was running", md)
        self.assertIn("rfid-tools", md)
        for dev in res.firmware:
            self.assertIn("`%s`" % dev, md)

    def test_the_json_publishes_it(self):
        res, protos = self._run()
        blob = grid.to_json(res, protos)
        self.assertIn('"firmware"', blob)
        self.assertIn('"harness"', blob)

    def test_a_device_that_did_not_report_is_flagged_in_the_table(self):
        res, protos = self._run()
        res.firmware["flipper"] = "firmware not reported by this channel"
        self.assertIn("⚠", grid.render(res, protos))


if __name__ == "__main__":
    unittest.main()
