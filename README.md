# AI Relationship Memory for Codex

![Demo](plugins/companion-memory/assets/demo.gif)

AI Relationship Memory is a local-first Codex plugin that gives AI personas a durable, inspectable memory layer. It is designed for relationship-shaped interactions: long-running assistants, companion personas, creative roleplay partners, coaches, tutors, or any agent that should remember preferences, boundaries, shared context, and compact episode summaries without sending that memory to a hosted database.

The project is deliberately boring under the hood: a Codex skill, a small MCP server, and a local SQLite database.

## Why This Exists

Most AI persona projects blur together three things that should stay separate:

- Persona: how the AI should speak and what role it is playing.
- Memory: what the user explicitly allowed it to remember.
- Transcript: everything that happened in chat.

This plugin keeps those layers separate. It defaults to compact, editable memories instead of raw transcript hoarding, excludes sensitive memories from normal recall, and makes forgetting a first-class operation.

## Quick Start

Clone the repository and open it as the current Codex workspace:

```bash
git clone https://github.com/your-name/companion-memory.git
cd companion-memory
```

Restart or reload Codex so it reads the workspace marketplace at:

```text
.agents/plugins/marketplace.json
```

Enable **AI Relationship Memory** in the Codex plugin UI. Then try:

```text
Use my local relationship persona and memories for this conversation.
Remember this preference locally: I prefer concise answers.
List what you remember about me.
Forget the memory about concise answers.
```

The MCP server initializes the SQLite database automatically. You can also check it manually:

```bash
python3 plugins/companion-memory/scripts/init_db.py --show-path --print-persona
```

## Example Prompts

```text
Remember this preference locally: call me Kai.
Remember this boundary: do not store raw transcripts.
Search my relationship memories for nickname.
List what you remember about me.
Show my current relationship persona.
Update the persona tone to warm, direct, and lightly playful.
Save a compact summary of this conversation.
Do not save this message.
Preview forgetting memories about nickname.
Export my local relationship memory.
```

## What It Stores

Memories are stored in `plugins/companion-memory/data/companion_memory.sqlite3`, which is ignored by Git.

Supported memory kinds:

- `profile`: stable facts about the user.
- `preference`: likes, dislikes, names, tone, and communication habits.
- `relationship`: shared rituals, important context, boundaries, and inside references.
- `episode`: compact summaries of meaningful conversations.
- `boundary`: consent rules and topics to avoid.
- `pinned`: high-priority memories that should rank first.

## Privacy Model

- Local-first: the plugin writes to a SQLite database under this workspace.
- No external service: the MCP server does not call network APIs.
- No raw transcript storage by default: compact summaries are preferred.
- Sensitive recall is opt-in: `sensitive` memories are hidden from normal search.
- Forgetting is built in: deletion starts with a dry-run preview, then soft-deletes matching memories.
- User control: users can list, export, and forget stored memories.

Do not store passwords, API keys, government IDs, payment details, or credentials.

## Safety Boundaries

This is a memory layer, not a claim that the AI has a body, independent offline life, or real-world agency. Personas should stay transparent about what is stored, avoid fabricating memories, and avoid encouraging isolation or dependency. For medical, legal, financial, or safety-critical topics, keep the interaction supportive but grounded.

## Repository Layout

```text
.agents/plugins/marketplace.json
plugins/companion-memory/
  .codex-plugin/plugin.json
  .mcp.json
  assets/
  scripts/
  skills/
  tests/
```

## Tests

Run the full local validation suite:

```bash
python3 plugins/companion-memory/scripts/run_checks.py
```

That script validates JSON files, compiles Python sources, runs unit tests, checks the generated demo GIF, and smoke-tests the MCP stdio server.

You can also run only the unit tests:

```bash
python3 -m unittest discover -s plugins/companion-memory/tests
```

## Development

Regenerate the README demo GIF:

```bash
python3 plugins/companion-memory/scripts/generate_demo_gif.py
```

Evaluate plugin quality with Plugin Eval when available:

```bash
node /path/to/plugin-eval/scripts/plugin-eval.js analyze plugins/companion-memory --format markdown
```

## License

MIT
