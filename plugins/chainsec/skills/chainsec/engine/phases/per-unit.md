# Per-Unit Analysis — Narrow Scope, Maximum Depth (B3)

> Phase 7 of the ChainSec pipeline (`engine/pipeline.md`). Runs after Rescan, before State Analysis. Skipped with `--quick`.
> *(Methodology adapted from PlamenTSV/plamen, MIT — `phase3b-rescan-prompt.md` § Phase 3c.)*

Reads: `A/facts.json`, `A/risk.json`, `A/recon.md`, `A/candidates/detect.json`, `A/candidates/rescan.json`
Writes: `A/clusters.json` (orchestrator; each cluster's `coverage` and `excluded` are filled in from its subagent's reply), `A/preflight.json` `warnings` (orchestrator, unclustered files), `A/candidates/per-unit-<n>.json` (one per cluster); the pipeline concatenates them into `A/candidates/per-unit.json`

`A` = `TARGET/.audit/<chain>/`. A **unit** is the pack's unit of analysis (`pack.json`
`unit_of_analysis`, e.g. a contract, module or program); `A/facts.json` `units[]` lists them.

## Purpose

Counter **attention dilution**. A whole-codebase agent spends its budget on the two or three most interesting files; everything else gets a skim. This phase assigns one agent per unit cluster with a scope narrow enough that depth is affordable.

Rescan (B4) covers cross-unit bugs by looking broadly. This phase covers the opposite failure: bugs that need line-by-line attention on one file. The two are complementary — run both.

## Orchestrator: build clusters

Run by the orchestrator before dispatching the per-cluster subagents.

### Step 1: Build Unit Clusters

Group scope files into clusters following the pack's clustering file (`pack.json` `clustering`,
relative to the pack folder). It says which units belong together (for example, a base and its
derived units: a "missing" check often lives in the parent, and an agent that only sees the child
reports a false positive), the cluster size cap, the maximum number of clusters (at most 8) and
the findings cap. Use `A/facts.json` `units[].parents` and `units[].loc` for the grouping and the
LOC sums, and `A/risk.json` `files[].score` (RISK_SCORE) to prioritise.

Record the cluster plan before starting:

| Cluster | Files | LOC | Reason for grouping |
|---------|-------|-----|---------------------|

Then write `A/clusters.json`, a JSON array with one object per cluster: `n` (1, 2, … in priority
order), `units` (unit names) and `files` (paths relative to ROOT, as in `A/facts.json`). Two optional
fields are added after the cluster's subagent returns (see "Record the subagent's reply" below):
`coverage` and `excluded`.

```json
[{"n":1,"units":["Vault","Owned"],"files":["src/Vault.<ext>","src/auth/Owned.<ext>"]},{"n":2,"units":["Router"],"files":["src/Router.<ext>"]}]
```

If any scope file received no dedicated cluster, say so explicitly with its RISK_SCORE —
silently dropping coverage reads as "we covered everything" when you didn't. Add one line per such
file to `A/preflight.json` `warnings` ("per-unit: no dedicated cluster for <file> (RISK_SCORE <score>)").

Dispatch one subagent per cluster (pipeline row 7), each running "Per-cluster run" below for its
cluster `n`.

### Record the subagent's reply

When a cluster's subagent returns, copy its coverage checkpoint and exclusions from its reply (see
"Output" below) into that cluster's object in `A/clusters.json`:

- `coverage`: one object per cluster file, from the Step 4 table: `file`, `loc`, `opened`
  (true/false), `functions` (number of functions analyzed).
- `excluded`: one string per `EXCLUDED — …` record from Step 2 (empty list when none).

```json
{"n":1,"units":["Vault","Owned"],"files":["src/Vault.<ext>","src/auth/Owned.<ext>"],"coverage":[{"file":"src/Vault.<ext>","loc":412,"opened":true,"functions":14},{"file":"src/auth/Owned.<ext>","loc":96,"opened":true,"functions":5}],"excluded":["EXCLUDED — withdraw() skips reward checkpoint at Vault.<ext>:142 → stale rewards. Duplicate of [HIGH] src/Vault.<ext>:142."]}
```

The orchestrator writes `A/clusters.json`; subagents never do (they run in parallel).

## Per-cluster run

You analyze ONE cluster: cluster `n` of `A/clusters.json` (units and files from your prompt).
Write your candidates to `A/candidates/per-unit-<n>.json`.

### Step 2: Build the Exclusion List

Same format as Rescan — one line per already-known candidate, from **both** `A/candidates/detect.json` and `A/candidates/rescan.json`:

```
- [HIGH] src/Vault.<ext>:142 — withdraw() skips reward checkpoint
```

#### Exclusion source rule (recall-safe)

You may exclude a candidate as a duplicate ONLY if you can point at a **concrete entry in the list above** — a real ID or a real `file:line`. A bug you *believe* is already known but cannot find in the list MUST be reported as new. **When in doubt, emit.**

Every exclusion you record must name its referent and carry its own content:

```
EXCLUDED — byte-width mismatch at Encoder.<ext>:412 truncates the high byte so a crafted
account passes validation → asset mis-routing. Duplicate of [HIGH] Encoder.<ext>:412.
```

A bare "already known" with no location and no referent is a suppressed bug, not an exclusion.

### Step 3: Analyze Each Cluster

For EACH function in the cluster, in order:

