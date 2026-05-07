from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def write_message(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    body = json.dumps(message).encode("utf-8")
    assert process.stdin is not None
    process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    process.stdin.write(body)
    process.stdin.flush()


def read_message(process: subprocess.Popen[bytes]) -> dict[str, Any]:
    assert process.stdout is not None
    header = bytearray()
    while not header.endswith(b"\r\n\r\n"):
        chunk = process.stdout.read(1)
        if not chunk:
            raise RuntimeError("server closed stdout before sending a response")
        header.extend(chunk)
    length = 0
    for line in header.decode("ascii").splitlines():
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
            break
    if length <= 0:
        raise RuntimeError(f"missing Content-Length header: {header!r}")
    return json.loads(process.stdout.read(length).decode("utf-8"))


def assert_ok(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("error"):
        raise AssertionError(response["error"])
    return response["result"]


def main() -> None:
    server = Path(sys.argv[1])
    process = subprocess.Popen(
        [sys.executable, str(server)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        write_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
        )
        init = assert_ok(read_message(process))
        assert init["serverInfo"]["name"] == "companion-memory"

        write_message(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = assert_ok(read_message(process))["tools"]
        assert len(tools) == 8

        write_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "companion_save_memory",
                    "arguments": {
                        "content": "User prefers concise answers.",
                        "kind": "preference",
                        "tags": ["style"],
                    },
                },
            },
        )
        saved = assert_ok(read_message(process))["structuredContent"]["memory"]
        assert saved["kind"] == "preference"

        write_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "companion_search_memories",
                    "arguments": {"query": "concise"},
                },
            },
        )
        found = assert_ok(read_message(process))["structuredContent"]["memories"]
        assert found and found[0]["id"] == saved["id"]
    finally:
        if process.stdin:
            process.stdin.close()
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
