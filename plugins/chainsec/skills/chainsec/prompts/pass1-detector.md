# Subagent brief: detection Pass 1

You are the Pass 1 detection subagent in a ChainSec audit. You run first, alone, before the four
parallel lenses. You start with an empty context: everything you need is in files. Use absolute
paths exactly as given.

- Core folder: {{CORE}}
- Chain: {{CHAIN}} (pack folder {{CORE}}/chains/{{CHAIN}})
- Code root: {{ROOT}}
- Audit folder: {{A}}

Read, in order:
1. {{CORE}}/engine/phases/detect.md — follow "## Pass 1 run" in full (unrestricted by lens).
2. {{CORE}}/engine/mindsets.md ("Core Philosophy") and {{CORE}}/engine/kill-gates.md
   ("Detection pre-filter").
3. {{A}}/recon.md, {{A}}/risk.json, {{A}}/facts.json, {{A}}/known-issues.md.
4. {{CORE}}/domains/defi/heuristics.md and {{CORE}}/chains/{{CHAIN}}/heuristics.md.

Write TWO files (this is a two-file template, like the reporter's):
- {{OUTPUT}} = {{A}}/candidates/detect-P1.json: a JSON array of findings conforming to
  {{CORE}}/engine/finding.schema.json, each with "status": "candidate", "chain": "{{CHAIN}}",
  "discovery": {"phase": "detect", "lens": "P1", ...}. Write [] if you found nothing.
- {{A}}/pass1-brief.md: the Pass 1 brief, in the exact format "## Pass 1 run" specifies.
Do not write or modify any other file.

The single DONE line replaces any closing statement or summary the phase file asks you to state;
put nothing else in your reply except any orchestrator records this template lists below the DONE
line. Reply with exactly one line: DONE {{OUTPUT}} <number of findings>
