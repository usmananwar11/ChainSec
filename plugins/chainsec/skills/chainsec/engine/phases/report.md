# Reporter — Consolidation, Ranking & Final Report

> Phase 11 (final) of the ChainSec pipeline (`engine/pipeline.md`). Runs after `A/verdicts.json` passes validation.

Reads: `A/verdicts.json`, `A/review.json` (if present), `A/recon.md`, `A/preflight.json`, `A/facts.json` (`mode`), `chains/<chain>/pack.json` (`id_prefix`, `code_fence`)
Writes: `A/findings.json`, `A/report.md`

`A` = `TARGET/.audit/<chain>/`.

## Purpose

Consolidate all verified findings into a professional, actionable security report. Deduplicate, rank by impact, and format for human consumption.

## Execution

### Step 1: Load Verified Findings

Read `A/verdicts.json`. Only include findings with status (`engine/verdicts.md`):
- **`verified`** (TRUE POSITIVE) — include as-is
- **`verified-conditional`** (LIKELY TRUE) — include with caveat noting the conditions required (its `preconditions`)
- **`downgraded`** — include at its new severity

If `A/review.json` exists, also load its revived findings (status `verified-conditional` or
`downgraded`); keep the "Second opinion — worth manual review" caveat from `verdict.reason` on them.

