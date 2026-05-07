from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PLUGIN_ROOT / "data" / "companion_memory.sqlite3"
DEFAULT_PERSONA_PATH = PLUGIN_ROOT / "assets" / "default-persona.json"
SEARCH_SCHEMA_VERSION = 2
LOCAL_EMBEDDING_MODEL = "local-hash-ngram-v1"
LOCAL_EMBEDDING_DIMENSIONS = 128
VECTOR_SEARCH_THRESHOLD = 0.18
MAX_SEARCH_CANDIDATES = 1000


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
        ensure_search_schema(conn)
        if get_setting(conn, "persona") is None:
            set_setting(conn, "persona", load_default_persona())
        conn.commit()
    return resolved


def ensure_search_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_vectors (
          memory_id TEXT PRIMARY KEY,
          embedding TEXT NOT NULL,
          dimensions INTEGER NOT NULL,
          model TEXT NOT NULL,
          indexed_text TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_vectors_model ON memory_vectors(model)")
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
              memory_id UNINDEXED,
              kind,
              content,
              summary,
              tags,
              tokenize='trigram'
            )
            """
        )
    except sqlite3.OperationalError:
        set_setting(conn, "search_fts5_available", False)
    needs_rebuild = get_setting(conn, "search_schema_version") != SEARCH_SCHEMA_VERSION
    memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    vector_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM memories
        JOIN memory_vectors ON memory_vectors.memory_id = memories.id
        """
    ).fetchone()[0]
    fts_count = 0
    if fts5_available(conn):
        fts_count = conn.execute("SELECT COUNT(*) FROM memory_fts").fetchone()[0]
    if needs_rebuild or vector_count != memory_count or (fts5_available(conn) and fts_count != memory_count):
        rebuild_search_indexes(conn)
        set_setting(conn, "search_schema_version", SEARCH_SCHEMA_VERSION)
        set_setting(conn, "search_embedding_model", LOCAL_EMBEDDING_MODEL)


def fts5_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'memory_fts'"
    ).fetchone()
    return row is not None


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


def parse_tags(tags: Any) -> list[str]:
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    if not tags:
        return []
    try:
        data = json.loads(str(tags))
    except json.JSONDecodeError:
        return [str(tags)]
    if isinstance(data, list):
        return [str(tag) for tag in data]
    return [str(data)]


