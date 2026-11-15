import subprocess
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "build_gost.js"
AUDIT = ROOT / "scripts" / "audit_docx.py"
FIXTURE = ROOT / "tests" / "fixtures" / "minimal_report.json"


class AuditTests(unittest.TestCase):
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
