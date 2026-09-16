"""Building and flashing. The same discipline as measuring, pointed at a different problem.

⛔ Flashing has the identical failure shape: the tool returns cheerfully, nothing says whether it
worked, and the only way to know is to ask something that observed the effect.
"""

import json
import os
import tempfile
import time
import unittest

import tests.helpers  # noqa: F401  — sets sys.path
from benchmatrix import dfu, firmware


def write_config(body: str) -> str:
    d = tempfile.mkdtemp()
    p = os.path.join(d, "firmware.toml")
    with open(p, "w") as fh:
        fh.write(body)
    return p


class TheShippedConfigIsUsable(unittest.TestCase):

    def test_it_loads_and_names_a_target(self):
        targets = firmware.load()
        self.assertIn("chameleon-ultra", targets)
        t = targets["chameleon-ultra"]
        self.assertTrue(t.build.get("command"))
        self.assertEqual(t.flash.get("method"), "nrf-dfu")

    def test_the_build_directory_and_artifact_resolve_to_real_places(self):
        t = firmware.load()["chameleon-ultra"]
        self.assertTrue(os.path.isdir(t.build_dir()), t.build_dir())
        self.assertTrue(t.artifact().endswith("ultra-dfu-app.zip"))

    def test_an_env_value_beginning_with_a_bang_is_a_command(self):
        """⭐ How a build gets GNU_VERSION=$(arm-none-eabi-gcc -dumpversion) without a shell —
        pinning a compiler version in a file is how it rots silently."""
        t = firmware.load()["chameleon-ultra"]
        env = firmware.build_env(t)
        self.assertRegex(env["GNU_VERSION"], r"^\d+\.\d+")
        self.assertTrue(env["PATH"].startswith(t.path("../.tools/bin")))

    def test_a_command_that_produces_nothing_is_refused_not_left_empty(self):
        path = write_config('[targets.x]\n[targets.x.build]\ncommand = ["true"]\n'
                            '[targets.x.build.env]\nV = "!true"\n')
        t = firmware.load(path)["x"]
        with self.assertRaises(firmware.FirmwareError) as cm:
            firmware.build_env(t)
        self.assertIn("would be empty", str(cm.exception))

    def test_a_missing_path_entry_is_refused_before_the_build_runs(self):
        """⛔ A build that picks up the wrong toolchain fails in ways that look like source
        problems."""
        path = write_config('[targets.x]\n[targets.x.build]\ncommand = ["true"]\n'
                            'path_prepend = ["../definitely-not-here"]\n')
        with self.assertRaises(firmware.FirmwareError) as cm:
            firmware.build_env(firmware.load(path)["x"])
        self.assertIn("do not exist", str(cm.exception))


class TheArtifactsDecide(unittest.TestCase):
    """⛔⛔ NOT THE EXIT CODE. `build.sh` ends with a step that fails harmlessly AFTER the DFU zips
    are written, and tools that return zero having produced nothing are not rare either."""

    def _target(self, command, artifacts='["out.txt"]'):
        d = tempfile.mkdtemp()
        cfg = os.path.join(d, "firmware.toml")
        with open(cfg, "w") as fh:
            fh.write('[targets.x]\n[targets.x.build]\ncwd = "."\ncommand = %s\nartifacts = %s\n'
                     % (json.dumps(command), artifacts))
        t = firmware.load(cfg)["x"]
        object.__setattr__(t, "build", dict(t.build, cwd=d))
        firmware.ROOT = "/"
        return t, d

    def tearDown(self):
        firmware.ROOT = os.path.normpath(os.path.join(firmware.HERE, ".."))

    def test_a_nonzero_exit_with_fresh_artifacts_is_a_good_build(self):
        t, d = self._target(["sh", "-c", "touch out.txt; exit 3"])
        res = firmware.build(t, out=lambda *a: None)
        self.assertTrue(res.ok)
        self.assertEqual(res.exit_code, 3)
        self.assertIn("fails harmlessly", res.note)

    def test_a_zero_exit_with_nothing_produced_is_not(self):
        t, d = self._target(["true"])
        res = firmware.build(t, out=lambda *a: None)
        self.assertFalse(res.ok)
        self.assertIn("not the evidence", res.note)

    def test_a_stale_artifact_does_not_count_as_a_build(self):
        """⚠ FRESH, NOT MERELY PRESENT."""
        t, d = self._target(["true"])
        with open(os.path.join(d, "out.txt"), "w") as fh:
            fh.write("from an earlier build")
        os.utime(os.path.join(d, "out.txt"), (time.time() - 3600, time.time() - 3600))
        self.assertFalse(firmware.build(t, out=lambda *a: None).ok)


class QuietOutputIsNotSuccess(unittest.TestCase):
    """⛔⛔ Captured non-interactively, nrfutil prints only an unrelated JLink warning — exactly what
    a flash that never happened prints. The JSON records are the evidence."""

    def test_a_success_record_is_required(self):
        self.assertTrue(dfu._succeeded([{"x": 1}, {"result": "success"}]))
        self.assertTrue(dfu._succeeded([{"task": {"result": "Success"}}]))

    def test_no_records_at_all_is_the_race_this_exists_to_catch(self):
        self.assertFalse(dfu._succeeded([]))

    def test_records_without_a_result_are_not_success(self):
        self.assertFalse(dfu._succeeded([{"progress": 50}, {"progress": 100}]))

    def test_a_failure_record_is_not_success(self):
        self.assertFalse(dfu._succeeded([{"result": "error", "message": "no device"}]))


class TheFlasherTargetsOneNamedDevice(unittest.TestCase):

    def test_cu_and_tty_spellings_are_the_same_device(self):
        """⚠ macOS exposes every USB serial device twice and `comports()` reports only the `cu.`
        form, while every note on this bench names the `tty.` form."""
        self.assertTrue(dfu.same_device("/dev/cu.usbmodemABC", "/dev/tty.usbmodemABC"))
        self.assertFalse(dfu.same_device("/dev/cu.usbmodemABC", "/dev/tty.usbmodemXYZ"))

    def test_usb_ids_parse_as_hex(self):
        self.assertEqual(dfu.usb("6868:8686"), (0x6868, 0x8686))

    def test_the_trigger_frame_is_the_documented_one(self):
        self.assertEqual(bytes.fromhex(dfu.DEFAULTS["trigger"]),
                         b"\x11\xef\x03\xf2\x00\x00\x00\x00\x0b\x00")


if __name__ == "__main__":
    unittest.main()
