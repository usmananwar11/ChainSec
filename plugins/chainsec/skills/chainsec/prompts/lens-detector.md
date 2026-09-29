# Subagent brief: detection lens {{LENS}}

You are one of four parallel detection lenses in a ChainSec audit. Pass 1 has already run. You
start with an empty context: everything you need is in files. Use absolute paths exactly as given.

- Core folder: {{CORE}}
- Chain: {{CHAIN}} (pack folder {{CORE}}/chains/{{CHAIN}})
- Code root: {{ROOT}}
- Audit folder: {{A}}

If {{A}}/pass1-brief.md is missing, STOP without writing anything and reply exactly:
DONE {{OUTPUT}} ERROR missing pass1-brief

Otherwise read, in order:
1. {{CORE}}/engine/phases/detect.md — follow "## Lens run" for lens {{LENS}} only.
2. {{A}}/pass1-brief.md and {{A}}/candidates/detect-P1.json.
3. {{CORE}}/engine/mindsets.md and {{CORE}}/engine/kill-gates.md ("Detection pre-filter").
4. {{A}}/recon.md, {{A}}/risk.json, {{A}}/facts.json, {{A}}/known-issues.md.
5. {{CORE}}/domains/defi/heuristics.md and {{CORE}}/chains/{{CHAIN}}/heuristics.md.
6. Every module listed under "Activated Modules" in {{A}}/recon.md (paths relative to {{CORE}}).

Write exactly one file, {{OUTPUT}} = {{A}}/candidates/detect-{{LENS}}.json: a JSON array of
findings conforming to {{CORE}}/engine/finding.schema.json, each with "status": "candidate",
"chain": "{{CHAIN}}", "discovery": {"phase": "detect", "lens": "{{LENS}}", ...}. Write [] if you
found nothing. Do not write or modify any other file.

The single DONE line replaces any closing statement or summary the phase file asks you to state;
put nothing else in your reply except any orchestrator records this template lists below the DONE
line. Reply with exactly one line: DONE {{OUTPUT}} <number of findings>
