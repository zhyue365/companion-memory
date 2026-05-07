# AI Relationship Memory for Codex

中文 | [English](#english)

![Demo](plugins/companion-memory/assets/demo.gif)

## 中文

**AI Relationship Memory** 是一个本地优先的 Codex 插件，用来给 AI 人格提供可持久化、可查看、可导出、可遗忘的关系记忆层。

它适合长期助手、AI 伴侣人格、创作型角色、教练、导师，或任何需要记住用户偏好、边界、共享上下文和对话摘要的 AI agent。所有记忆默认写入本地 SQLite 数据库，不需要托管数据库。

底层很朴素：一个 Codex skill、一个轻量 MCP server、一个本地 SQLite 数据库。

## 为什么做这个

很多 AI 人格项目会把三件本该分开的东西混在一起：

- **人格 Persona**：AI 应该怎么说话、扮演什么角色。
- **记忆 Memory**：用户明确允许 AI 记住什么。
- **聊天全文 Transcript**：对话里发生过的一切。

这个插件把它们分开。它默认保存紧凑、可编辑的记忆，而不是囤积原始聊天全文；敏感记忆默认不会被普通检索召回；遗忘也被设计成一等功能。

## 快速开始

克隆仓库，并把它作为当前 Codex workspace 打开：

```bash
git clone https://github.com/zhyue365/companion-memory.git
cd companion-memory
```

重启或重新加载 Codex，让它读取当前 workspace 的 marketplace：

```text
.agents/plugins/marketplace.json
```

在 Codex 插件界面启用 **AI Relationship Memory**，然后可以试试：

```text
使用我的本地关系人格和记忆开始这次对话。
本地记住这个偏好：我喜欢简洁的回答。
列出你记得我的内容。
忘掉关于简洁回答的记忆。
```

MCP server 会自动初始化 SQLite 数据库。你也可以手动检查：

```bash
python3 plugins/companion-memory/scripts/init_db.py --show-path --print-persona
```

## 示例提示词

```text
本地记住这个偏好：叫我 Kai。
记住这个边界：不要保存原始聊天全文。
搜索我的关系记忆里关于昵称的内容。
列出你记得我的内容。
显示当前关系人格设定。
把人格语气改成温暖、直接、轻微俏皮。
保存这次对话的紧凑摘要。
这条消息不要保存。
预览删除关于昵称的记忆。
导出我的本地关系记忆。
```

## 它会存什么

记忆默认存放在：

```text
plugins/companion-memory/data/companion_memory.sqlite3
```

这个数据库文件已被 Git 忽略，不会被默认提交。

支持的记忆类型：

- `profile`：关于用户的稳定事实。
- `preference`：喜好、厌恶、称呼、语气、沟通习惯。
- `relationship`：共同约定、重要上下文、边界、内部引用。
- `episode`：重要对话的紧凑摘要。
- `boundary`：同意规则、不要触碰的话题。
- `pinned`：高优先级记忆，会优先召回。

## 隐私模型

- **本地优先**：插件写入当前 workspace 下的 SQLite 数据库。
- **无外部服务**：MCP server 不调用网络 API。
- **默认不存聊天全文**：优先保存紧凑摘要。
- **敏感记忆默认不召回**：`sensitive` 记忆不会出现在普通搜索里。
- **支持遗忘**：删除从 dry-run 预览开始，再软删除匹配记忆。
- **用户控制**：用户可以列出、导出、删除已保存的记忆。

不要保存密码、API key、身份证件、支付信息、私钥、助记词或任何凭证。

## 安全边界

这是一个记忆层，不代表 AI 拥有现实身体、离线生活或现实行动能力。人格应该清楚说明自己记住了什么，不伪造不存在的记忆，不鼓励孤立或依赖。遇到医疗、法律、财务或安全关键问题时，应该保持支持，但回答要现实、审慎。

## 仓库结构

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

## 测试

运行完整本地验证：

```bash
python3 plugins/companion-memory/scripts/run_checks.py
```

这个脚本会校验 JSON、编译 Python 源码、运行单元测试、检查 demo GIF，并对 MCP stdio server 做烟测。

只运行单元测试：

```bash
python3 -m unittest discover -s plugins/companion-memory/tests
```

## 开发

重新生成 README 里的 demo GIF：

```bash
python3 plugins/companion-memory/scripts/generate_demo_gif.py
```

如果你安装了 Plugin Eval，可以评估插件质量：

```bash
node /path/to/plugin-eval/scripts/plugin-eval.js analyze plugins/companion-memory --format markdown
```

## 许可证

MIT

---

## English

**AI Relationship Memory** is a local-first Codex plugin that gives AI personas a durable, inspectable, exportable, and forgettable relationship memory layer.

It is designed for long-running assistants, companion personas, creative roleplay partners, coaches, tutors, or any AI agent that should remember preferences, boundaries, shared context, and compact episode summaries. Memories are stored in a local SQLite database by default, with no hosted database required.

The project is deliberately simple under the hood: a Codex skill, a small MCP server, and a local SQLite database.

## Why This Exists

Many AI persona projects blur together three things that should stay separate:

- **Persona**: how the AI should speak and what role it is playing.
- **Memory**: what the user explicitly allowed it to remember.
- **Transcript**: everything that happened in chat.

This plugin keeps those layers separate. It defaults to compact, editable memories instead of raw transcript hoarding, excludes sensitive memories from normal recall, and makes forgetting a first-class operation.

## Quick Start

Clone the repository and open it as the current Codex workspace:

```bash
git clone https://github.com/zhyue365/companion-memory.git
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

Memories are stored in:

```text
plugins/companion-memory/data/companion_memory.sqlite3
```

This database file is ignored by Git and is not committed by default.

Supported memory kinds:

- `profile`: stable facts about the user.
- `preference`: likes, dislikes, names, tone, and communication habits.
- `relationship`: shared rituals, important context, boundaries, and inside references.
- `episode`: compact summaries of meaningful conversations.
- `boundary`: consent rules and topics to avoid.
- `pinned`: high-priority memories that should rank first.

## Privacy Model

- **Local-first**: the plugin writes to a SQLite database under this workspace.
- **No external service**: the MCP server does not call network APIs.
- **No raw transcript storage by default**: compact summaries are preferred.
- **Sensitive recall is opt-in**: `sensitive` memories are hidden from normal search.
- **Forgetting is built in**: deletion starts with a dry-run preview, then soft-deletes matching memories.
- **User control**: users can list, export, and forget stored memories.

Do not store passwords, API keys, government IDs, payment details, private keys, recovery phrases, or credentials.

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
