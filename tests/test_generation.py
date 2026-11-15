import json
import os
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_gost.js"
FIXTURE = ROOT / "tests" / "fixtures" / "minimal_report.json"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class GenerationTests(unittest.TestCase):
    def test_profile_generates_title_toc_and_page_rules(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.docx"
            subprocess.run(
                ["node", str(SCRIPT), str(FIXTURE), str(output)],
                cwd=ROOT,
                check=True,
                env={**os.environ, "NODE_PATH": str(ROOT / "scripts" / "node_modules")},
            )
            with zipfile.ZipFile(output) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
                text = "".join(node.text or "" for node in document.iter(W + "t"))
                self.assertIn("ТИТУЛЬНЫЙ ЛИСТ", text)
                self.assertNotIn("Иванов", text)
                self.assertIsNotNone(document.find(f".//{W}titlePg"))
                self.assertTrue(document.findall(f".//{W}fldChar"))
                self.assertTrue(any(
                    "TOC" in (node.get(W + "instr") or "")
                    for node in document.iter(W + "fldSimple")
                ) or any(
                    "TOC" in (node.text or "")
                    for node in document.iter(W + "instrText")
                ))
                chapter = next(node for node in document.iter(W + "p")
                               if "1 Основной раздел" in "".join(t.text or "" for t in node.iter(W + "t"))
                               and node.find(f"{W}pPr/{W}pStyle") is not None
                               and node.find(f"{W}pPr/{W}pStyle").get(W + "val") == "Heading1")
                self.assertIsNotNone(chapter.find(f"{W}pPr/{W}pageBreakBefore"))
                appendix = next(node for node in document.iter(W + "t") if node.text == "ПРИЛОЖЕНИЕ А")
                self.assertEqual(appendix.text, "ПРИЛОЖЕНИЕ А")


if __name__ == "__main__":
    unittest.main()
