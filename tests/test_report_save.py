import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_docx


class ReportSaveTests(unittest.TestCase):
    def test_replace_failure_preserves_previous_report_and_removes_temporary(self):
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "report.md"
            target.write_text("previous", encoding="utf-8")
            with patch.object(audit_docx.os, "replace", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    audit_docx.save_report(target, "new")
            self.assertEqual(target.read_text(), "previous")
            self.assertEqual(list(Path(tmp).iterdir()), [target])
            audit_docx.save_report(target, "Новый отчёт")
            self.assertEqual(target.read_text(encoding="utf-8"), "Новый отчёт")

    def test_save_failure_returns_report_and_exit_two(self):
        for as_json in (False, True):
            with self.subTest(json=as_json):
                args = ["audit", "input.docx", "--out", "report.md"]
                if as_json:
                    args.append("--json")
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.object(sys, "argv", args), patch.object(audit_docx, "Audit") as audit, \
                        patch.object(audit_docx, "save_report", side_effect=OSError("disk full")), \
                        contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    audit.return_value.run.return_value = [("предупреждение", "section", "Check title")]
                    self.assertEqual(audit_docx.main(), 2)
                if as_json:
                    report = json.loads(stdout.getvalue())
                    self.assertTrue(report["completed"])
                    self.assertFalse(report["ok"])
                    self.assertEqual(len(report["findings"]), 1)
                    self.assertIn("disk full", report["errors"][0]["message"])
                    self.assertEqual(stderr.getvalue(), "")
                else:
                    self.assertIn("Check title", stdout.getvalue())
                    self.assertIn("disk full", stderr.getvalue())
