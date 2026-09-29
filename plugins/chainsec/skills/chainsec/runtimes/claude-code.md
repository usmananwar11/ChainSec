# Runtime: Claude Code

Detected by: the `Agent` tool (older versions: `Task`).

- Paths: this skill's folder is `${CLAUDE_SKILL_DIR}`; CORE is `${CLAUDE_SKILL_DIR}/../chainsec`
  resolved with `cd ... && pwd`. (`${CLAUDE_PLUGIN_ROOT}` also works for plugin installs.)
- **Parallel row:** send ONE message containing one `Agent` call per unit of work (e.g. four calls
  for lenses A–D), `subagent_type: "general-purpose"`, `description` like "ChainSec lens A",
  `prompt` = the filled template. At most 8 calls per message; batch the rest.
- **One-subagent row:** a single `Agent` call with the filled template.
- Wait for every call to return, then check each output file exists and parses. A missing or
  invalid file → do that unit yourself, sequentially, following the same template; if it still
  fails, record the phase in `incomplete_phases`.
- Never paste file contents into prompts; pass paths.
