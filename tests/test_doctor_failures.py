import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gost_docx


class DoctorFailureTests(unittest.TestCase):
    def test_probe_failures_are_bounded_and_reported(self):
        for failure, message in [(subprocess.TimeoutExpired("node", 10), "exceeded 10 seconds"),
                                 (PermissionError("not executable"), "Could not run Node.js")]:
            for as_json in (False, True):
                with self.subTest(failure=failure, json=as_json):
                    stream = io.StringIO()
                    with patch.object(gost_docx.shutil, "which", return_value="node"), \
                            patch.object(gost_docx, "has_lxml", return_value=True), \
                            patch.object(gost_docx.subprocess, "run", side_effect=failure) as run, \
                            contextlib.redirect_stdout(stream):
                        self.assertEqual(gost_docx.doctor(as_json), 1)
                    self.assertEqual(run.call_args.kwargs["timeout"], 10)
                    self.assertIn(message, stream.getvalue())
                    if as_json:
                        report = json.loads(stream.getvalue())
                        self.assertFalse(report["ok"])
                        self.assertEqual(report["checks"][-1]["status"], "error")
                    else:
                        self.assertIn("ERROR", stream.getvalue())
