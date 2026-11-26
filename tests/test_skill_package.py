import os
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_runtime_metadata_matches_cli_and_lockfile(self):
        package = json.loads((ROOT / "scripts/package.json").read_text())
        lock = json.loads((ROOT / "scripts/package-lock.json").read_text())
        version = subprocess.run([sys.executable, str(ROOT / "scripts/gost_docx.py"), "--version"],
                                 capture_output=True, text=True, check=True).stdout.strip().split()[-1]
        self.assertEqual(package["version"], version)
        self.assertEqual(lock["version"], version)
        self.assertEqual(lock["packages"][""]["version"], version)
        self.assertEqual(package["name"], lock["name"])
        self.assertEqual(package["name"], lock["packages"][""]["name"])
        self.assertEqual(package["license"], lock["packages"][""]["license"])
        self.assertEqual(package["dependencies"], lock["packages"][""]["dependencies"])
        self.assertTrue(package["private"])

    def test_subcommand_help_and_argument_errors_need_no_dependencies(self):
        runner = [sys.executable, "-I", "-S", str(ROOT / "scripts/gost_docx.py")]
        for command, expected in [("audit", "--out"), ("format", "--out"), ("build", "output")]:
            with self.subTest(command=command):
                help_result = subprocess.run([*runner, command, "--help"],
                                             env={**os.environ, "PATH": ""}, capture_output=True, text=True)
                self.assertEqual(help_result.returncode, 0)
                self.assertIn(expected, help_result.stdout)
                missing = subprocess.run([*runner, command], capture_output=True, text=True)
                self.assertEqual(missing.returncode, 2)
                self.assertIn("required", missing.stderr)
                self.assertNotIn("Install", missing.stderr)

    def test_doctor_json_reports_missing_and_skipped_dependencies(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/gost_docx.py"), "doctor", "--json"],
            env={**os.environ, "PATH": ""}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], 1)
        self.assertFalse(report["ok"])
        checks = {item["name"]: item for item in report["checks"]}
        self.assertEqual(checks["node"]["status"], "missing")
        self.assertEqual(checks["docx"]["status"], "skipped")
        self.assertTrue(checks["node"]["hint"])
        self.assertEqual(result.stderr, "")

    def test_required_package_files_exist(self):
        for relative in (
            "SKILL.md",
            "references/gost-rules.md",
            "scripts/audit_docx.py",
            "scripts/apply_gost.py",
            "scripts/build_gost.js",
            "scripts/gost_docx.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_skill_has_valid_minimal_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        header = match.group(1)
        self.assertRegex(header, r"(?m)^name:\s*gost-docx\s*$")
        self.assertRegex(header, r"(?m)^description:\s*\S")

    def test_instructions_do_not_contain_machine_specific_paths(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"/Users/|/home/[^ ]+|~/.claude|~/.agents")

    def test_runner_help_is_available_without_dependencies(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/gost_docx.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("audit", result.stdout)
        self.assertIn("build", result.stdout)
        self.assertIn("doctor", result.stdout)

    def test_runner_reports_version(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/gost_docx.py"), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"^gost-docx \d+\.\d+\.\d+\n$")

    def test_runner_explains_missing_node(self):
        env = {**os.environ, "PATH": ""}
        runner = [sys.executable, str(ROOT / "scripts/gost_docx.py")]
        result = subprocess.run([*runner, "validate", "task.json"], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Install Node.js", result.stderr)

        result = subprocess.run([*runner, "doctor"], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("MISSING node", result.stdout)
        self.assertIn("SKIPPED docx", result.stdout)

    def test_runner_explains_missing_lxml(self):
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(ROOT / "scripts/gost_docx.py"), "audit", "input.docx"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("python3 -m pip install lxml", result.stderr)


if __name__ == "__main__":
    unittest.main()
