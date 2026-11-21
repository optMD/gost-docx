import json
import os
import shutil
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_gost.js"
FIXTURE = ROOT / "tests" / "fixtures" / "minimal_report.json"
CLI = ROOT / "scripts" / "gost_docx.py"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class GenerationTests(unittest.TestCase):
    def test_validate_checks_task_without_installing_docx(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy(CLI, folder)
            shutil.copy(CLI.with_name("task_spec.js"), folder)
            command = [sys.executable, str(folder / CLI.name), "validate"]
            result = subprocess.run([*command, str(FIXTURE)], cwd=folder,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Valid task JSON", result.stdout)

            task = folder / "invalid.json"
            task.write_text('{"chapters":[{}]}', encoding="utf-8")
            result = subprocess.run([*command, task.name], cwd=folder,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("chapters[0].heading", result.stderr)
            self.assertEqual({path.name for path in folder.iterdir()},
                             {CLI.name, "task_spec.js", task.name})

    def test_build_rejects_invalid_spec_before_touching_output(self):
        cases = [
            ("{", "Invalid JSON"),
            ("[]", "$: expected an object"),
            ('{"profile":"unknown"}', "profile: expected one of report"),
            ('{"introduction":"text"}', "introduction: expected an array"),
            ('{"abstract":{"keywords":[42]}}', "abstract.keywords[0]: expected a string"),
            ('{"keywords":["ГОСТ"]}', "keywords: move this field to abstract.keywords"),
            ('{"keywords":[],"abstract":{"keywords":["ГОСТ"]}}',
             "keywords: move this field to abstract.keywords"),
            ('{"chapters":[{"heading":"Main","subsections":[{}]}]}',
             "chapters[0].subsections[0].heading: expected a non-empty string"),
            ('{"chapters":[{"heading":"Main","paragraphs":[{}]}]}',
             "chapters[0].paragraphs[0]: expected a string"),
            ('{"sources":[null]}', "sources[0]: expected an object"),
            ('{"appendices":[{"letter":1}]}', "appendices[0].letter: expected a string"),
        ]
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            spec = folder / "task.json"
            output = folder / "report.docx"
            output.write_bytes(b"existing file")
            for contents, message in cases:
                with self.subTest(contents=contents):
                    spec.write_text(contents, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "scripts" / "gost_docx.py"),
                         "build", spec.name, output.name],
                        cwd=folder,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertEqual(output.read_bytes(), b"existing file")

    def test_build_supports_text_objects_and_optional_fields(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            spec = folder / "task.json"
            output = folder / "report.docx"
            spec.write_text(json.dumps({"sources": ["First source", {"text": "Second source"}]}),
                            encoding="utf-8")
            subprocess.run(["node", str(SCRIPT), str(spec), str(output)], check=True, cwd=folder)
            with zipfile.ZipFile(output) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
                text = " ".join(node.text or "" for node in document.iter(W + "t"))
            self.assertIn("1. First source", text)
            self.assertIn("2. Second source", text)

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
