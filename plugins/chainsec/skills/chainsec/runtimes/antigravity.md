# Runtime: Antigravity

Detected by: the `invoke_subagent` tool.

- Paths: resolve relative paths against this skill's folder; CORE is `<skill folder>/../chainsec`.
- **Parallel row:** call `invoke_subagent` once per unit of work (they run concurrently), each
  with the filled template as its task. Use the general-purpose/"self" agent type.
- **One-subagent row:** one `invoke_subagent` call.
- Verify outputs as in `runtimes/claude-code.md`.
