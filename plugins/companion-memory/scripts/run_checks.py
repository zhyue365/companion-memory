#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
JSON_FILES = [
    REPO / ".agents" / "plugins" / "marketplace.json",
    ROOT / ".codex-plugin" / "plugin.json",
    ROOT / ".mcp.json",
    ROOT / "assets" / "default-persona.json",
    ROOT / "assets" / "tool-definitions.json",
]


def check_json() -> None:
    for path in JSON_FILES:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
        print(f"json ok: {path.relative_to(REPO)}")


def check_compile() -> None:
    pycache = REPO / ".pycache"
    os.environ["PYTHONPYCACHEPREFIX"] = str(pycache)
    for folder in (SCRIPTS, TESTS):
        for path in sorted(folder.glob("*.py")):
            py_compile.compile(str(path), doraise=True)
            print(f"compile ok: {path.relative_to(REPO)}")


def check_tests() -> None:
    sys.path.insert(0, str(SCRIPTS))
    suite = unittest.defaultTestLoader.discover(str(TESTS))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


def check_demo_gif() -> None:
    demo = ROOT / "assets" / "demo.gif"
    if not demo.exists():
        raise AssertionError("demo.gif is missing; run generate_demo_gif.py")
    header = demo.read_bytes()[:6]
    if header not in {b"GIF87a", b"GIF89a"}:
        raise AssertionError("demo.gif does not look like a GIF")
    print(f"gif ok: {demo.relative_to(REPO)} ({demo.stat().st_size} bytes)")


def check_mcp_smoke() -> None:
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as db:
        env = os.environ.copy()
        env["COMPANION_MEMORY_DB"] = db.name
        script = TESTS / "mcp_smoke_client.py"
        subprocess.run(
            [sys.executable, str(script), str(SCRIPTS / "companion_memory_server.py")],
            check=True,
            env=env,
            cwd=str(ROOT),
        )
    print("mcp smoke ok")


def main() -> None:
    check_json()
    check_compile()
    check_tests()
    check_demo_gif()
    check_mcp_smoke()
    print("all checks passed")


if __name__ == "__main__":
    main()
