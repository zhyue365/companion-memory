from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from companion_store import (  # noqa: E402
    forget_memory,
    get_persona,
    save_memory,
    search_memories,
    update_persona,
)


class CompanionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "memory.sqlite3"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_persona_initializes_and_merges_patch(self) -> None:
        persona = get_persona(self.db_path)
        self.assertEqual(persona["language"], "zh-CN")

        updated = update_persona(
            {"memory_policy": {"store_raw_transcripts": True}},
            path=self.db_path,
        )

        self.assertTrue(updated["memory_policy"]["store_raw_transcripts"])
        self.assertIn("sensitive_recall_default", updated["memory_policy"])

    def test_save_and_search_memory(self) -> None:
        saved = save_memory(
            "用户喜欢被叫宝贝。",
            kind="preference",
            tags=["nickname", "nickname", " "],
            pinned=True,
            path=self.db_path,
        )

        self.assertEqual(saved["tags"], ["nickname"])
        results = search_memories("宝贝", kinds=["preference"], path=self.db_path)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], saved["id"])
        self.assertTrue(results[0]["pinned"])

    def test_sensitive_memories_are_hidden_by_default(self) -> None:
        save_memory("普通偏好", path=self.db_path)
        save_memory("敏感家庭细节", sensitivity="sensitive", path=self.db_path)

        default_results = search_memories("", path=self.db_path)
        sensitive_results = search_memories("", include_sensitive=True, path=self.db_path)

        self.assertEqual(len(default_results), 1)
        self.assertEqual(len(sensitive_results), 2)

    def test_forget_memory_previews_then_soft_deletes(self) -> None:
        saved = save_memory("需要忘掉的约定", kind="relationship", path=self.db_path)

        preview = forget_memory(query="忘掉", dry_run=True, path=self.db_path)
        self.assertEqual(preview["count"], 1)
        self.assertIsNone(search_memories("忘掉", path=self.db_path)[0]["deleted_at"])

        deleted = forget_memory(memory_id=saved["id"], dry_run=False, path=self.db_path)
        visible = search_memories("忘掉", path=self.db_path)
        deleted_visible = search_memories("忘掉", include_deleted=True, path=self.db_path)

        self.assertEqual(deleted["count"], 1)
        self.assertEqual(visible, [])
        self.assertIsNotNone(deleted_visible[0]["deleted_at"])


if __name__ == "__main__":
    unittest.main()
