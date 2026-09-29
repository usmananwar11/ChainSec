# Runtime: Codex

Detected by: a sub-agent / delegation tool in your tool list (Codex only delegates when a skill or
the user asks — this skill is asking).

- Paths: resolve relative paths against the folder containing this SKILL.md; CORE is
  `<that folder>/../chainsec` resolved with `cd ... && pwd`.
- **Parallel row:** spawn one sub-agent per unit of work with the filled template as its task,
  all before waiting on any of them.
- **One-subagent row:** spawn one sub-agent.
- No sub-agent tool available → follow `runtimes/generic.md`.
- Verify outputs as in `runtimes/claude-code.md`.

Status: tool names unverified on Codex (no local install during v0.1 smoke tests).
