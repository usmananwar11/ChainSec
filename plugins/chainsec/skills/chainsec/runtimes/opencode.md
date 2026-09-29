# Runtime: OpenCode

Detected by: the `task` tool (OpenCode v1) or `subagent` tool (reported rename in v2).

- Paths: the skill tool prints "Base directory for this skill: <abs path>". CORE is that path
  followed by `/../chainsec`, resolved with `cd ... && pwd`.
- **Parallel row:** in ONE message, issue one `task` (or `subagent`) call per unit of work with
  `subagent_type: "general"` and the filled template as the prompt. OpenCode runs them concurrently.
- **One-subagent row:** a single call.
- Then verify outputs exactly as in `runtimes/claude-code.md` (existence + JSON parse, sequential
  retry once, then `incomplete_phases`).
