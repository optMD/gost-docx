import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

MODULE = Path(__file__).resolve().parents[1] / "scripts/atomic_write.js"


class AtomicBuildTests(unittest.TestCase):
    def test_write_and_rename_failures_leave_previous_output_intact(self):
        code = '''
const fs = require("fs");
const { atomicWrite } = require(process.argv[1]);
const operation = process.argv[3];
const original = fs[operation];
fs[operation] = () => { throw new Error("injected failure"); };
try {
  atomicWrite(process.argv[2], Buffer.from("new"));
  process.exitCode = 2;
} catch (error) {
  if (error.message !== "injected failure") throw error;
} finally { fs[operation] = original; }
'''
        for operation in ("writeFileSync", "renameSync"):
            with self.subTest(operation=operation), TemporaryDirectory() as tmp:
                target = Path(tmp) / "output.docx"
                target.write_bytes(b"previous")
                result = subprocess.run(["node", "-e", code, str(MODULE), str(target), operation],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(target.read_bytes(), b"previous")
                self.assertEqual(list(Path(tmp).iterdir()), [target])

    def test_successful_write_cleans_temporary_directory(self):
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "output.docx"
            code = 'require(process.argv[1]).atomicWrite(process.argv[2], Buffer.from("new"));'
            for _ in range(2):
                subprocess.run(["node", "-e", code, str(MODULE), str(target)], check=True)
                self.assertEqual(target.read_bytes(), b"new")
                self.assertEqual(list(Path(tmp).iterdir()), [target])
