#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

from companion_store import (
    export_data,
    forget_memory,
    get_persona,
    record_exchange,
    save_memory,
    search_memories,
    update_persona,
)


PROTOCOL_VERSION = "2024-11-05"
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TOOL_DEFINITIONS_PATH = PLUGIN_ROOT / "assets" / "tool-definitions.json"


def load_tools() -> list[dict[str, Any]]:
    with TOOL_DEFINITIONS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


TOOLS = load_tools()


def read_message() -> dict[str, Any] | None:
    first = sys.stdin.buffer.readline()
    if first == b"":
        return None
    while first in {b"\n", b"\r\n"}:
        first = sys.stdin.buffer.readline()
        if first == b"":
            return None
    lower = first.lower()
    if lower.startswith(b"content-length:"):
        length = int(first.split(b":", 1)[1].strip())
        while True:
            line = sys.stdin.buffer.readline()
            if line in {b"\n", b"\r\n", b""}:
                break
        body = sys.stdin.buffer.read(length)
        return json.loads(body.decode("utf-8"))
    return json.loads(first.decode("utf-8"))


def write_message(message: dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def result_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def tool_result(payload: Any) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
    }


def list_memories(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "memories": search_memories(
            query="",
            include_sensitive=bool(arguments.get("include_sensitive", False)),
            include_deleted=bool(arguments.get("include_deleted", False)),
            limit=int(arguments.get("limit", 25)),
        )
    }


TOOL_HANDLERS = {
    "companion_get_persona": lambda args: {"persona": get_persona()},
    "companion_update_persona": lambda args: {
        "persona": update_persona(args["patch"], bool(args.get("replace", False)))
    },
    "companion_save_memory": lambda args: {"memory": save_memory(**args)},
    "companion_search_memories": lambda args: {"memories": search_memories(**args)},
    "companion_list_memories": list_memories,
    "companion_forget_memory": lambda args: {"result": forget_memory(**args)},
    "companion_record_exchange": lambda args: {"exchange": record_exchange(**args)},
    "companion_export": lambda args: {"export": export_data(**args)},
}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return tool_result(handler(arguments or {}))


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if request_id is None and str(method).startswith("notifications/"):
        return None
    if method == "initialize":
        return result_response(
            request_id,
            {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "companion-memory", "version": "0.1.0"},
            },
        )
    if method == "ping":
        return result_response(request_id, {})
    if method == "tools/list":
        return result_response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        try:
            return result_response(
                request_id,
                call_tool(params.get("name", ""), params.get("arguments") or {}),
            )
        except Exception as exc:
            return result_response(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
    return error_response(request_id, -32601, f"Method not found: {method}")


def main() -> None:
    while True:
        try:
            request = read_message()
            if request is None:
                return
            response = handle_request(request)
            if response is not None:
                write_message(response)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            request_id = None
            try:
                request_id = request.get("id")  # type: ignore[name-defined]
            except Exception:
                pass
            write_message(error_response(request_id, -32603, str(exc)))


if __name__ == "__main__":
    main()
