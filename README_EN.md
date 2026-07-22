<div align="center">

# DNA Memory

**A local-first shared memory layer for Codex, Claude, Hermes, and Obsidian**

[![Stars](https://img.shields.io/github/stars/AIPMAndy/dna-memory?style=social)](https://github.com/AIPMAndy/dna-memory/stargazers)
[![License](https://img.shields.io/github/license/AIPMAndy/dna-memory)](https://github.com/AIPMAndy/dna-memory)
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/)

English | [简体中文](./README.md) | [Quick start](./QUICKSTART.md)

</div>

DNA Memory uses a Markdown/Obsidian directory as the durable source of truth
and SQLite as a disposable, rebuildable index. Codex, Claude Code, Claude
Desktop, and Hermes can use the same stdio MCP server instead of keeping
conflicting long-term memory copies.

It does not equate storing every conversation with learning. Native transcripts
stay in their original clients. DNA Memory stores bounded provenance pointers,
reviewable proposals, and verified reusable conclusions.

## Core philosophy: from conversation data to reusable cognition

> **DNA Memory does not treat storing conversations as forming memories.** It is
> a biomimetically inspired cognitive memory system. Cross-client conversations
> are raw perceptual input; bounded collection, signal extraction, importance and
> confidence weighting, cognitive classification, verification, recall feedback,
> and explicit replacement progressively abstract that data into reusable
> cognition.

It is not another indefinitely growing chat database. Native conversations are
source material; only conclusions that have been filtered, verified, and are
worth reusing in future work become durable memory.

## Core Strategy: Process Memory Before Storing It

DNA Memory is not designed to push more conversation into a database. Its core
is a policy loop that gives an agent a human-memory-inspired way to process
experience. Conversations are treated as raw perceptual input; only signals
that pass the policy gates can become reusable long-term cognition:

1. **Bound perception**: read bounded sources and necessary lifecycle metadata,
   not complete transcripts as durable memory.
2. **Filter signals**: remove operational talk, transient status, credentials,
   and conclusions that cannot be reused.
3. **Weight evidence**: combine importance, confidence, provenance, and later
   usage feedback to decide whether a signal is worth keeping.
4. **Classify cognition**: map signals to preferences, facts, insights,
   decisions, project state, open loops, workflows, and error lessons.
5. **Crystallize after verification**: write only safe, short, traceable,
   verified conclusions to the Markdown truth store.
6. **Recall and learn from feedback**: recall before context-dependent tasks;
   record `useful` or `misleading` only when the result actually affected work.
7. **Evolve and forget**: exact duplicates are collapsed, invalidated cognition
   is replaced through explicit `supersedes`, and stale pointers are retained
   only according to bounded retention rules.

This is an engineering strategy inspired by cognitive processes, not a claim
to reproduce the human brain. The goal is a repeatable
“filter-weight-abstract-verify-recall-correct” loop, rather than an ever-growing
chat archive. DNA Memory should be evaluated by whether high-quality cognition
is reused correctly, not by how much text it stores.

```text
raw conversations
  -> bounded collection and signal extraction
  -> importance, confidence, and usage-feedback weighting
  -> cognitive classification
  -> verified crystallization into durable cognition
  -> task-focused recall
  -> useful / misleading feedback and supersedes evolution
```

The current implementation organizes durable cognition into four groups and
eight memory types:

| Cognitive model | Memory types | Purpose |
|---|---|---|
| Individual tendencies | `preference` | Stable preferences and collaboration habits |
| Facts and insights | `fact`, `insight` | Verified facts and knowledge abstracted from them |
| Decisions and state | `decision`, `project_state`, `open_loop` | Rationale, current state, and unresolved work |
| Procedures and experience | `workflow`, `error_lesson` | Reusable workflows and verified lessons from failure |

Biomimetics is a design inspiration here, not a claim to replicate the human
brain. DNA Memory's value is not how many conversations it stores, but how much
high-quality cognition it forms and whether that cognition is accurately
recalled and effectively reused in later decisions.

## Safety model

- Markdown is durable truth; SQLite is search, queue, and telemetry state.
- `memory_remember` stores concise conclusions, not transcripts.
- Native importers retain IDs, paths, hashes, offsets, and counts by default.
- Automatic extraction produces at most three candidates per session and 800
  characters per summary.
- Credential-like content is rejected.
- Cloud-only Claude Desktop chats require explicit MCP writeback when no stable
  local transcript source is available.
- Memory failure never blocks the primary task.

## Install

```bash
git clone https://github.com/AIPMAndy/dna-memory.git \
  "$HOME/.local/share/dna-memory/app"
cd "$HOME/.local/share/dna-memory/app"

python3 -m venv "$HOME/.local/share/dna-memory/mcp-venv"
"$HOME/.local/share/dna-memory/mcp-venv/bin/pip" install \
  -r requirements-mcp.txt

mkdir -p "$HOME/.config/dna-memory" "$HOME/Documents/DNA-Memory-Vault/Memory"
cp docs/profiles/profile.example.json \
  "$HOME/.config/dna-memory/profile.json"
```

The profile stays outside the repository. Adjust the vault and platform Skill
roots, then verify the store:

```bash
export DNA_MEMORY_PROFILE="$HOME/.config/dna-memory/profile.json"
python3 dna.py memory status --json
python3 dna.py memory reindex --json
```

## Connect Codex, Claude Code, and Hermes

```bash
ROOT="$HOME/.local/share/dna-memory/app"
PYTHON="$HOME/.local/share/dna-memory/mcp-venv/bin/python"
PROFILE="$HOME/.config/dna-memory/profile.json"

codex mcp add dna-memory \
  --env "DNA_MEMORY_PROFILE=$PROFILE" \
  -- "$PYTHON" "$ROOT/scripts/memory_mcp.py"

claude mcp add --scope user dna-memory \
  -e "DNA_MEMORY_PROFILE=$PROFILE" \
  -- "$PYTHON" "$ROOT/scripts/memory_mcp.py"

hermes mcp add dna-memory \
  --command "$PYTHON" \
  --env "DNA_MEMORY_PROFILE=$PROFILE" \
  --args "$ROOT/scripts/memory_mcp.py"
```

Verify runtime connectivity, not only configuration text:

```bash
codex mcp get dna-memory
claude mcp get dna-memory
hermes mcp test dna-memory
```

Claude Desktop uses `mcpServers` with absolute paths. See
[client setup](docs/mcp-and-client-adapters.md) for migration, backup, hooks,
importers, and rollback.

## MCP tools

| Tool | Purpose |
|---|---|
| `memory_recall` | Recall active memories for a focused query |
| `memory_get` | Fetch one memory and its replacement relationships |
| `memory_remember` | Write a verified durable conclusion |
| `memory_feedback` | Record `useful` or `misleading` recall feedback |
| `memory_close_session` | Store bounded session provenance |
| `memory_status` | Inspect truth and index state |
| `memory_reindex` | Rebuild SQLite from Markdown |

Distribute the bundled [dna-memory-loop](skills/dna-memory-loop/SKILL.md) to
each client. It establishes the same behavior everywhere: recall before
context-dependent work, give feedback only for used results, and write back
only after verification.

## Operations

```bash
python3 dna.py memory status --json
python3 dna.py memory coverage --json
python3 dna.py memory value --json
python3 dna.py memory reindex --json
python3 dna.py memory maintain daily --json
python3 dna.py memory maintain weekly --json
python3 dna.py memory maintain monthly --json
```

`memory value` separates reviewable `backlog.reviewable_proposals` from
provenance and lifecycle events. `backlog.pending` is only a compatibility
alias for `total_pending`; it is not the number of memories awaiting review.
Per-client `recall_hits` and `recall_share` show active-recall adoption across
Codex, Claude, and Hermes. Recall share is not a quality score.

In daily maintenance results, `crystallized` counts newly created durable
memories and `deduplicated` counts candidates that matched an active memory
with the same type and normalized summary. Duplicate candidates do not create
another Markdown page; their new sources and clients are merged into the
existing provenance fields. Deduplication is exact after normalization, not a
fuzzy similarity merge.

When a new verified fact invalidates an older one, pass exact old memory IDs in
`supersedes`. Old Markdown remains available as history, while default recall
returns active conclusions only. DNA Memory never infers replacement from type
or project alone.

## Bounded native import

```bash
python3 scripts/import_codex_rollouts.py
python3 scripts/import_claudian_sessions.py
python3 scripts/import_claude_desktop_sessions.py
python3 scripts/import_hermes_sessions.py
python3 scripts/import_native_history.py
```

Importers are incremental and idempotent. Ordinary events remain provenance
pointers. Explicit `DNA_MEMORY_PROPOSAL {JSON}` markers and bounded signal
extraction create review candidates; daily maintenance still applies type,
sensitivity, capacity, and deduplication gates.

After changing native extraction rules, backtest the last seven days in a
separate empty database before bounded production re-extraction. The importer
emits aggregate metrics only, and automatic results remain reviewed
`memory_proposal` events rather than direct long-term memories:

```bash
python3 -m scripts.import_native_history --backtest-days 7 \
  --backtest-db /tmp/dna-memory-backtest.db
python3 -m scripts.import_native_history --reextract-days 7
```

Proceed only when manual sampling finds at most 10% false positives and zero
sensitive leakage. Daily maintenance remains the crystallization gate.

Capture is not the same as durable learning. Evaluate both capture coverage and
the number of verified memories that are later recalled and marked useful.

## Shared Skill management

```bash
cp assets/skills.example.json "$HOME/.config/dna-memory/skills.json"
python3 dna.py skills inventory --json
python3 dna.py skills doctor --json
python3 dna.py skills sync --json
python3 dna.py skills sync --apply --json
```

The registry grants distribution authority only for named Skills. Unregistered
platform-specific Skills are never deleted or overwritten. `sync` is a dry run
unless `--apply` is present.

## Public release safety

Runtime profiles, databases, native sessions, memory JSON, private Skills, and
deployment notes are excluded from source control. Run this before publishing:

```bash
python3 scripts/check_public_safety.py
```

If a credential was ever committed, deleting the current file is insufficient:
revoke the credential and clean the Git history.

## Validate

```bash
python3 -m pytest -q
python3 -m compileall -q dna.py dna scripts tests
python3 scripts/check_public_safety.py
git diff --check
```

## License

[MIT](LICENSE)
