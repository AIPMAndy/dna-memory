# Security and privacy / 安全与隐私

DNA Memory is a **local-first** memory system. The canonical current entry point
is `skills/dna-memory-loop/SKILL.md`; the shared-memory MCP and Markdown vault
workflows are documented in `README.md`.

## Security review: SkillsCat legacy report (2026-11-14)

The [SkillsCat listing](https://skills.cat/skills/aipmandy/dna-memory)
shows an **AI scan: High** for three legacy Python scripts and
**VirusTotal: Low**. The listing's older three-layer-memory documentation
does not describe the current shared-memory MCP architecture. A scanner label
is a finding to investigate, not proof of exfiltration or compromise.

| Scanned component | Evidence in the repository | Remediation |
| --- | --- | --- |
| `scripts/advanced_recall.py` | Local SQLite query; no network request in this module. The old CLI echoed memory contents. | CLI hides raw memory text by default; `--show-content` is an explicit opt-in for a trusted terminal. The callable search API still returns requested memory data. |
| `scripts/dna_memory_daemon.py` | `subprocess` launches fixed, local `evolve.py` actions (`reflect` or `decay`) and the daemon itself; no `shell=True` found in these paths. Older logging copied raw command output. | Explicit action allowlist, local `sys.executable`, `shell=False`, `stdin=DEVNULL`, log output suppression, private (0600) PID/log files, reject symlink destinations. |
| `scripts/reflect_pending.py` | Old script promoted unverified pending content automatically from a shared `/tmp` path. The subprocess used `shell=False`, but automated promotion violated the verification boundary. | Converted into a **read-only** review utility; it never runs a child process, prints private content, or auto-writes memories. Requires an owned private regular input file with bounded size. |

Scope: these claims cover the listed scripts at the reviewed commit, **not**
every installation or every third-party copy. No observed network exfiltration
in the reviewed scripts is **not** a guarantee that every deployment is safe.

## Secure usage

- Keep the Markdown vault, SQLite index, profile and backups **outside** the Git
  repository. Use per-user file permissions, restrict backups and review
  sharing settings before synchronizing through a third-party cloud.
- Treat imported conversations and candidate memories as untrusted input.
  Never automatically promote candidates solely by increasing a confidence
  number. Verify source, relevance and the absence of private credentials
  before calling `memory_remember`.
- Avoid passing credentials, access tokens, private keys, raw transcripts or
  large logs into persistent memory. The maintained MCP path applies
  validation and bounded-content policy; use that path instead of legacy
  scripts for new deployments.
- Do not run the daemon with elevated privileges. Its legacy log/PID defaults
  remain under `/tmp` for compatibility, but files are now created with
  private permissions and symlink destinations are rejected. For new runs,
  prefer `DNA_MEMORY_LOG_FILE` and `DNA_MEMORY_PID_FILE` under a
  user-owned private directory.
- CLI command `advanced_recall.py --show-content` can expose stored data to
  terminal captures. Use it only in a trusted environment.
- If a key was ever committed or logged, deleting its copy is insufficient;
  rotate/revoke it and investigate relevant history and logs.

## Validate

```bash
python3 -m pytest -q tests/test_legacy_security_hardening.py
python3 -m pytest -q
python3 -m compileall -q dna.py dna scripts tests
python3 scripts/check_public_safety.py
```

CI is not a substitute for inspecting the running system or for a fresh
third-party registry scan. Check whether the current SkillsCat page has
re-indexed before claiming its **High** label has been cleared.

## Reporting security issues

Please use the repository's GitHub Security advisory/reporting feature where
available; for sensitive disclosures, avoid opening public issues containing
credentials, private memory or exploit details. Public PRs may discuss fixes
without exposing confidential data.
