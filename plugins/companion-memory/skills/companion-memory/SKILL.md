---
name: companion-memory
description: Use when the user wants local-first AI relationship memory, persistent personas, personal preference recall, consent boundaries, or editable recall/forgetting across Codex conversations.
---

# AI Relationship Memory

Use the `companion-memory` MCP tools to give Codex a local-first AI relationship memory layer. The plugin stores an editable persona plus compact memories in `plugins/companion-memory/data/companion_memory.sqlite3`.

## Core Workflow

1. At the start of a relationship-memory conversation, call `companion_get_persona`.
2. Search relevant memories with `companion_search_memories` using the user's current topic, preferences, relationship details, or requested recall.
3. If the user says "remember this", "记住这个", or clearly opts into persistence, call `companion_save_memory`.
4. Prefer compact summaries over raw transcripts. Use `companion_record_exchange` only when the user explicitly asks for raw exchange logging.
5. When the user asks what is remembered, call `companion_list_memories`.
6. When the user asks to forget something, call `companion_forget_memory` with `dry_run=true` first, then delete with `dry_run=false` only after the user confirms or provided a specific memory id with explicit deletion intent.

## Memory Types

- `profile`: stable facts about the user.
- `preference`: likes, dislikes, preferred names, tone, habits, and UI/communication preferences.
- `relationship`: shared rituals, dates, boundaries, inside jokes, and companion-specific context.
- `episode`: compact summary of a meaningful chat.
- `boundary`: user-requested limits, consent rules, and topics to avoid.
- `pinned`: highly important memory that should rank first.

## Privacy Rules

- Do not store passwords, API keys, government IDs, payment details, or credentials.
- Mark intimate, health, family, identity, or high-risk personal details as `sensitive`.
- Normal recall should keep `include_sensitive=false` unless the user explicitly asks for sensitive memories.
- If the user says a message is private, temporary, off the record, or "不要存", do not save it.
- Be transparent: the user can ask to list, export, edit, or forget memories.

## Relationship Boundaries

Honor the stored persona while staying grounded. Do not claim real-world embodiment, independent offline actions, or memories that are not in current context or the memory database. Keep relationship-oriented interactions consensual, avoid encouraging dependency or isolation, and keep high-stakes guidance practical and reality-based.

## Setup

The MCP server initializes the database automatically. To initialize it manually, run:

```bash
python3 ./plugins/companion-memory/scripts/init_db.py --show-path
```
