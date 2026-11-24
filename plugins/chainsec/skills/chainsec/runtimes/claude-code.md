# Runtime: Claude Code

Detected by: an `Agent` tool (older versions: a `Task` tool with a `subagent_type` parameter).

- Paths: this skill's folder is `${CLAUDE_SKILL_DIR}`; CORE is `${CLAUDE_SKILL_DIR}/../chainsec`
  resolved with `cd ... && pwd`. (`${CLAUDE_PLUGIN_ROOT}` also works for plugin installs.)
- **Parallel row:** send ONE message containing one `Agent` call per unit of work (e.g. four calls
  for lenses A–D), `subagent_type: "general-purpose"`, `description` like "ChainSec lens A",
  `prompt` = the filled template. At most 8 calls per message; batch the rest.
- **One-subagent row:** a single `Agent` call with the filled template.
- **Background subagents (newer Claude Code):** if an `Agent` call returns "Async agent launched"
  instead of the subagent's result, the subagent runs in the background. **Do not end your turn
  while any dispatched subagent is unfinished**: in headless runs (`claude -p`) ending the turn ends
  the session and loses the subagents' work. Wait in the same turn with a `Monitor` call whose
  command loops until every expected output file exists (for example
  `until [ -f A/candidates/detect-A.json ] && [ -f A/candidates/detect-B.json ]; do sleep 10; done`),
  or keep doing independent work meanwhile. Continue only when the files are there.
- Wait for every call to return, then check each output file exists and parses. A missing or
  invalid file → do that unit yourself, sequentially, following the same template; if it still
  fails, record the phase in `incomplete_phases`.
- Never paste file contents into prompts; pass paths.
