"""Exercise a detached skill copy with freshly installed Node dependencies."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


class InstalledRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = TemporaryDirectory(prefix="gost install ")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.skill = cls.base / "installed skill"
        cls.work = cls.base / "Работа пользователя"
        cls.work.mkdir()
        cls.skill.mkdir()
        shutil.copy2(ROOT / "SKILL.md", cls.skill)
        for folder in ("scripts", "references"):
            shutil.copytree(ROOT / folder, cls.skill / folder,
                            ignore=shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc"))
        cls.env = {k: v for k, v in os.environ.items() if k not in ("NODE_PATH", "PYTHONPATH")}
        cls.env["PYTHONUTF8"] = "1"
        npm = shutil.which("npm")
        if npm is None:
            raise RuntimeError("npm is required for the isolated installation test")
        result = subprocess.run([npm, "ci", "--prefix", str(cls.skill / "scripts"),
                                 "--ignore-scripts", "--no-audit", "--no-fund"],
                                cwd=cls.work, env=cls.env, capture_output=True, text=True,
                                encoding="utf-8", timeout=180)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(self.skill / "scripts/gost_docx.py"), *map(str, args)],
                              cwd=self.work, env=self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=60)

    def test_detached_install_contains_helpers_and_loads_dependencies(self):
        for name in ("atomic_write.js", "task_spec.js", "audit_docx.py", "apply_gost.py"):
            self.assertTrue((self.skill / "scripts" / name).is_file(), name)
        self.assertFalse((self.skill / ".git").exists())
        self.assertFalse((self.work / "node_modules").exists())
        result = self.run_cli("doctor", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
