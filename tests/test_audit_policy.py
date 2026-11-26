import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_docx
import gost_docx
from lxml import etree


class AuditPolicyTests(unittest.TestCase):
    def test_toc_entries_are_exempt_but_real_chapters_still_need_breaks(self):
        audit = audit_docx.Audit.__new__(audit_docx.Audit)
        audit.findings = []
        audit.doc = etree.fromstring(f'<w:document xmlns:w="{audit_docx.W}"><w:body>'
            '<w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:t>1 Chapter</w:t></w:r></w:p>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>1 Chapter</w:t></w:r></w:p>'
            '</w:body></w:document>')
        audit.check_main_section_breaks()
        self.assertEqual(len(audit.findings), 1)
        self.assertEqual(audit.findings[0][1], "абз.1")

    def test_warning_policy_keeps_severity_and_controls_json_status(self):
        for findings in ([], [("предупреждение", "раздел", "Check visually")],
                         [("ошибка", "раздел", "Wrong margin")]):
            for strict in (False, True):
                for json_output in (False, True):
                    with self.subTest(findings=findings, strict=strict, json=json_output):
                        args = ["audit", "input.docx"]
                        if strict:
                            args.append("--fail-on-warning")
                        if json_output:
                            args.append("--json")
                        stream = io.StringIO()
                        with patch.object(sys, "argv", args), patch.object(audit_docx, "Audit") as audit:
                            audit.return_value.run.return_value = findings
                            with contextlib.redirect_stdout(stream):
                                code = audit_docx.main()
                        failed = bool(findings) and (strict or findings[0][0] == "ошибка")
                        self.assertEqual(code, int(failed))
                        if json_output:
                            report = json.loads(stream.getvalue())
                            self.assertEqual(report["ok"], not failed)
                            self.assertTrue(report["completed"])
                            if findings and findings[0][0] == "предупреждение":
                                self.assertEqual(report["findings"][0]["severity"], "warning")

    def test_runner_forwards_warning_policy(self):
        with patch.object(sys, "argv", ["gost", "audit", "input.docx", "--fail-on-warning"]), \
                patch.object(gost_docx, "run_python", return_value=1) as run:
            self.assertEqual(gost_docx.main(), 1)
            run.assert_called_once_with("audit_docx.py", ["input.docx", "--fail-on-warning"])
