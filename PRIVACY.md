# Privacy Notes

AI Relationship Memory is designed as a local-first plugin.

## Data Location

The default database path is:

```text
plugins/companion-memory/data/companion_memory.sqlite3
```

The database is ignored by Git. The plugin creates it on first use.

## Data Types

The plugin can store:

- Persona settings.
- User preferences.
- Relationship notes.
- Consent boundaries.
- Compact episode summaries.
- Optional raw exchange records when explicitly enabled.

The default workflow prefers compact summaries over raw transcripts.

## Sensitive Memory

Memories can be marked as `public`, `private`, or `sensitive`.

Normal search excludes `sensitive` memories unless the caller explicitly requests them. This is intended to reduce accidental recall of intimate, health-related, family, identity, or high-risk personal details.

## Forgetting

The forget tool supports a dry-run preview. A confirmed forget operation soft-deletes matching memories by setting `deleted_at`; it does not physically wipe rows from SQLite.

For a hard wipe, delete the local database file:

```bash
rm plugins/companion-memory/data/companion_memory.sqlite3*
```

## What Not To Store

Do not store passwords, API keys, government IDs, payment details, private keys, recovery phrases, or credentials.
