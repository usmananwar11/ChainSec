# Runtime: OpenCode

Detected by: a lowercase `task` or `subagent` delegation tool. Skill-output wording
alone does not identify OpenCode; without delegation tools, use `runtimes/generic.md`.

- Paths: the skill tool prints "Base directory for this skill: <abs path>". CORE is that path
  followed by `/../chainsec`, resolved with `cd ... && pwd`.
- **Parallel row:** in ONE message, issue one `task` (or `subagent`) call per unit of work with
  `subagent_type: "general"` and the filled template as the prompt. OpenCode runs them concurrently.
- **One-subagent row:** a single call.
- Then verify outputs exactly as in `runtimes/claude-code.md` (existence + JSON parse, sequential
  retry once, then `incomplete_phases`).
