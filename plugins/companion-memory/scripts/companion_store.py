from __future__ import annotations

import argparse
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PLUGIN_ROOT / "data" / "companion_memory.sqlite3"
DEFAULT_PERSONA_PATH = PLUGIN_ROOT / "assets" / "default-persona.json"


def db_path_from_env(path: str | None = None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    env_path = os.environ.get("COMPANION_MEMORY_DB")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return DEFAULT_DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    resolved = db_path_from_env(str(path) if path else None)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        os.chmod(resolved, 0o600)
    except OSError:
        pass
    return conn


def init_db(path: str | Path | None = None) -> Path:
    resolved = db_path_from_env(str(path) if path else None)
    with connect(resolved) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              content TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              tags TEXT NOT NULL DEFAULT '[]',
              sensitivity TEXT NOT NULL DEFAULT 'private',
              source TEXT NOT NULL DEFAULT '',
              pinned INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
            CREATE INDEX IF NOT EXISTS idx_memories_sensitivity ON memories(sensitivity);
            CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories(deleted_at);
            CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

            CREATE TABLE IF NOT EXISTS exchanges (
              id TEXT PRIMARY KEY,
              user_message TEXT NOT NULL,
              assistant_message TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              tags TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL
            );
            """
        )
        if get_setting(conn, "persona") is None:
            set_setting(conn, "persona", load_default_persona())
    return resolved


def load_default_persona() -> dict[str, Any]:
    with DEFAULT_PERSONA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_setting(conn: sqlite3.Connection, key: str) -> Any | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    return json.loads(row["value"])


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    conn.execute(
        """
        INSERT INTO settings(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = excluded.updated_at
        """,
        (key, payload, utc_now()),
    )


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_persona(path: str | Path | None = None) -> dict[str, Any]:
    init_db(path)
    with connect(path) as conn:
        persona = get_setting(conn, "persona")
    return persona or load_default_persona()


def update_persona(patch: dict[str, Any], replace: bool = False, path: str | Path | None = None) -> dict[str, Any]:
    init_db(path)
    with connect(path) as conn:
        current = get_setting(conn, "persona") or load_default_persona()
        updated = patch if replace else deep_merge(current, patch)
        set_setting(conn, "persona", updated)
        conn.commit()
    return updated


def normalize_tags(tags: list[str] | None) -> str:
    if not tags:
        return "[]"
    cleaned = sorted({str(tag).strip() for tag in tags if str(tag).strip()})
    return json.dumps(cleaned, ensure_ascii=False)


def row_to_memory(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["tags"] = json.loads(data.get("tags") or "[]")
    data["pinned"] = bool(data.get("pinned"))
    return data


def save_memory(
    content: str,
    kind: str = "profile",
    summary: str = "",
    tags: list[str] | None = None,
    sensitivity: str = "private",
    source: str = "",
    pinned: bool = False,
    path: str | Path | None = None,
) -> dict[str, Any]:
    if not content.strip():
        raise ValueError("content is required")
    if sensitivity not in {"public", "private", "sensitive"}:
        raise ValueError("sensitivity must be public, private, or sensitive")
    init_db(path)
    memory_id = str(uuid.uuid4())
    now = utc_now()
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO memories(
              id, kind, content, summary, tags, sensitivity, source, pinned,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                kind,
                content.strip(),
                summary.strip(),
                normalize_tags(tags),
                sensitivity,
                source.strip(),
                1 if pinned else 0,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    return row_to_memory(row)


def search_memories(
    query: str = "",
    kinds: list[str] | None = None,
    include_sensitive: bool = False,
    include_deleted: bool = False,
    limit: int = 12,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    init_db(path)
    limit = max(1, min(int(limit), 100))
    clauses = []
    params: list[Any] = []
    if not include_deleted:
        clauses.append("deleted_at IS NULL")
    if not include_sensitive:
        clauses.append("sensitivity != 'sensitive'")
    if kinds:
        placeholders = ",".join("?" for _ in kinds)
        clauses.append(f"kind IN ({placeholders})")
        params.extend(kinds)
    if query.strip():
        like = f"%{query.strip()}%"
        clauses.append("(content LIKE ? OR summary LIKE ? OR tags LIKE ?)")
        params.extend([like, like, like])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    sql = f"""
        SELECT * FROM memories
        {where}
        ORDER BY pinned DESC, updated_at DESC, created_at DESC
        LIMIT ?
    """
    params.append(limit)
    with connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_memory(row) for row in rows]


def get_memory(memory_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    init_db(path)
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    return row_to_memory(row) if row else None


def forget_memory(
    memory_id: str = "",
    query: str = "",
    kind: str = "",
    dry_run: bool = True,
    limit: int = 20,
    path: str | Path | None = None,
) -> dict[str, Any]:
    init_db(path)
    limit = max(1, min(int(limit), 100))
    clauses = ["deleted_at IS NULL"]
    params: list[Any] = []
    if memory_id:
        clauses.append("id = ?")
        params.append(memory_id)
    elif query.strip():
        like = f"%{query.strip()}%"
        clauses.append("(content LIKE ? OR summary LIKE ? OR tags LIKE ?)")
        params.extend([like, like, like])
    else:
        raise ValueError("memory_id or query is required")
    if kind:
        clauses.append("kind = ?")
        params.append(kind)
    where = " AND ".join(clauses)
    with connect(path) as conn:
        rows = conn.execute(
            f"SELECT * FROM memories WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        matches = [row_to_memory(row) for row in rows]
        if not dry_run and matches:
            now = utc_now()
            ids = [memory["id"] for memory in matches]
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"UPDATE memories SET deleted_at = ?, updated_at = ? WHERE id IN ({placeholders})",
                [now, now, *ids],
            )
            conn.commit()
    return {"dry_run": dry_run, "count": len(matches), "matches": matches}


def record_exchange(
    user_message: str,
    assistant_message: str,
    summary: str = "",
    tags: list[str] | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    if not user_message.strip() and not assistant_message.strip():
        raise ValueError("user_message or assistant_message is required")
    init_db(path)
    exchange_id = str(uuid.uuid4())
    now = utc_now()
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO exchanges(id, user_message, assistant_message, summary, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                exchange_id,
                user_message.strip(),
                assistant_message.strip(),
                summary.strip(),
                normalize_tags(tags),
                now,
            ),
        )
        conn.commit()
    return {
        "id": exchange_id,
        "summary": summary.strip(),
        "tags": json.loads(normalize_tags(tags)),
        "created_at": now,
    }


def export_data(
    include_sensitive: bool = False,
    include_deleted: bool = False,
    path: str | Path | None = None,
) -> dict[str, Any]:
    init_db(path)
    with connect(path) as conn:
        persona = get_setting(conn, "persona") or load_default_persona()
        memories = search_memories(
            query="",
            include_sensitive=include_sensitive,
            include_deleted=include_deleted,
            limit=100,
            path=path,
        )
        exchanges = [
            {
                **dict(row),
                "tags": json.loads(row["tags"] or "[]"),
            }
            for row in conn.execute(
                "SELECT * FROM exchanges ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        ]
    return {
        "exported_at": utc_now(),
        "include_sensitive": include_sensitive,
        "include_deleted": include_deleted,
        "persona": persona,
        "memories": memories,
        "exchanges": exchanges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the Companion Memory SQLite database.")
    parser.add_argument("--db", default="", help="Optional database path. Defaults to plugin data directory.")
    parser.add_argument("--show-path", action="store_true", help="Print the initialized database path.")
    parser.add_argument("--print-persona", action="store_true", help="Print the current persona JSON.")
    args = parser.parse_args()

    path = init_db(args.db or None)
    if args.show_path:
        print(path)
    if args.print_persona:
        print(json.dumps(get_persona(path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
