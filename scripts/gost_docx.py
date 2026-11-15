#!/usr/bin/env python3
"""Portable command-line entry point for the gost-docx skill.

The command resolves all implementation files relative to this script, so it
works from a cloned repository and from an installed agent skill directory.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_python(script: str, args: list[str]) -> int:
    return subprocess.run([sys.executable, str(ROOT / script), *args]).returncode


def run_build(args: list[str]) -> int:
    env = os.environ.copy()
    node_modules = ROOT / "node_modules"
    existing = env.get("NODE_PATH")
    env["NODE_PATH"] = os.pathsep.join(
        part for part in (str(node_modules), existing) if part
    )
    return subprocess.run(
        ["node", str(ROOT / "build_gost.js"), *args], env=env
    ).returncode


def doctor() -> int:
    """Report whether optional runtime dependencies are available."""
    checks = {
        "python": True,
        "lxml": importlib.util.find_spec("lxml") is not None,
        "node": shutil.which("node") is not None,
        "docx": (ROOT / "node_modules" / "docx").is_dir(),
    }
    for name, available in checks.items():
        print(f"{'OK' if available else 'MISSING':7} {name}")
    return 0 if all(checks.values()) else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Portable command runner for the gost-docx skill."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit an existing DOCX")
    audit.add_argument("args", nargs=argparse.REMAINDER)

    format_parser = subparsers.add_parser(
        "format", help="Format a DOCX copy according to GOST rules"
    )
    format_parser.add_argument("args", nargs=argparse.REMAINDER)

    build = subparsers.add_parser("build", help="Build a DOCX from a JSON task")
    build.add_argument("args", nargs=argparse.REMAINDER)
    subparsers.add_parser("doctor", help="Check the local runtime environment")

    parsed = parser.parse_args()
    if parsed.command == "audit":
        return run_python("audit_docx.py", parsed.args)
    if parsed.command == "format":
        return run_python("apply_gost.py", parsed.args)
    if parsed.command == "doctor":
        return doctor()
    return run_build(parsed.args)


if __name__ == "__main__":
    raise SystemExit(main())
