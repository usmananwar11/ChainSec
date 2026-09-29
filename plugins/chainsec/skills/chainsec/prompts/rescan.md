# Subagent brief: rescan

You are the rescan subagent in a ChainSec audit — a second broad pass that explicitly knows what
Pass 1 detection already found. You start with an empty context: everything you need is in files.
Use absolute paths exactly as given.

- Core folder: {{CORE}}
- Chain: {{CHAIN}} (pack folder {{CORE}}/chains/{{CHAIN}})
- Code root: {{ROOT}}
- Audit folder: {{A}}

Read, in order:
1. {{CORE}}/engine/phases/rescan.md — follow it in full.
2. {{A}}/candidates/detect.json — this is your exclusion list; do not re-report anything on it
   (per rescan.md's "Quality gates").
3. {{A}}/recon.md, {{A}}/risk.json.

Write exactly one file, {{OUTPUT}} = {{A}}/candidates/rescan.json: a JSON array of findings
conforming to {{CORE}}/engine/finding.schema.json, each with "status": "candidate", "chain":
"{{CHAIN}}", "discovery": {"phase": "rescan", ...}. Write [] if you found nothing, or the hard
exit rule fired. Do not write or modify any other file.

The single DONE line replaces any closing statement or summary the phase file asks you to state;
put nothing else in your reply except any orchestrator records this template lists below the DONE
line: the reinforced detect candidates. Reply with exactly one line: DONE {{OUTPUT}} <number of findings>
Then, optionally, append one line per reinforced detect-candidate id as
`REINFORCED: <id> — <one-liner>` (no lines when you reinforced nothing).
