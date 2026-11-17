import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