def memory_index_text(memory: sqlite3.Row | dict[str, Any]) -> str:
    get = memory.get if isinstance(memory, dict) else lambda key, default="": memory[key] if key in memory.keys() else default
    tags = parse_tags(get("tags", "[]"))
    parts = [
        str(get("kind", "")),
        str(get("content", "")),
        str(get("summary", "")),
        " ".join(tags),
        str(get("source", "")),
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def embedding_features(text: str) -> list[str]:
    normalized = text.lower()
    features: list[str] = []
    features.extend(f"word:{token}" for token in re.findall(r"[a-z0-9_][a-z0-9_.+-]{1,}", normalized))
    features.extend(f"cjk:{token}" for token in re.findall(r"[\u4e00-\u9fff]{2,}", normalized))
    compact = re.sub(r"\s+", "", normalized)
    max_chars = min(len(compact), 1200)
    compact = compact[:max_chars]
    for size in (2, 3, 4):
        if len(compact) < size:
            continue
        features.extend(f"gram{size}:{compact[index:index + size]}" for index in range(len(compact) - size + 1))
    if not features and normalized.strip():
        features.append(f"text:{normalized.strip()}")
    return features


def query_terms(query: str) -> list[str]:
    terms = []
    for token in re.findall(r"[a-z0-9_][a-z0-9_.+-]{1,}|[\u4e00-\u9fff]{2,}", query.lower()):
        token = token.strip()
        if token and token not in terms:
            terms.append(token)
    return terms[:20]


def local_embedding(text: str, dimensions: int = LOCAL_EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    for feature in embedding_features(text):
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        index = value % dimensions
        sign = 1.0 if (value >> 63) == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [round(value / norm, 6) for value in vector]


def parse_embedding(payload: str) -> list[float]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [float(value) for value in data]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def sync_memory_search_index(conn: sqlite3.Connection, memory: sqlite3.Row | dict[str, Any]) -> None:
    memory_id = str(memory["id"])
    tags = parse_tags(memory["tags"])
    indexed_text = memory_index_text(memory)
    now = utc_now()
    if fts5_available(conn):
        conn.execute("DELETE FROM memory_fts WHERE memory_id = ?", (memory_id,))
        conn.execute(
            """
            INSERT INTO memory_fts(memory_id, kind, content, summary, tags)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                str(memory["kind"]),
                str(memory["content"]),
                str(memory["summary"] or ""),
                " ".join(tags),
            ),
        )
    conn.execute(
        """
        INSERT INTO memory_vectors(memory_id, embedding, dimensions, model, indexed_text, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(memory_id) DO UPDATE SET
          embedding = excluded.embedding,
          dimensions = excluded.dimensions,
          model = excluded.model,
          indexed_text = excluded.indexed_text,
          updated_at = excluded.updated_at
        """,
        (
            memory_id,
            json.dumps(local_embedding(indexed_text), separators=(",", ":")),
            LOCAL_EMBEDDING_DIMENSIONS,
            LOCAL_EMBEDDING_MODEL,
            indexed_text,
            now,
        ),
    )


def rebuild_search_indexes(conn: sqlite3.Connection) -> dict[str, int]:
    if fts5_available(conn):
        conn.execute("DELETE FROM memory_fts")
    conn.execute("DELETE FROM memory_vectors")
    rows = conn.execute("SELECT * FROM memories ORDER BY created_at ASC").fetchall()
    for row in rows:
        sync_memory_search_index(conn, row)
    return {"memories_indexed": len(rows)}


def search_index_stats(path: str | Path | None = None) -> dict[str, Any]:
    init_db(path)
    with connect(path) as conn:
        memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        vector_count = conn.execute("SELECT COUNT(*) FROM memory_vectors").fetchone()[0]
        fts_available = fts5_available(conn)
        fts_count = conn.execute("SELECT COUNT(*) FROM memory_fts").fetchone()[0] if fts_available else 0
    return {
        "schema_version": SEARCH_SCHEMA_VERSION,
        "embedding_model": LOCAL_EMBEDDING_MODEL,
        "embedding_dimensions": LOCAL_EMBEDDING_DIMENSIONS,
        "fts5_available": fts_available,
        "memories": memory_count,
        "fts_rows": fts_count,
        "vector_rows": vector_count,
    }


def rebuild_search_indexes_for_path(path: str | Path | None = None) -> dict[str, Any]:
    init_db(path)
    with connect(path) as conn:
        result = rebuild_search_indexes(conn)
        set_setting(conn, "search_schema_version", SEARCH_SCHEMA_VERSION)
        set_setting(conn, "search_embedding_model", LOCAL_EMBEDDING_MODEL)
        conn.commit()
    return {**result, **search_index_stats(path)}


def build_fts_query(query: str) -> str:
    terms = []
    for raw in re.findall(r"\S+", query.strip().lower()):
        term = raw.replace('"', " ").strip()
        if not term:
            continue
        if len(term) < 3 and not re.search(r"[a-z0-9]", term):
            continue
        terms.append(f'"{term}"')
    return " OR ".join(terms[:12])


def fts_scores(conn: sqlite3.Connection, query: str) -> dict[str, float]:
    if not query.strip() or not fts5_available(conn):
        return {}
    fts_query = build_fts_query(query)
    if not fts_query:
        return {}
    try:
        rows = conn.execute(
            """
            SELECT memory_id, bm25(memory_fts) AS rank
            FROM memory_fts
            WHERE memory_fts MATCH ?
            LIMIT ?
            """,
            (fts_query, MAX_SEARCH_CANDIDATES),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {row["memory_id"]: 2.0 + min(2.0, max(0.0, -float(row["rank"]))) for row in rows}


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
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        sync_memory_search_index(conn, row)
        conn.commit()
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
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    candidate_limit = limit if not query.strip() else MAX_SEARCH_CANDIDATES
    sql = f"""
        SELECT * FROM memories
        {where}
        ORDER BY pinned DESC, updated_at DESC, created_at DESC
        LIMIT ?
    """
    params.append(candidate_limit)
    with connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
        if not query.strip():
            return [row_to_memory(row) for row in rows[:limit]]
        fts_rank = fts_scores(conn, query)
        vectors = {
            row["memory_id"]: parse_embedding(row["embedding"])
            for row in conn.execute("SELECT memory_id, embedding FROM memory_vectors").fetchall()
        }
    query_text = query.strip().lower()
    query_vector = local_embedding(query_text)
    scored: list[tuple[float, str, str, dict[str, Any]]] = []
    for row in rows:
        memory = row_to_memory(row)
        indexed_text = memory_index_text(memory)
        indexed_lower = indexed_text.lower()
        terms = query_terms(query_text)
        matched_terms = sum(1 for term in terms if term in indexed_lower)
        like_score = 3.0 if query_text in indexed_lower else 0.0
        if matched_terms:
            like_score = max(like_score, 1.0 + 0.5 * matched_terms)
        rank_score = fts_rank.get(memory["id"], 0.0)
        vector_score = cosine_similarity(query_vector, vectors.get(memory["id"], []))
        if like_score or rank_score or vector_score >= VECTOR_SEARCH_THRESHOLD:
            total_score = like_score + rank_score + max(0.0, vector_score)
            if memory["pinned"]:
                total_score += 0.5
            scored.append((total_score, str(memory["updated_at"]), str(memory["created_at"]), memory))
    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [memory for *_sort_keys, memory in scored[:limit]]


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
    parser.add_argument("--print-search-stats", action="store_true", help="Print FTS/vector index stats.")
    parser.add_argument("--rebuild-search-index", action="store_true", help="Rebuild FTS5 and vector indexes.")
    args = parser.parse_args()

    path = init_db(args.db or None)
    if args.rebuild_search_index:
        print(json.dumps(rebuild_search_indexes_for_path(path), ensure_ascii=False, indent=2))
    if args.show_path:
        print(path)
    if args.print_persona:
        print(json.dumps(get_persona(path), ensure_ascii=False, indent=2))
    if args.print_search_stats:
        print(json.dumps(search_index_stats(path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
