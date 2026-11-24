import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/gost_docx.py"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class DocxFailureTests(unittest.TestCase):
    def test_invalid_xml_parts_produce_diagnostics_and_preserve_output(self):
        valid = f'<w:document xmlns:w="{W}"><w:body/></w:document>'
        for parts in ({}, {"word/document.xml": "<broken"},
                      {"word/document.xml": "<other/>"},
                      {"word/document.xml": valid, "word/styles.xml": "<broken"},
                      {"word/document.xml": valid, "word/_rels/document.xml.rels": "<broken"}):
            with self.subTest(parts=parts), TemporaryDirectory() as tmp:
                source, target = Path(tmp) / "input.docx", Path(tmp) / "output.docx"
                with zipfile.ZipFile(source, "w") as archive:
                    for name, value in parts.items():
                        archive.writestr(name, value)
                target.write_bytes(b"previous output")
                result = subprocess.run([sys.executable, str(CLI), "audit", str(source), "--json"],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json.loads(result.stdout)["completed"])
                self.assertNotIn("Traceback", result.stderr)
                result = subprocess.run([sys.executable, str(CLI), "format", str(source), "--out", str(target)],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(target.read_bytes(), b"previous output")