1. **State completeness** — does every state-modifying path update ALL related state? (timestamps, accumulators, snapshots, mirrored balances)
2. **Conditional branch audit** — for each if/else, what state is written in each branch? Is anything left stale on the skip path?
3. **Boundary values** — what happens at 0, 1, MAX, and the type boundary for every parameter?
4. **Pairing audit** — for each encode / normalize / hash / lock operation, trace its inverse (decode / denormalize / verify / unlock). Same inputs, same order?
5. **Fee and reward trace** — follow accrual → accumulation → claim → transfer. Do assets and shares stay consistent at every step?
6. **Parent standalone pass** — when a base unit is in your cluster, also examine its unconditional paths *on their own terms*, as if no child existed. Timestamp updates, fee math and state transitions that run regardless of which override is active are invisible when you only read the parent through the child's lens.

#### Cross-cluster boundaries

When an issue sits on a boundary with a unit outside your cluster, describe it from **your** files' perspective and name the external unit. Do not trace into it — another cluster's agent owns that code.

### Step 4: File Coverage Checkpoint (MANDATORY)

Before writing findings, list every file in your cluster and confirm you opened it:

| File | LOC | Opened? | Functions analyzed |
|------|-----|---------|--------------------|

Any `Opened: NO` → open and analyze it before returning. 28% of historically missed findings were in files the agent never opened.

### Quality gates

- Every finding needs a specific `file:line` (a `locations[]` entry with `file` and `line_start`).
- **Maximum 5 findings per cluster** — prioritise by severity. This is a depth pass, not a volume pass.
- Do not re-report anything on the exclusion list (subject to the exclusion source rule above).
- Do not report generic best practice; kill gate A removes those unconditionally.
- Record concrete values you tested as depth-evidence tags (`audit_trail.depth_evidence`).

### Output

Write a JSON array to `A/candidates/per-unit-<n>.json`; each element conforms to
`engine/finding.schema.json`. Use the standard candidate format (field mapping in
`engine/phases/detect.md` Step 6), with IDs `PC<n>-1`, `PC<n>-2`, …, `status: "candidate"`,
`discovery.phase: "per-unit"` and `discovery.unit` set to the unit the finding is in. Write `[]`
if you found nothing.

Example element (cluster 1):

```json
{
  "id": "PC1-1",
  "chain": "<chain>",
  "title": "Owned base skips lastAccrual update on the pause branch",
  "severity": "Medium",
  "category": "state-staleness",
  "status": "candidate",
  "locations": [{"file": "src/auth/Owned.<ext>", "line_start": 58, "line_end": 66, "unit": "Owned", "function": "_accrue"}],
  "discovery": {"phase": "per-unit", "lens": null, "mindset": "edge-case", "consensus": null, "unit": "Owned"},
  "description": "Discovery: per-unit step 2 (conditional branch audit) and step 6 (parent standalone pass). When paused, _accrue() returns before writing lastAccrual, so the first accrual after unpausing charges interest for the whole paused period.",
  "root_cause": "The early-return branch leaves lastAccrual stale, so elapsed time includes the pause.",
  "vulnerable_code": "if (paused) return;\ninterest += rate * (now - lastAccrual);\nlastAccrual = now;",
  "harm": {"who": "borrowers with open positions during a pause", "loses_what": "interest charged for time the protocol was paused", "magnitude": "rate × pause duration × outstanding debt"},
  "exploit_trace": [
    "1. Admin pauses the protocol for 7 days; lastAccrual stays at the pause timestamp.",
    "2. Admin unpauses; the next call to _accrue() computes elapsed = 7 days.",
    "3. Result: every borrower is charged 7 days of interest for a period in which they could not repay."
  ],
  "preconditions": [{"text": "the protocol is paused for a non-trivial period", "type": "TIMING"}],
  "postconditions": [{"text": "debt balances are inflated by the paused period's interest", "type": "BALANCE"}],
  "audit_trail": {
    "step_execution": "Per-unit: 1=✓ 2=✓ 3=✓ 4=✗(N/A: no encode/decode pair) 5=✓ 6=✓",
    "rules_applied": ["R8:✓(lastAccrual is cached state across pause/unpause)", "R10:✓(assessed at a 7-day pause)", "R11:✗(no external tokens)", "R12:✗(single path)", "R15:✗(no flash-loan-accessible state)", "R16:✗(no oracle dependency)"],
    "depth_evidence": ["[VARIATION:pause 1h→7d → overcharge grows linearly]", "[TRACE:unpause→_accrue()→interest += rate*7d]"],
    "missing_precondition": "",
    "postconditions_created": ["debt balances are inflated by the paused period's interest"],
    "who_benefits": "Lenders, at borrowers' expense"
  }
}
```

The cluster plan lives in `A/clusters.json`. Complete the coverage checkpoint (Step 4) and record
your exclusions before writing the file; they are not part of the JSON output.

Then state: `Per-unit complete: cluster <n>, M new candidates`, followed in the same reply by the
Step 4 coverage table and one line per `EXCLUDED — …` record (or `Excluded: none`). The orchestrator
copies both into `A/clusters.json` (see "Record the subagent's reply").

## No iteration

This phase does NOT iterate. The narrow scope *is* the depth mechanism — there is no attention saturation to counter by re-scanning. One pass per cluster is sufficient.
