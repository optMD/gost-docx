import subprocess
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "build_gost.js"
AUDIT = ROOT / "scripts" / "audit_docx.py"
FIXTURE = ROOT / "tests" / "fixtures" / "minimal_report.json"


class AuditTests(unittest.TestCase):
    def test_json_audit_distinguishes_findings_from_unreadable_documents(self):
        runner = [sys.executable, str(AUDIT.with_name("gost_docx.py")), "audit"]
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.docx"
            report = Path(tmp) / "audit.json"
            subprocess.run(["node", str(GENERATOR), str(FIXTURE), str(source)], check=True)
            result = subprocess.run([*runner, "--json", "--out", str(report), str(source)],
                                    capture_output=True, text=True)
            data = json.loads(result.stdout)
            self.assertTrue(data["completed"])
            self.assertEqual(data, json.loads(report.read_text()))
            self.assertEqual(result.returncode, 0 if data["ok"] else 1)
            self.assertEqual(data["ok"], not any(f["severity"] == "error" for f in data["findings"]))
            source.write_bytes(b"not a DOCX")
            result = subprocess.run([*runner, str(source), "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["completed"])
            self.assertTrue(json.loads(result.stdout)["errors"])
            self.assertEqual(result.stderr, "")

    def test_report_and_format_refuse_to_overwrite_the_input(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "input.docx"
            subprocess.run(["node", str(GENERATOR), str(FIXTURE), str(source)], check=True)
            original = source.read_bytes()
            hard_link = folder / "alias.docx"
            os.link(source, hard_link)
            for script, code in ((AUDIT, 2), (AUDIT.with_name("apply_gost.py"), 1)):
                for output in (source, hard_link):
                    with self.subTest(script=script.name, output=output.name):
                        result = subprocess.run(
                            [sys.executable, str(script), str(source), "--out", str(output)],
                            capture_output=True, text=True,
                        )
                        self.assertEqual(result.returncode, code, result.stderr)
                        self.assertIn("совпадает с исходным файлом", result.stderr)
                        self.assertEqual(source.read_bytes(), original)

    def test_generated_document_is_openable_by_audit(self):
        try:
            import lxml  # noqa: F401
        except ImportError:
            self.skipTest("lxml is required by audit_docx.py")
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.docx"
            subprocess.run(
                ["node", str(GENERATOR), str(FIXTURE), str(output)],
                cwd=ROOT,
                check=True,
                env={**os.environ, "NODE_PATH": str(ROOT / "scripts" / "node_modules")},
            )
            result = subprocess.run(
                ["python3", str(AUDIT), str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertNotIn("не удалось открыть", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