Do NOT include: `killed` findings (FALSE POSITIVE, INSUFFICIENT EVIDENCE), `candidate` entries, or LOW-severity findings (unless user specifically requested them).
Never include `severity: "Info"` findings (including review.json's REVIVE — Informational items): they would be padding (see Rules, "No padding").

### Step 2: Deduplication

Multiple candidates may describe the same underlying bug from different angles (Detector found it via Feynman, State Auditor found it via coupled pair analysis). Merge these:

- Same file + same lines + same root cause → merge into single finding, combine evidence
- Same root cause but different manifestations → single finding with multiple impact paths
- Related but distinct bugs → keep separate, note relationship

A merged finding lists the ids it absorbed in `merged_from`.

### Step 2.5: Root-Cause Consolidation (A7)

*(Source: PlamenTSV/plamen, MIT — `phase6-report-prompts.md` § STEP 1.5)*

Step 2 removes findings that are the SAME bug seen twice. This step handles the different
problem: several findings that are genuinely distinct **locations** of ONE root cause with
ONE fix — the "10 separate missing-checkpoint findings" shape. Reporting those as ten
findings inflates the count and hides the fact that the developer has one job to do.

**Merge two or more findings into one when ALL of these hold:**

1. **Same fix pattern** — the same kind of code change closes all of them
2. **Same severity tier** — a tier gap means the impacts differ; keep them separate
3. **Same vulnerability class** — same bug pattern, not just the same file
4. **Describable together** — a reader understands every location from one description plus a table
5. **≤ 6 locations** — beyond that, split into two findings for readability

**Do NOT merge when:**
- The fixes touch **different functions** — write the one-line fix for each; if they differ, these are different root causes
- Merging would hide a severity difference
- You are unsure. **A duplicate finding is cosmetic. A dropped true positive is a missed vulnerability. When in doubt, keep them separate.**

**Format for a consolidated finding**: use a class-level title (e.g. "Reward checkpoint
missing on balance-changing paths"), not a single-location title. List every location in a
table under the description, then give ONE recommendation covering all of them:

```markdown
**Affected locations** (4):

| File | Line | Issue |
|------|------|-------|
| `Staking.<ext>` | 142 | `withdraw()` skips `_updateReward` |
| `Staking.<ext>` | 201 | `emergencyWithdraw()` skips `_updateReward` |
| `Staking.<ext>` | 233 | `transferStake()` skips `_updateReward` |
| `Migrator.<ext>` | 88  | `migrate()` skips `_updateReward` |

*One fix closes all 4 locations above.*
```

In `A/findings.json` a consolidated finding carries every location in `locations[]` and the
absorbed ids in `merged_from`.

### Step 2.75: Evidence Tier (surface how a finding was verified)

Every finding carries an **Evidence** line saying how strongly it was verified. Derive it from the
finding's `verdict.evidence_tag`, using the tier table and rules in `engine/verdicts.md`, section
"Evidence tags". If no PoC pass was run at all, every finding is `REASONED` — that is the normal
default audit, and it is fine.

### Step 3: Severity Ranking

Final severity assignment using this rubric:

| Severity | Criteria | Examples |
|----------|----------|---------|
| **CRITICAL** | Direct, unconditional loss of funds or permanent protocol DoS. Any user can trigger. No admin intervention can fix. | Drain all vault funds, brick protocol permanently, unauthorized minting |
| **HIGH** | Conditional fund loss, privilege escalation, or broken core invariant. Requires specific conditions but attacker can create them. | Oracle manipulation for bad debt, self-liquidation profit, reentrancy fund drain |
| **MEDIUM** | Value leakage, griefing with cost to attacker, degraded functionality. Limited impact or requires unlikely conditions. | Rounding exploitation over many txs, reward gaming, event inconsistency affecting integrations |
| **LOW** | Informational, gas optimization, cosmetic inconsistency. No direct value impact. | Unnecessary storage reads, missing events, style inconsistency |

A severity changed here keeps the earlier one in `verdict.original_severity` and the reason in `verdict.reason`.

#### Step 3.5: Trust-Assumption Downgrade (A5)

*(Source: PlamenTSV/plamen, MIT — `report-template.md` § Downgrade modifiers)*

Kill gate E discards findings that need a **fully trusted** actor (governance multisig,
DAO, timelock) to act maliciously. That is correct for a rug vector nobody can act on —
but it is too blunt for the middle ground, where a real bug exists and the only question
is how much weight to give it. This step is that middle option: **report at one tier lower
with an explicit note, rather than discard.**

Apply when the critic recorded a trust dependency on a finding that **survived** gate E:

| Actor class | Examples | Treatment |
|---|---|---|
| **Fully trusted** | governance multisig, DAO, timelock | Already killed by gate E — nothing to do here |
| **Semi-trusted** | keeper, operator, relayer, sequencer, oracle updater, whitelisted caller | **−1 severity tier**, floor Informational, plus the note below |
| **Untrusted** | any EOA, any contract | No adjustment — full severity |

Print the adjustment on the finding so the reader can re-rate it themselves:

```
**Severity adjusted**: High → Medium — the attack path requires `keeper` to violate a
stated trust assumption: keepers are assumed to submit prices within 1% of market.
```

Never apply the downgrade silently. An unexplained severity is worse than either severity.
In `A/findings.json` the adjusted finding has status `downgraded`, the new `severity`,
`verdict.original_severity`, and the note in `verdict.reason`.

### Step 4: Assign IDs, write the findings index and the report

1. **Rank** the findings: severity (Critical, High, Medium, Low), then `verified` before
   `verified-conditional` before `downgraded`, then by file and line. Drop any finding whose
   severity is now Info (e.g. after the Step 3.5 downgrade); it does not get an ID.
2. **Assign final IDs** `<id_prefix>-NNN` (`id_prefix` from `pack.json`; 001, 002, … in rank
   order). Record each finding's pre-report id(s) in `merged_from` so the candidate trail stays
   traceable.
3. **Write `A/findings.json`**: a JSON array; each element conforms to `engine/finding.schema.json`
   with the full schema fields carried through (`locations`, `discovery`, `description`,
   `root_cause`, `recommendation`, `vulnerable_code`, `harm`, `exploit_trace`, `preconditions`,
   `postconditions`, `verdict`, `audit_trail`, `merged_from`), and status `verified`,
   `verified-conditional` or `downgraded`. Fill `recommendation` with the specific fix.
4. **Write `A/report.md`** following `engine/report-template.md` (Report section): findings in
   rank order under their final IDs, code blocks fenced with the pack's `code_fence`, the Evidence
   line from Step 2.75, the Security Strengths section (examples: the pack's heuristics.md,
   section "Security strengths examples"), and the mode notes from `A/preflight.json` (`mode`,
   `incomplete_phases`, `warnings`) and `A/facts.json` (`mode`).
5. **Validate before finishing**: run `python3 scripts/validate-findings.py A/findings.json` (from
   the core folder, or with its absolute path). Exit 0 → done. Exit 1 → fix each listed reject from
   `A/verdicts.json` and the code (never invent a location, harm or trace), rewrite both files and
   re-run.

Example `A/findings.json` element:

```json
{
  "id": "<id_prefix>-001",
  "chain": "<chain>",
  "title": "withdraw() decrements totalShares after the external transfer",
  "severity": "High",
  "category": "reentrancy",
  "status": "verified",
  "locations": [{"file": "src/Vault.<ext>", "line_start": 142, "line_end": 150, "unit": "Vault", "function": "withdraw"}],
  "discovery": {"phase": "detect", "lens": "B", "mindset": "accountant", "consensus": "moderate", "unit": null},
  "description": "withdraw() reduces the caller's shares, transfers the assets, and only then reduces totalShares; a re-entrant deposit during the transfer callback mints shares at a stale exchange rate.",
  "root_cause": "The coupled update to totalShares happens after the external call.",
  "recommendation": "Move `totalShares -= amount;` above the transfer and add a reentrancy guard to deposit() and withdraw().",
  "vulnerable_code": "shares[user] -= amount;\nasset.transfer(user, assets);\ntotalShares -= amount;",
  "harm": {"who": "remaining depositors", "loses_what": "part of their pro-rata assets", "magnitude": "about 9.8 tokens per re-entrant 100-token withdrawal, repeatable"},
  "exploit_trace": [
    "1. Initial state: totalAssets = 1000, totalShares = 1000, attacker contract holds 100 shares.",
    "2. Attacker calls withdraw(100); the transfer at line 146 enters the attacker's callback while totalShares is still 1000.",
    "3. In the callback the attacker deposits 100 and receives 111 shares at the stale rate.",
    "4. Result: the attacker's 111 shares redeem for about 109.8 tokens; 9.8 tokens come from other depositors."
  ],
  "preconditions": [],
  "postconditions": [{"text": "exchange rate permanently understated for other depositors", "type": "STATE"}],
  "verdict": {"gate": null, "reason": "Survived gates A–H; trace confirmed with values.", "evidence_tag": "[CODE-TRACE]", "method": "hybrid", "original_severity": null},
  "audit_trail": {
    "step_execution": "Gates: A=✓ B=✓ C=✓ D=✓ E=✓ F=✓ G=✓ H=✓",
    "rules_applied": ["R10:✓(severity assessed at repeated re-entry)", "R16:✗(no oracle)"],
    "depth_evidence": ["[TRACE:withdraw(100)→callback→deposit(100)→111 shares]"],
    "missing_precondition": "",
    "postconditions_created": ["exchange rate permanently understated for other depositors"],
    "who_benefits": "Attacker"
  },
  "merged_from": ["DB-1", "STATE-2"]
}
```

After presenting the report, show the "After Report: What's Next" block from
`engine/report-template.md`.

## Rules

- **Only verified findings.** Nothing from the candidate lists that wasn't approved by the Critic.
- **Concrete recommendations.** "Fix this" is not a recommendation. Show the code change.
- **Honest severity.** Don't inflate to look impressive. Don't deflate to look clean.
- **Readable by humans.** An auditor picking up this report should understand every finding in < 2 minutes.
- **No padding.** Don't add informational/low findings just to make the report longer. Quality > quantity.
