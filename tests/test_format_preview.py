import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/gost_docx.py"


class FormatPreviewTests(unittest.TestCase):
    def test_preview_matches_real_changes_without_writing(self):
        with TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "source.docx", Path(tmp) / "formatted.docx"
            subprocess.run([sys.executable, str(CLI), "build", str(ROOT / "tests/fixtures/minimal_report.json"),
                            str(source)], check=True, capture_output=True)
            original = source.read_bytes()
            target.write_bytes(b"keep existing result")
            command = [sys.executable, str(CLI), "format", str(source), "--out", str(target)]
            preview = subprocess.run([*command, "--dry-run"], capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn("Файл не записан", preview.stdout)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(target.read_bytes(), b"keep existing result")
            self.assertEqual(set(Path(tmp).iterdir()), {source, target})
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(source) as before, zipfile.ZipFile(target) as after:
                changed = {name for name in after.namelist()
                           if name not in before.namelist() or before.read(name) != after.read(name)}
            listed = {line[2:] for line in preview.stdout.splitlines() if line.startswith("- ")}
            self.assertEqual(changed, listed)
            self.assertEqual(source.read_bytes(), original)

    def test_preview_failure_does_not_create_output(self):
        with TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "bad.docx", Path(tmp) / "result.docx"
            source.write_bytes(b"bad input")
            result = subprocess.run([sys.executable, str(CLI), "format", str(source), "--out", str(target),
                                     "--dry-run"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
