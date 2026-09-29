# Runtime: generic (sequential)

Use when no subagent tool is available, or when unsure.

- Paths: CORE is `<this skill's folder>/../chainsec` resolved to an absolute path.
- **Parallel and one-subagent rows:** do each unit of work yourself, one after another. For each,
  read the filled template and follow it exactly as a subagent would, write its output file(s)
  (the template names them), then move on. Do not carry conclusions from one lens into the next
  beyond what the files say — re-read inputs from disk for each unit (this preserves the
  independence the lenses rely on).
- Verify each output file (exists + JSON parse) before moving on; redo a unit once if invalid,
  then record the phase in `incomplete_phases`.
