---
name: dna-memory-loop
description: Use when a substantive task may depend on prior decisions, preferences, project state, workflows, errors, or open loops, or when a verified result should become reusable across Codex, Claude, Hermes, and an Obsidian vault.
---

# DNA Memory Loop

Use DNA Memory as the cross-client long-term truth. Treat each client's native
history as a transcript source, not as a competing durable memory store.

## Before substantive work

1. Extract one to four distinctive terms from the request, project, error, or expected result.
2. Call `memory_recall` separately for each term. Include the real client and session ID when available.
3. Deduplicate by memory ID. Inject at most five memories and about 2,000 tokens total.
4. Use only relevant results. Current files, processes, remote state, and tests override stale memory.

Skip recall for simple, self-contained work such as translation, current time,
one-step formatting, or a command that does not depend on history.

## Feedback

- Call `memory_feedback(..., outcome="useful")` only when a recalled memory changed or confirmed the work.
- Use `outcome="misleading"` when a memory sent the task in the wrong direction.
- Do not submit feedback for a result that was displayed but not used.

## After verification

Call `memory_remember` only for a durable preference, decision with rationale,
fact, insight, reusable workflow, proven error lesson, project state, or open
loop. Write a compact conclusion with bounded source pointers. Never store a
full transcript, credentials, raw prompts, or large tool output.

When current evidence invalidates an older conclusion, read the older memory
IDs and pass only those exact IDs through `supersedes`. Never infer replacement
from project or type alone.

When a native session has a stable source pointer, call `memory_close_session`
with bounded metadata. This records provenance, not transcript content.

## Bounded proposals

If the client cannot directly call `memory_remember`, it may append up to three
reviewable candidates to its final message:

`DNA_MEMORY_PROPOSAL {"type":"decision|fact|workflow|preference|insight|error_lesson|project_state|open_loop","summary":"verified reusable conclusion","confidence":"high|medium|low","importance":0.0}`

Keep each summary under 800 characters. A proposal remains a candidate until
maintenance applies type, sensitivity, capacity, and deduplication checks.

## Degraded mode

Memory failure must not block the main task. Continue from current evidence,
report the degraded capability once, and never fabricate recall, feedback, or
writeback success.
