<div align="center">

# 🧬 DNA Memory

**Make AI Agents learn, reinforce, forget, and generalize like a human brain**

[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![OpenClaw](https://img.shields.io/badge/Built%20for-OpenClaw-purple)](https://github.com/openclaw/openclaw)

**English** | [简体中文](./README.md)

</div>

---

> Most AI memory systems only solve **storage**.
> **DNA Memory** is about how agents actually **learn and evolve**.

It is not just a memory store. It is a memory evolution system with:
- **3-layer memory architecture**
- **reinforcement and decay**
- **reflection (`reflect`)**
- **promotion to long-term memory (`promote`)**
- **duplicate cleanup (`dedupe`)**
- **FTS5-powered recall search**
- **background daemon maintenance**

---

## 🆚 Why not just use a normal memory store?

| Capability | Mem0 | Zep | LangChain Memory | **DNA Memory** |
|------------|:----:|:---:|:----------------:|:--------------:|
| Basic storage | ✅ | ✅ | ✅ | ✅ |
| Vector / semantic retrieval | ✅ | ✅ | ✅ | ⚠️ extensible |
| Multi-layer architecture | ❌ | ⚠️ | ❌ | ✅ **working / short / long** |
| Active forgetting | ❌ | ❌ | ❌ | ✅ |
| Reflection loop | ❌ | ❌ | ❌ | ✅ |
| Pattern extraction | ❌ | ❌ | ❌ | ✅ |
| Long-term promotion | ❌ | ❌ | ❌ | ✅ |
| Local-first / minimal core deps | ❌ | ❌ | ❌ | ✅ |
| Built for agent workflows | ⚠️ | ⚠️ | ⚠️ | ✅ |

**Positioning in one sentence:**

> DNA Memory helps AI agents not only remember, but also reinforce, forget, summarize, and evolve like a real cognitive system.

---

## 🚀 Quick Start in 30 Seconds

```bash
# 1) Clone into your OpenClaw skills directory
git clone https://github.com/AIPMAndy/dna-memory.git ~/.openclaw/skills/dna-memory

# 2) Remember one preference
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py remember "The user prefers concise and direct responses" -t preference -i 0.9

# 3) Recall related memories
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py recall "concise direct"

# 4) Inspect stats
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py stats
```

**Why it is practical:**
- core features run on Python + SQLite
- no external database required
- local-first by default
- ideal for personal assistants, local agents, and autonomous workflows

---

## ✨ Core Capabilities

### 1. Three-layer memory architecture

```text
Working Memory
  ↓ filter
Short-term Memory
  ↓ consolidate / promote
Long-term Memory
```

| Layer | Role | Typical content |
|------|------|-----------------|
| Working | temporary session context | current task state, fresh facts |
| Short-term | recent important information | preferences, lessons, recent errors |
| Long-term | stable knowledge and patterns | rules, skills, persistent preferences |

### 2. Reinforcement and forgetting

- **used often → higher weight**
- **unused for a long time → decay**
- **low-weight memories → removable**
- **stable high-value memories → promoted to long-term memory**

### 3. Reflection (`reflect`)

`reflect` does two things:
- extracts recurring patterns from recent high-weight memories
- promotes stable short-term memories into long-term memory

### 4. Better recall search

Current recall supports:
- **multi-keyword AND search**
- **type filters** like `type:error` / `type:skill`
- **SQLite FTS5 full-text search**
- automatic fallback to LIKE search if FTS5 is unavailable

Examples:

```bash
python3 scripts/evolve.py recall "feishu api"
python3 scripts/evolve.py recall "type:error github"
python3 scripts/evolve.py recall "user preference concise"
```

### 5. Background maintenance daemon

The daemon can automatically run:
- `reflect`
- `decay`
- throttled maintenance so the same batch is not repeatedly summarized

It can also be registered with **macOS launchd** for auto-start on boot.

---

## 📦 Actual current architecture

```text
dna-memory/
├── scripts/
│   ├── evolve.py              # core CLI: remember / recall / stats / reflect / dedupe ...
│   ├── dna_memory_daemon.py   # background maintenance daemon
│   ├── semantic_search.py     # experimental semantic search module
│   ├── analyze.py
│   ├── api.py
│   ├── autocollect.py
│   ├── backup.py
│   ├── cli.py
│   ├── detailed_stats.py
│   ├── knowme_link.py
│   ├── reminder.py
│   ├── trigger.py
│   └── visualize.py
├── memory/
│   ├── memory.db              # SQLite primary store (memories + operations)
│   └── working.json           # working memory
├── assets/
│   └── config.json            # daemon / decay config
├── README.md
├── README_EN.md
└── SKILL.md
```

> Note: `memory/*.db` should not be committed. The repo now ignores real memory database files by default.

---

## 🧪 Core Commands

### Remember

```bash
python3 scripts/evolve.py remember "Andy prefers concise and direct responses" -t preference -i 0.95
```

### Recall

```bash
python3 scripts/evolve.py recall "concise response"
python3 scripts/evolve.py recall "type:skill feishu"
```

### Stats

```bash
python3 scripts/evolve.py stats
```

### Reflect

```bash
python3 scripts/evolve.py reflect
```

### Promote

```bash
python3 scripts/evolve.py promote --id 12
```

### Dedupe

```bash
python3 scripts/evolve.py dedupe
```

### Daemon

```bash
# start
python3 scripts/dna_memory_daemon.py start

# check status
python3 scripts/dna_memory_daemon.py status

# stop
python3 scripts/dna_memory_daemon.py stop
```

---

## ⚙️ Use Cases

### 1. Personal AI assistants
- remember user preferences
- develop a stable collaboration style over time
- learn from mistakes instead of repeating them

### 2. Agent workflow orchestration
- turn finished tasks into reusable skills
- store failure cases as error memories
- extract patterns from long-running work

### 3. AI products with personalization
- accumulate user profiles
- track behavioral patterns
- build long-term personalization

### 4. Self-improving agent systems
- works well with OpenClaw, self-improving-agent, and custom agent stacks
- turns operational experience into reusable memory assets

---

## 🧭 Recommended Workflow

```text
Receive task
  ↓
Recall related memories
  ↓
Execute
  ↓
Remember new preferences / skills / errors
  ↓
Reflect recurring patterns
  ↓
Promote into long-term memory
```

This workflow is especially useful when:
- the user corrects the agent
- a new preference is learned
- an API/tool fails
- a long task finishes
- a repeatable pattern appears

---

## 🗺️ Roadmap

- [x] SQLite single-store refactor
- [x] remember / recall / reflect / promote / dedupe CLI
- [x] daemon for automatic reflect / decay
- [x] FTS5-based recall search
- [x] launchd auto-start setup
- [ ] better Chinese tokenization and ranking
- [ ] real embedding-based semantic retrieval
- [ ] stronger memory graph visualization
- [ ] more complete import / export / migration tooling
- [ ] shared memory spaces for multi-agent systems

---

## 🤝 Contributing

Issues and PRs are welcome.

High-impact contribution areas:
- recall ranking quality
- Chinese search experience
- pattern extraction quality
- memory visualization
- embedding provider integrations

---

## 👨‍💻 Author

**Andy / AI酋长Andy**  
Ex-Tencent / Baidu AI Product Expert → LLM Unicorn VP → Startup CEO

Focus areas:
- AI agents
- AI commercialization
- memory systems
- human augmentation

GitHub: https://github.com/AIPMAndy

---

## 📄 License

[Apache 2.0](LICENSE)

---

<div align="center">

**If this project helps you, give it a ⭐ Star.**

</div>
