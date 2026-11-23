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
    def test_strict_build_rejects_typo_before_overwriting_output(self):
        with TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.json"
            output = Path(tmp) / "result.docx"
            task.write_text('{"chapters":[{"heading":"Main","pargraphs":["Lost text"]}]}')
            output.write_bytes(b"existing document")
            command = [sys.executable, str(CLI), "build", str(task), str(output)]
            result = subprocess.run([*command, "--strict"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("chapters[0].pargraphs", result.stderr)
            self.assertEqual(output.read_bytes(), b"existing document")
            task.write_text('{"chapters":[{"heading":"Main","paragraphs":["Kept text"]}]}')
            result = subprocess.run([*command, "--strict"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("Kept text", archive.read("word/document.xml").decode())

    def test_strict_validation_detects_nested_typos_without_changing_default(self):
        cases = [({"titel": "Title"}, "$.titel"),
                 ({"abstract": {"keywrods": []}}, "abstract.keywrods"),
                 ({"chapters": [{"heading": "Main", "pargraphs": []}]}, "chapters[0].pargraphs"),
                 ({"sources": [{"text": "Book", "year": 2020}]}, "sources[0].year"),
                 ({"appendices": [{"titel": "Extra"}]}, "appendices[0].titel")]
        with TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.json"
            for spec, path in cases:
                with self.subTest(path=path):
                    task.write_text(json.dumps(spec), encoding="utf-8")
                    command = [sys.executable, str(CLI), "validate", str(task), "--json"]
                    result = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    result = subprocess.run([*command, "--strict"], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(path, json.loads(result.stdout)["errors"][0]["message"])
            result = subprocess.run([sys.executable, str(CLI), "validate", str(FIXTURE), "--strict"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_preserves_task_for_same_path_and_aliases(self):
        with TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.json"
            task.write_text('{"introduction":["Keep this text"]}', encoding="utf-8")
            original = task.read_bytes()
            hardlink = Path(tmp) / "hard.docx"
            os.link(task, hardlink)
            symlink = Path(tmp) / "symbolic.docx"
            symlink.symlink_to(task)
            for output in (task, hardlink, symlink):
                with self.subTest(output=output):
                    result = subprocess.run([sys.executable, str(CLI), "build", str(task), str(output)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("Output path refers to the input task", result.stderr)
                    self.assertEqual(task.read_bytes(), original)

    def test_validation_json_reports_success_and_failures(self):
        with TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.json"
            for content, expected in [("{}", True), ("{", False),
                                      ('{"sources":[""]}', False), (None, False)]:
                with self.subTest(content=content):
                    if content is None:
                        task.unlink()
                    else:
                        task.write_text(content, encoding="utf-8")
                    result = subprocess.run([sys.executable, str(CLI), "validate", str(task), "--json"],
                                            capture_output=True, text=True)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["schema_version"], 1)
                    self.assertEqual(report["ok"], expected)
                    self.assertEqual(bool(report["errors"]), not expected)
                    self.assertEqual(result.returncode, 0 if expected else 1)
                    self.assertEqual(result.stderr, "")
            result = subprocess.run([sys.executable, str(CLI), "validate", str(task), "--json"],
                                    env={**os.environ, "PATH": ""}, capture_output=True, text=True)
            self.assertFalse(json.loads(result.stdout)["ok"])
            self.assertEqual(result.returncode, 1)

    def test_utf8_bom_task_validates_and_builds(self):
        with TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.json"
            output = Path(tmp) / "report.docx"
            task.write_text(json.dumps({"sources": ["BOM source"]}), encoding="utf-8-sig")
            for args in (["validate", str(task)], ["build", str(task), str(output)]):
                result = subprocess.run([sys.executable, str(CLI), *args],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
            self.assertIn("BOM source", "".join(document.itertext()))

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
            ('{"sources":[""]}', "sources[0]: expected a non-empty string"),
            ('{"sources":["  "]}', "sources[0]: expected a non-empty string"),
            ('{"sources":[{"text":""}]}', "sources[0].text: expected a non-empty string"),
            ('{"sources":[{"text":"  "}]}', "sources[0].text: expected a non-empty string"),
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
