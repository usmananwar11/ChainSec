# ChainSec pipeline

All paths in this file are relative to the core skill folder (CORE). `<chain>` is a pack name,
`A` = `TARGET/.audit/<chain>/`, `P` = `chains/<chain>/`.

## Inputs
- `TARGET`: directory being audited (default: the current working directory). Make it absolute.
- Flags: `--quick` (skip per-unit and state phases), `--chain <name>`, `--fresh` (discard previous state).
- `CORE`: absolute path of the core skill folder (the entry skill resolved it).

## Step 0 — Detect chains
Run `python3 CORE/scripts/detect-chain.py TARGET -o TARGET/.audit/chains.json`.
- With `--chain X`: keep only entries for X; if none remain, use `[{"chain": "X", "root": "."}]`
  and confirm `chains/<X>/pack.json` exists (otherwise stop: unsupported chain).
- Empty list: stop with "No supported chain detected. Supported packs: <folders in chains/>".

## Per chain
Process chains one after another. For each: `ROOT = TARGET/<root>`, `A = TARGET/.audit/<chain>`.
With `--fresh`, delete `A` first. **Resume:** skip a phase whose output already exists (JSON outputs
must also parse and, for findings files, pass `scripts/validate-findings.py` schema checks); say
`resumed: <phase>`.

| # | Phase | How | Output |
|---|---|---|---|
| 1 | preflight | follow `engine/phases/preflight.md` (gate mode) | `A/preflight.json` |
| 2 | extract | `bash CORE/P/<pack.extractor> ROOT A/facts.json` | `A/facts.json` |
| 3 | score | `python3 CORE/scripts/score-risk.py A/facts.json CORE/P/pack.json -o A/risk.json` | `A/risk.json` |
| 4 | recon | follow `engine/phases/recon.md` | `A/recon.md`, `A/known-issues.md` |
| 5 | detect | one subagent, `prompts/pass1-detector.md`, writing `A/candidates/detect-P1.json` and `A/pass1-brief.md`; then **parallel**: one subagent per lens A, B, C, D using `prompts/lens-detector.md`, each writing `A/candidates/detect-<lens>.json`; then follow the "Consensus merge" and "Pass 3 sweep" sections of `engine/phases/detect.md` | `A/candidates/detect.json` |
| 6 | rescan | one subagent, `prompts/rescan.md` | `A/candidates/rescan.json` |
| 7 | per-unit (skip if `--quick`) | build clusters per `engine/phases/per-unit.md`; **parallel**: one subagent per cluster (max 8), `prompts/per-unit.md`, each writing `A/candidates/per-unit-<n>.json`; then `python3 CORE/scripts/merge-findings.py --concat -o A/candidates/per-unit.json A/candidates/per-unit-*.json` | `A/candidates/per-unit.json` |
| 8 | state (skip if `--quick`) | one subagent, `prompts/state-auditor.md` | `A/candidates/state.json` |
| 9 | verify | one subagent, `prompts/critic.md` | `A/verdicts.json` |
| 10 | validate | see "Validation and repair" | `A/verdicts.json` passes |
| 11 | report | one subagent, `prompts/reporter.md` | `A/report.md`, `A/findings.json` |

## Validation and repair
1. `python3 CORE/scripts/validate-findings.py A/verdicts.json`. Exit 0 → continue.
2. Exit 1 → run the "Repair pass" section of `engine/phases/verify.md` on the listed ids (edit
   `A/verdicts.json` in place), then re-run step 1.
3. Still exit 1 → `python3 CORE/scripts/validate-findings.py A/verdicts.json --downgrade`.
4. Still exit 1 (schema errors) → fix the JSON mechanically once more; if it still fails, mark the
   chain's report phase `incomplete` and continue with the next chain.

## After all chains
Run `python3 CORE/scripts/merge-findings.py -o TARGET/.audit/findings.json TARGET/.audit/*/findings.json`
(only chains that produced one). If one chain ran, copy `A/report.md` to `TARGET/.audit/report.md`;
otherwise write `TARGET/.audit/report.md` following "Combined report" in `engine/report-template.md`.

## Dispatch
Work out your runtime from the subagent tool you have, then read the matching file and follow it
for every **parallel** or **one subagent** row:

| You have | Runtime file |
|---|---|
| `Agent` or `Task` tool (Claude Code) | `runtimes/claude-code.md` |
| `task` or `subagent` tool (OpenCode) | `runtimes/opencode.md` |
| a Codex sub-agent tool | `runtimes/codex.md` |
| `invoke_subagent` (Antigravity) | `runtimes/antigravity.md` |
| none of these, or unsure | `runtimes/generic.md` (sequential, in this conversation) |

Fill prompt templates by replacing `{{CORE}}`, `{{CHAIN}}`, `{{ROOT}}`, `{{A}}`, `{{OUTPUT}}`
and the template-specific placeholders with absolute paths/values. Pass paths, never file contents.
After each subagent returns, confirm its output file exists and parses as JSON
(`python3 -c "import json,sys; json.load(open(sys.argv[1]))" <file>`).

## Failures
| Failure | Do |
|---|---|
| Required tool missing | preflight stops the chain; print the pack's install command |
| Optional tool missing | continue; `preflight.json` mode `degraded`; say so in the report |
| Extractor fails | it falls back to regex mode itself; if it exits non-zero, stop the chain and show stderr |
| Subagent output missing/invalid | re-run that unit once sequentially in this conversation; if still bad, record the phase as `incomplete` in `A/preflight.json` → `incomplete_phases` and continue |
| Validation still failing | see "Validation and repair" step 4 |

## Final message
Report: chains audited; per chain the facts mode (`compiler`/`regex`), preflight mode
(`full`/`degraded`) and incomplete phases; finding counts by severity; the path
`TARGET/.audit/report.md`; next steps `chainsec-review`, `chainsec-poc <ID>`, `chainsec-fuzz`.
