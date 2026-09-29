# Report template

Used by the report phase (`engine/phases/report.md`) to write `A/report.md` and `A/findings.json`,
and by the pipeline's "After all chains" step for the combined report. `A` = `TARGET/.audit/<chain>/`.

Pack values used below (from `chains/<chain>/pack.json`):
- `id_prefix`: final finding IDs are `<id_prefix>-NNN` (001, 002, … in rank order).
- `code_fence`: the language tag of every code block showing target code.

## Report (`A/report.md`)

````markdown
# ChainSec Security Audit Report

**Target**: [Protocol name]
**Date**: [Date]
**Auditor**: ChainSec
**Scope**: [Files audited]

---

## Executive Summary

[2-3 sentences: what was audited, key findings, overall risk assessment]

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | X |
| High | X |
| Medium | X |
| Low | X |

---

## Findings

### [<ID>] <Title> — <SEVERITY>

**File**: `path/to/file:XX`
**Category**: [e.g., reentrancy, state-desync, access-control]
**Evidence**: [one of — see the Evidence tier below]

**Description**:
[Clear explanation of the vulnerability. What's wrong and why it matters.]

**Impact**:
[Specific impact: who is affected, how much value at risk, under what conditions.]

**Proof of Concept**:
```
[If [POC-PASS]: the passing test's harm assertion + the profit/drain output, and the
run command. Otherwise: the concrete attack steps / code trace.]
```

**Root Cause**:
[One sentence: the fundamental reason this bug exists.]

**Recommendation**:
[Specific fix. Not "add a check" — show exactly what check, where, and why it works.]

**Vulnerable Code**:
```<code_fence>
// The actual vulnerable code
```

**Fixed Code** (suggested):
```<code_fence>
// The corrected code
```

---

[Repeat for each finding, ordered by severity (Critical first)]

---

## Security Strengths

[Exactly 5 bullet points. Derived from what Recon observed in the codebase — not generic praise, only things you actually verified in the code. Each bullet should name the specific contract/pattern/version.]

Pick the 5 most relevant from these categories (skip any that don't apply):
- **Access control model**: What pattern is used? Is it consistent across all privileged functions?
- **Reentrancy protection**: Are state-mutating external calls guarded? CEI pattern followed? Guard coverage?
- **Arithmetic safety**: Checked math, explicit unchecked blocks only where safe, safe downcasts?
- **Battle-tested dependencies**: Which libraries? Are they current versions?
- **Input validation**: Are external entry points validated (zero-address checks, bound checks, array length limits)?
- **Upgrade safety**: If upgradeable — initializer guards, storage gap patterns, upgrade pattern choice?
- **Oracle handling**: Staleness checks, fallback oracles, price bound validation?
- **Test coverage**: Visible test suite breadth, fuzzing, invariant tests?

examples: see the pack's heuristics.md "Security strengths examples"

Format in the report:
```
## Security Strengths

- **[Category]**: [Specific observation with contract/file names]
- **[Category]**: [Specific observation]
- **[Category]**: [Specific observation]
- **[Category]**: [Specific observation]
- **[Category]**: [Specific observation]
```

**Rules**: Only state what you verified in the code. Never write generic praise like "good use of modifiers." If you can't find 5 concrete strengths, fill remaining slots with "Area for improvement: [what's missing]" — honest signal is more valuable than padding.

---

## Architecture Observations

[Non-finding observations from the recon phase that are worth noting:
- Complexity hotspots that could hide future bugs
- Areas that would benefit from additional testing
- Design decisions that are unusual or noteworthy]

---

## Methodology

This audit was performed using ChainSec's multi-phase analysis:
1. **Recon**: Architecture mapping, fund flow analysis, trust boundary identification
2. **Detection**: Feynman first-principles interrogation (7 question categories, 28+ questions per function) + 40 exploit-derived heuristic checks
3. **State Analysis**: Coupled state dependency mapping, mutation matrix cross-checking, parallel path comparison, masking code detection
4. **Verification**: Devil's advocate falsification of every H/M finding, mandatory proof-of-concept traces, systematic FP elimination

[Mode notes: facts mode (`compiler`/`regex`), preflight mode (`full`/`degraded`), incomplete phases — from `A/preflight.json` and `A/facts.json`.]

Methodology derived from Krait by Zealynx Security.
````

The **Evidence** line is one of the evidence-tier lines in `engine/verdicts.md`.

## Findings index (`A/findings.json`)

Also save the machine-readable findings to `A/findings.json`: a JSON array; each element
conforms to `engine/finding.schema.json`, carries its final `<id_prefix>-NNN` id, and has
status `verified`, `verified-conditional` or `downgraded`. Krait's index fields map to schema
fields: `file`/`line` → `locations[]`, `impact` → `harm`, `rootCause` → `root_cause`. Counts
by severity go in the report's Finding Summary, not in the JSON.

```json
[
  {
    "id": "<id_prefix>-001",
    "chain": "<chain>",
    "title": "...",
    "severity": "High",
    "category": "...",
    "status": "verified",
    "locations": [{ "file": "path/to/file", "line_start": 42 }],
    "description": "...",
    "harm": { "who": "...", "loses_what": "...", "magnitude": "..." },
    "root_cause": "...",
    "recommendation": "...",
    "verdict": { "evidence_tag": "[CODE-TRACE]" }
  }
]
```

## After Report: What's Next

After presenting the report, **always show this block** (copy exactly, filling in the count):

```
───────────────────────────────────────────────────
📋 [N] findings saved to .audit/findings.json
───────────────────────────────────────────────────
```

Then offer next steps:

### Next Steps

1. **Review killed findings** (if the Critic killed 5+ candidates): Suggest running `chainsec-review` to get a second opinion on findings killed by the automatic gates. Especially valuable when many findings were killed by Gates C (intentional design), E (admin trust), or B (theoretical).

2. **Prove a finding**: Suggest running `chainsec-poc <ID>` on a Critical or High finding (or on the whole findings list for batch triage) to turn a `[CODE-TRACE]` into an executed `[POC-PASS]` or `[POC-FAIL]` (`engine/poc/workflow.md`).

3. **Fuzz invariants**: Suggest running `chainsec-fuzz` to extract the protocol's invariants and test them with the pack's fuzzing framework (`engine/fuzz.md`).

Present these as a numbered list after the banner. Let the user choose which (if any) they want.

## Combined report (multiple chains)

When more than one chain was audited, write `TARGET/.audit/report.md` with:

1. `# ChainSec Security Audit Report`, then Target, Date, Auditor and Scope (all chains).
2. One Finding Summary table per chain (`### <chain>` heading, then the Severity/Count table).
3. `## Findings`: every finding from `TARGET/.audit/findings.json` in its ranked order, each in
   the finding format above, using the fence language of that finding's chain pack.
4. `## Boundary findings`: every finding with `boundary: true` (by id and title, with the chains
   its locations span).
5. `## Mode notes`: per chain, the facts mode (`compiler`/`regex`), preflight mode
   (`full`/`degraded`) and incomplete phases.
6. The Security Strengths, Architecture Observations and Methodology sections, combined across
   chains, ending with `Methodology derived from Krait by Zealynx Security.`
