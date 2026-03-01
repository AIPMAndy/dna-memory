<div align="center">

# 🧬 DNA Memory

**Make AI Agents Learn and Grow Like a Human Brain**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-purple.svg)](https://openclaw.ai)
[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory)

English | [简体中文](README.md)

</div>

---

The human brain isn't a hard drive. It forgets, generalizes, and reflects.

Existing AI memory solutions only solve "storage" — DNA Memory solves **"learning"**.

## 🆚 Why DNA Memory?

| Capability | Mem0 | Zep | LangChain Memory | **DNA Memory** |
|------------|:----:|:---:|:----------------:|:--------------:|
| Basic Storage | ✅ | ✅ | ✅ | ✅ |
| Vector Search | ✅ | ✅ | ✅ | ✅ |
| Multi-layer Architecture | ❌ | ⚠️ | ❌ | ✅ **3 layers** |
| Active Forgetting | ❌ | ❌ | ❌ | ✅ |
| Auto Pattern Extraction | ❌ | ❌ | ❌ | ✅ |
| Reflection Loop | ❌ | ❌ | ❌ | ✅ |
| Knowledge Graph | ❌ | ⚠️ | ❌ | ✅ |
| Dynamic Weighting | ❌ | ❌ | ❌ | ✅ |
| Zero-dependency Local | ❌ | ❌ | ❌ | ✅ |

**DNA Memory simulates how the human brain actually works:**

- 📉 **Forgetting** — Unimportant info naturally fades away
- 📈 **Reinforcement** — Frequently used memories get stronger
- 🔄 **Generalization** — Extract patterns from scattered info
- 🧠 **Reflection** — Periodically review and optimize
- 🕸️ **Association** — Build knowledge graphs between memories

## 🚀 Quick Start (30 seconds)

```bash
# 1. Clone
git clone https://github.com/AIPMAndy/dna-memory.git ~/.openclaw/skills/dna-memory

# 2. Remember something
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py remember "I prefer concise responses" -t preference -i 0.9

# 3. Check stats
python3 ~/.openclaw/skills/dna-memory/scripts/evolve.py stats
```

**Zero dependencies** — Just Python 3.8+, no packages to install.

## 📖 Core Commands

```bash
# Remember
evolve.py remember "content" -t type -i importance(0-1)

# Recall
evolve.py recall "keyword"

# Reflect (extract patterns)
evolve.py reflect

# Decay (forget low-weight memories)
evolve.py decay

# Link memories
evolve.py link mem_001 mem_002 -r "causal"

# List / Delete / Export
evolve.py list [-L for long-term]
evolve.py delete mem_xxx
evolve.py export -o backup.json
```

## 🏗️ Three-Layer Architecture

```
┌─────────────────────────────────────────────┐
│  🔴 Working Memory                           │
│     Current session temp info                │
│     → Auto-filtered after session ends       │
└─────────────────┬───────────────────────────┘
                  ↓ Filter
┌─────────────────────────────────────────────┐
│  🟡 Short-term Memory                        │
│     Last 7 days important info               │
│     → Decays over time if unused             │
└─────────────────┬───────────────────────────┘
                  ↓ Consolidate
┌─────────────────────────────────────────────┐
│  🟢 Long-term Memory                         │
│     Verified persistent knowledge            │
│     → Extracted patterns, high-weight items  │
└─────────────────────────────────────────────┘
```

## 🔄 Memory Evolution

| Event | Weight Change |
|-------|:-------------:|
| Accessed/Used | **+0.1** |
| User Confirmed | **+0.2** |
| User Corrected | Mark as error |
| 7 days unused | **-0.1** |
| Linked to others | **+0.05** |
| Generalized to pattern | **Promoted** |

## 💡 Use Cases

- **Personal AI Assistant** — Remembers preferences, gets smarter over time
- **Knowledge Workers** — Accumulates domain expertise
- **Customer Service Agent** — Learns customer patterns
- **Autonomous Agents** — Learns from mistakes, self-improves
- **Agent Developers** — Add memory evolution to your agents

## 📄 License

[Apache 2.0](LICENSE)

---

<div align="center">

## 👨‍💻 Author

**AI酋长Andy (Andy the AI Chief)**

Ex-Tencent/Baidu AI Product Expert → LLM Unicorn VP → Startup CEO

Focused on AI commercialization, helping founders amplify business with AI

[![GitHub](https://img.shields.io/badge/GitHub-AIPMAndy-181717?logo=github)](https://github.com/AIPMAndy)
[![Twitter](https://img.shields.io/badge/Twitter-@pmai_andy-1DA1F2?logo=twitter&logoColor=white)](https://twitter.com/pmai_andy)

---

**If this helps you, please give it a ⭐ Star!**

</div>
