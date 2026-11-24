#!/usr/bin/env python3
"""Portable command-line entry point for the gost-docx skill.

The command resolves all implementation files relative to this script, so it
works from a cloned repository and from an installed agent skill directory.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VERSION = "0.1.0"
LXML_HINT = "Install lxml in the active Python environment: python3 -m pip install lxml"
NODE_HINT = "Install Node.js and make sure node is on PATH."
DOCX_HINT = f'Install the Node.js dependencies: npm ci --prefix "{ROOT}"'


def has_lxml() -> bool:
    try:
        importlib.import_module("lxml.etree")
    except ImportError:
        return False
    return True


def run_python(script: str, args: list[str]) -> int:
    if not has_lxml():
        print(LXML_HINT, file=sys.stderr)
        return 1
    return subprocess.run([sys.executable, str(ROOT / script), *args]).returncode


def run_node(script: str, args: list[str]) -> int:
    node = shutil.which("node")
    if node is None:
        print(NODE_HINT, file=sys.stderr)
        return 1
    env = os.environ.copy()
    node_modules = ROOT / "node_modules"
    existing = env.get("NODE_PATH")
    env["NODE_PATH"] = os.pathsep.join(
        part for part in (str(node_modules), existing) if part
    )
    return subprocess.run(
        [node, str(ROOT / script), *args], env=env
    ).returncode


def doctor(json_output=False) -> int:
    """Check dependencies and show how to install missing components."""
    node = shutil.which("node")
    probe_error = None
    checks = [
        ("python", True, ""),
        ("lxml", has_lxml(), LXML_HINT),
        ("node", node is not None, NODE_HINT),
    ]
    if node is not None:
        try:
            result = subprocess.run(
                [node, "-e", 'require("docx")'],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            checks.append(("docx", result.returncode == 0, DOCX_HINT))
        except subprocess.TimeoutExpired:
            probe_error = "Node.js dependency check exceeded 10 seconds. Check the Node.js installation and retry."
        except OSError as error:
            probe_error = f"Could not run Node.js dependency check: {error}"
        if probe_error:
            checks.append(("docx", False, probe_error))

    ok = all(available for _, available, _ in checks)
    if json_output:
        items = [{"name": name, "status": "ok" if available else "missing",
                  "hint": hint if not available else None} for name, available, hint in checks]
        if probe_error:
            items[-1]["status"] = "error"
        if node is None:
            items.append({"name": "docx", "status": "skipped", "hint": NODE_HINT})
        print(json.dumps({"schema_version": 1, "ok": ok, "checks": items}))
        return 0 if ok else 1
    for name, available, hint in checks:
        status = "ERROR" if name == "docx" and probe_error else ("OK" if available else "MISSING")
        print(f"{status:7} {name}")
        if not available:
            print(f"        {hint}")
    if node is None:
        print("SKIPPED docx (requires Node.js)")
    return 0 if all(available for _, available, _ in checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Portable command runner for the gost-docx skill."
    )
    parser.add_argument(
        "--version", action="version", version=f"gost-docx {VERSION}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit an existing DOCX")
    audit.add_argument("docx", help="Input DOCX document")
    audit.add_argument("--out", help="Save the audit report to this path")
    audit.add_argument("--json", action="store_true", help="Emit a structured DOCX audit report")
    audit.add_argument("--fail-on-warning", action="store_true", help="Return failure for warnings as well as errors")

    format_parser = subparsers.add_parser(
        "format", help="Format a DOCX copy according to GOST rules"
    )
    format_parser.add_argument("docx", help="Input DOCX document (preserved)")
    format_parser.add_argument("--out", help="Output DOCX path (default: input_gost.docx)")
    format_parser.add_argument("--dry-run", action="store_true", help="Preview changed DOCX parts without saving")

    build = subparsers.add_parser("build", help="Build a DOCX from a JSON task")
    build.add_argument("task", help="Input task JSON")
    build.add_argument("output", help="Output DOCX path")
    build.add_argument("--strict", action="store_true", help="Reject unknown task fields before writing DOCX")
    validate = subparsers.add_parser("validate", help="Check a task JSON file")
    validate.add_argument("task", help="Path to the task JSON")
    validate.add_argument("--json", action="store_true", help="Emit a structured validation report")
    validate.add_argument("--strict", action="store_true", help="Reject unknown fields, including nested fields")
    doctor_parser = subparsers.add_parser("doctor", help="Check the local runtime environment")
    doctor_parser.add_argument("--json", action="store_true", help="Emit a structured dependency report")

    parsed = parser.parse_args()
    if parsed.command == "audit":
        if parsed.json and not has_lxml():
            print(json.dumps({"schema_version": 1, "ok": False, "completed": False,
                              "findings": [], "errors": [{"message": LXML_HINT}]}))
            return 2
        return run_python("audit_docx.py", [parsed.docx, *(["--out", parsed.out] if parsed.out else []),
                                           *(["--json"] if parsed.json else []),
                                           *(["--fail-on-warning"] if parsed.fail_on_warning else [])])
    if parsed.command == "format":
        return run_python("apply_gost.py", [parsed.docx, *(["--out", parsed.out] if parsed.out else []),
                                           *(["--dry-run"] if parsed.dry_run else [])])
    if parsed.command == "doctor":
        return doctor(parsed.json)
    if parsed.command == "validate":
        if parsed.json and shutil.which("node") is None:
            print(json.dumps({"schema_version": 1, "ok": False, "errors": [{"message": NODE_HINT}]}))
            return 1
        return run_node("task_spec.js", [parsed.task, *(["--json"] if parsed.json else []),
                                        *(["--strict"] if parsed.strict else [])])
    return run_node("build_gost.js", [parsed.task, parsed.output, *(["--strict"] if parsed.strict else [])])


if __name__ == "__main__":
    raise SystemExit(main())
