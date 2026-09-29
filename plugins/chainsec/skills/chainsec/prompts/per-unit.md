# Subagent brief: per-unit cluster {{CLUSTER_N}}

You analyze ONE cluster in a ChainSec audit: cluster {{CLUSTER_N}}, units {{CLUSTER_UNITS}}. You
start with an empty context: everything you need is in files. Use absolute paths exactly as given.

- Core folder: {{CORE}}
- Chain: {{CHAIN}} (pack folder {{CORE}}/chains/{{CHAIN}})
- Code root: {{ROOT}}
- Audit folder: {{A}}

Read, in order:
1. {{CORE}}/engine/phases/per-unit.md — follow "## Per-cluster run" for cluster {{CLUSTER_N}}
   (files listed in {{A}}/clusters.json).
2. {{A}}/facts.json, {{A}}/risk.json, {{A}}/recon.md.
3. {{A}}/candidates/detect.json and {{A}}/candidates/rescan.json — your exclusion list (Step 2).

Write exactly one file, {{OUTPUT}} = {{A}}/candidates/per-unit-{{CLUSTER_N}}.json: a JSON array of
findings conforming to {{CORE}}/engine/finding.schema.json, each with "status": "candidate",
"chain": "{{CHAIN}}", "discovery": {"phase": "per-unit", "unit": <the unit>, ...}. Write [] if you
found nothing.

The single DONE line replaces any closing statement or summary the phase file asks you to state;
put nothing else in your reply except any orchestrator records this template lists below the DONE
line: the Step 4 coverage checkpoint and the Step 2 exclusions the orchestrator copies into
{{A}}/clusters.json. Reply with exactly one line: DONE {{OUTPUT}} <number of findings>
Then append one line per cluster file as `COVERAGE: <file>|<loc>|<opened true/false>|<functions
analyzed>` and one line per exclusion as `EXCLUDED: <the EXCLUDED — record>` (or `EXCLUDED: none`).
