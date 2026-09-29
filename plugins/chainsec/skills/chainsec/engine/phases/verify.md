# Critic — Verification Gate & False Positive Elimination

> Phase 9 of the ChainSec pipeline (`engine/pipeline.md`). Runs after Detection and State Analysis. Its "Repair pass" section is also run by the pipeline's "Validation and repair" step.

Reads: `A/candidates/detect.json`, `A/candidates/rescan.json`, `A/candidates/per-unit.json`, `A/candidates/state.json`, `A/recon.md`, `A/known-issues.md`
Writes: `A/verdicts.json`

`A` = `TARGET/.audit/<chain>/`. Read ALL available candidate files before starting:

- `A/candidates/detect.json` (Phase 5, required)
- `A/candidates/rescan.json` (Phase 6 — `[]` if the hard-exit rule fired)
- `A/candidates/per-unit.json` (Phase 7 — absent with `--quick`)
- `A/candidates/state.json` (Phase 8 — absent with `--quick`)

Do not read the partial files `A/candidates/detect-P1.json`, `A/candidates/detect-<lens>.json` or
`A/candidates/per-unit-<n>.json`; their contents are already in the merged files above.

Every candidate from every file goes through the same gates. A candidate from a
second-pass agent gets no benefit of the doubt and no extra suspicion.

## Purpose

**Every CRITICAL, HIGH, and MEDIUM candidate must be VERIFIED before it reaches the user.** This phase is the devil's advocate — its job is to DISPROVE findings. Only findings that survive attempted falsification are TRUE POSITIVES.

**Devil's Advocate methodology** *(Source: PlamenTSV/plamen, MIT)*: For every finding, FIRST argue why it is NOT a bug — construct the strongest possible defense. Only if that defense fails does the finding stand. Before marking anything as FALSE POSITIVE, also ask: "Does ANY other finding in this audit enable the missing precondition?" A finding dismissed in isolation may become exploitable when combined with another.

The goal is **zero false positives** on H/M findings. A false positive wastes the auditor's time and destroys trust. Better to miss a real bug than report a fake one.

## Core Rule

**INNOCENT UNTIL PROVEN GUILTY. The burden of proof is on the FINDING, not on the code.**

For each candidate, you must:
1. Attempt to DISPROVE it through code trace
2. Only if disproof FAILS does the finding stand
3. If you cannot write a concrete exploit trace with actual values, the finding is KILLED
4. There is NO "likely true" or "insufficient evidence" — either you proved it or you didn't
5. **When in doubt, KILL it.** A missed real bug is unfortunate. A false positive destroys credibility.

## Step 0: AUTOMATIC KILL GATE (MANDATORY — run FIRST on every candidate)

Apply `engine/kill-gates.md` Step 0 (Gates A–H and the DoS exception). Read the pack's
fp-patterns.md, section "Gate overrides and examples", first. A gate kill is `status: killed` with
`verdict.gate` set to the gate letter.

---

## Step 0.5: IMPACT PREMISE — harm, not mechanism (MANDATORY, runs before any trace)

Apply `engine/kill-gates.md` Step 0.5. Record the harm statement in `harm` (`who`, `loses_what`,
`magnitude`). A kill here is `status: killed`, `verdict.gate: impact-premise`, with
`verdict.reason` starting `Harm: MECHANISM-ONLY`.

---

**After the Kill Gate and Impact Premise, surviving candidates proceed to verification methods below.**

## Consensus-Aware Verification

Before applying verification methods, check the candidate's **consensus tag** from detection (`discovery.consensus`):

- **STRONG consensus (3+ sources)**: This finding was independently discovered by multiple analysis passes with different mindsets. If it passed kill gates A-H, fast-track to VERIFIED — write the exploit trace for documentation but the convergent evidence is strong.
- **MODERATE consensus (2 sources)**: Normal verification — full kill gate + exploit trace. The dual discovery adds confidence but doesn't skip any steps.
- **NO consensus (1 source only)**: Apply EXTRA scrutiny. Ask: why did the other 4 passes miss this? Acceptable reasons: different lens domain, file wasn't in that lens's scope. Suspicious reasons: it's in a Tier 1 file that all lenses analyzed. Require an especially concrete exploit trace with specific values.

The consensus tag is set only on detect-phase candidates found by Pass 1 and the lenses A–D (sources =
Pass 1 + each lens that found it). It is `null` on Pass 3, rescan, per-unit and state candidates: verify
those normally, without the consensus adjustments above.

## Verification Methods

### Method A: Deep Code Trace

For each candidate:

1. **Read the cited code.** Open the file, go to the exact lines. Does the code actually match what the candidate claims?

2. **Trace the full call chain.** Follow every internal call from the entry point to the final effect:
   - Does the function call other internal functions that apply the "missing" check?
   - Does a modifier or hook apply validation the candidate didn't see?
   - Does a parent contract (via inheritance) provide the protection?

3. **Check for mitigating code elsewhere:**
   - Is there a `require` in a called function that prevents the scenario?
   - Is there an access control modifier that limits who can trigger it?
   - Does a reentrancy guard exist that blocks the attack path?
   - Is there a time lock, pause mechanism, or rate limit?
   - Does the constructor/initializer set state that prevents the edge case?

4. **Confirm reachability end-to-end:**
   - Can an attacker actually reach this code path with the required parameters?
   - Are there economic constraints that make the attack unprofitable?
   - Does the gas cost of the attack exceed the extractable value?

### Method B: Proof-of-Concept Trace

For complex findings, construct a concrete attack trace:

```
1. Initial state: [exact values]
2. Attacker calls: function(param1, param2)
3. State changes to: [exact values]
4. Attacker calls: function2(param3)
5. State changes to: [exact values]
6. Result: [exact value extracted / state corrupted]
```

If you cannot construct a concrete trace with actual values → the finding is likely false.

### Method C: Hybrid

Code trace to confirm mechanism plausibility + concrete trace with values to verify impact.

### Method D: Executable PoC (escalation for CRITICAL / HIGH)

Executable PoC: optional escalation via the `chainsec-poc` skill using the pack's PoC guide
(`pack.json` `poc.guide`; method in `engine/poc/workflow.md`).

**Out of scope inside the audit's critic subagent:** it never builds or runs a PoC. Where this
section would escalate, it records "PoC recommended" in `verdict.reason` and keeps the verdict it
can support by trace; the user runs `chainsec-poc` afterwards.

A written trace is `[CODE-TRACE]` — fallible reasoning. For a Critical or High finding where the
pack's PoC framework is available (`A/preflight.json` shows its tool OK), escalate to an
**executed** PoC: it forks the chain or builds against in-scope source, asserts the actual HARM
(not the mechanism), and returns `[POC-PASS]` / `[POC-FAIL]`.

- `[POC-PASS]` → the only tag that supports CONFIRMED as ground truth. Upgrade confidence.
- `[POC-FAIL]` → the attack did not reproduce. Default to killing the finding unless the
  `engine/poc/assertion-protocol.md` retry protocol shows the failure was a setup error.
- Can't execute (no build env, external dep unavailable, ≥5 failed compiles) → stay at
  `[CODE-TRACE]`; do not claim a proof you did not run.

This is a **targeted, rare** escalation — not a routine per-finding step. Reach for it only
when a specific **Critical** cannot be resolved by reasoning alone and the cost of shipping
it wrong (or killing a real one) is high. Do NOT PoC every High inline; routine PoC
verification across Critical/High is the **opt-in post-report handoff** (`chainsec-poc`, see
`engine/report-template.md` "After Report: What's Next"), which runs batch-triage on demand so the
default audit stays cheap. A Medium with a clean trace never needs a PoC, and a genuinely
un-executable finding stays `[CODE-TRACE]` honestly — never penalized for it.

## Verification Checklist

For EVERY CRITICAL, HIGH, and MEDIUM candidate, answer ALL of these:

```
[ ] Does the cited code actually exist at the stated lines?
[ ] Is the described mechanism correct? (Does the code actually do what the finding claims?)
[ ] Are there mitigating factors the finding missed?
    [ ] Access control in this or calling functions?
    [ ] Validation in parent contracts (check inheritance chain)?
    [ ] Reentrancy guards?
    [ ] Timelock or delay mechanisms?
    [ ] Economic infeasibility (attack cost > profit)?
    [ ] Language-level safety (Rust overflow panics, Move abort)?
[ ] Is severity accurate given actual impact?
    [ ] "Fund loss" = actual drain, or just a revert? (revert ≠ high)
    [ ] "Anyone can call" = true, or just permissioned actors?
    [ ] "All funds at risk" = really all, or dust amount?
[ ] Is the attack path actually reachable?
    [ ] Can you trace from a permissionless entry point to the exploit?
    [ ] Are all required preconditions achievable?
```

## Common False Positive Patterns

Eliminate these systematically. A kill by one of these is `status: killed` with
`verdict.gate: fp-pattern:<id>` (e.g. `fp-pattern:FP-1`).

### FP-1: Authorization Handled Elsewhere
The finding claims "missing access control" but auth is enforced by:
- The function that calls this one (external → internal flow)
- A modifier on a parent contract
- A router/proxy that gates access before delegation
- A factory pattern where only the factory can create instances

**Check**: Trace ALL callers of the function. If every path goes through auth, the finding is false.

### FP-2: Validation in Called Functions
The finding claims "unchecked input" but the called function validates:
- `_transfer` checks balance internally
- `_mint` checks for address(0) internally
- Library functions (SafeMath, SafeERC20) handle edge cases

**Check**: Read the implementation of every function called within the vulnerable function.

### FP-3, FP-7, FP-8: see the pack's fp-patterns.md

FP-3 (standard library protection), FP-7 (language-level arithmetic safety, with its downcast
exception) and FP-8 (read-only / view function confusion) are chain-specific: the pack's
fp-patterns.md, section "FP patterns".

### FP-4: Rounding Drift Cleaned Downstream
The finding claims "precision loss" but:
- The protocol has a dust threshold that catches small remainders
- A periodic reconciliation function rebalances
- The rounding favors the protocol (safe direction)

**Check**: Is the rounding direction safe? Does dust accumulate dangerously or stay bounded?

### FP-5: Bounded Loops / Economic Constraints
The finding claims "unbounded loop DoS" but:
- The loop is bounded by design (max N participants, max M items)
- The economic cost of growing the loop exceeds griefing benefit
- An admin can prune the array

**Check**: What's the realistic maximum iteration count? Is it gas-feasible?

### FP-6: Severity Inflation
The finding claims CRITICAL but:
- A safety check catches the condition before value loss → MEDIUM at most
- The impact is value leakage, not value theft → MEDIUM
- Only an admin can trigger it (trusted role) → Context-dependent
- The edge case requires specific token types that aren't in scope

**Check**: Re-classify with accurate severity.

### FP-9: Test/Script/Interface-Only
The finding points to code in:
- Test files (test/, t/, and the pack's test-file patterns in `pack.json` `scope.exclude`)
- Deploy scripts (script/, deploy/)
- Interfaces (no implementation)
- Mock contracts

**Check**: Is this production code? If not, discard.

### FP-10: Documented Design Decision
The behavior flagged is intentional:
- Comments explicitly explain why
- The documentation describes this as expected behavior
- It's a known trade-off (e.g., "we accept 1 wei rounding per operation")

**Check**: Read surrounding comments and documentation.

## Cross-Feed Iteration

After initial verification, check if any VERIFIED findings from the Detector reveal state inconsistencies that the State Auditor should re-examine, or vice versa.

If new insights emerge:
1. Flag them as new candidates
2. Apply the same verification process
3. Maximum 2 iteration cycles to prevent endless loops

## Verdict Format

For each candidate, assign ONE verdict and write it as the finding's `status`, using the mapping
in `engine/verdicts.md`:

| Krait verdict | `status` | Required fields |
|---|---|---|
| **TRUE POSITIVE (TP)**: Verified exploitable. Include proof trace. | `verified` | `exploit_trace`, `harm`, `verdict.method`, `verdict.evidence_tag` |
| **LIKELY TRUE (LT)**: Mechanism confirmed but edge-case dependent. Include conditions. | `verified-conditional` | as TP, plus the conditions in `preconditions` |
| **DOWNGRADE**: Real issue but severity is wrong. Specify correct severity. | `downgraded` | new `severity`, `verdict.original_severity`, `verdict.reason` |
| **FALSE POSITIVE (FP)**: Disproven. Specify which FP pattern and why. | `killed` | `verdict.gate` (gate letter, `impact-premise` or `fp-pattern:<id>`), `verdict.reason` |
| **INSUFFICIENT EVIDENCE (IE)**: Cannot prove or disprove. Exclude from report. | `killed` | `verdict.gate: insufficient-evidence`, `verdict.reason` |

`verdict.method` is `code-trace` (Method A), `poc-trace` (Method B), `hybrid` (Method C) or
`executable-poc` (Method D). `verdict.evidence_tag` is `[CODE-TRACE]` unless an executed PoC
produced `[POC-PASS]` / `[POC-FAIL]` (tiers in `engine/verdicts.md`, "Evidence tags").

## Output

Write a JSON array to `A/verdicts.json`; each element conforms to `engine/finding.schema.json`.
It contains **all** candidates from every input file, each with its final `status` — killed ones
included, with `verdict.gate` and `verdict.reason`. Keep each candidate's `id`, `chain`,
`discovery` and `locations`; the reporter assigns final IDs. New candidates from Cross-Feed
Iteration keep the id scheme of the phase that would have produced them (`STATE-<n>` or `D<lens>-<n>`)
continuing after the highest existing number.

Field mapping (Krait verdict field → schema field):

| Krait field | Schema field |
|---|---|
| Verdict | `status` (table above) |
| Severity (original: … — downgraded because …) | `severity`; `verdict.original_severity` and `verdict.reason` when changed |
| File | `locations[]` |
| Harm | `harm` (`who`, `loses_what`, `magnitude`) — required for every non-killed finding |
| Verification Method | `verdict.method` |
| Proof | `exploit_trace` (concrete exploitation trace with values, or the complete code trace) |
| Impact | `harm.magnitude` and `description` |
| Root Cause | `root_cause` |
| Reason (killed) | `verdict.reason` (pattern or gate and why) |
| Step Execution | `audit_trail.step_execution` (`Gates: A=✓ B=✓ C=✓ D=✓ E=✓ F=✓ G=✓ H=✓`) |
| Rules Applied | `audit_trail.rules_applied` |
| Depth Evidence | `audit_trail.depth_evidence` |
| Missing Precondition / Precondition Type (killed: the blocker that makes it invalid) | `preconditions[]` + `audit_trail.missing_precondition` |
| Postconditions Created / Postcondition Types (carry from detector/reasoner) | `postconditions[]` + `audit_trail.postconditions_created` |
| Who Benefits | `audit_trail.who_benefits` |

Example element (verified):

```json
{
  "id": "DB-1",
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
    "2. Attacker calls withdraw(100): line 143 sets shares[attacker] = 0, line 146 transfers 100 tokens and enters the attacker's callback.",
    "3. In the callback totalAssets = 900 and totalShares = 1000; attacker calls deposit(100) and receives 100 × 1000 / 900 = 111 shares.",
    "4. withdraw resumes and sets totalShares = 1000 - 100 + 111 = 1011 against totalAssets = 1000.",
    "5. Result: attacker's 111 shares redeem for 109.8 tokens after depositing 100; the 9.8-token gain comes from other depositors."
  ],
  "preconditions": [],
  "postconditions": [{"text": "exchange rate permanently understated for other depositors", "type": "STATE"}],
  "verdict": {"gate": null, "reason": "Survived gates A–H; no reentrancy guard on deposit() or withdraw(); trace confirmed with values.", "evidence_tag": "[CODE-TRACE]", "method": "hybrid", "original_severity": null},
  "audit_trail": {
    "step_execution": "Gates: A=✓ B=✓ C=✓ D=✓ E=✓ F=✓ G=✓ H=✓",
    "rules_applied": ["R8:✗(single transaction)", "R10:✓(severity assessed at repeated re-entry)", "R11:✗(no external tokens)", "R12:✓(detector enumerated 2 enablers; both reachable)", "R15:✗(no flash-loan-accessible state)", "R16:✗(no oracle)"],
    "depth_evidence": ["[TRACE:withdraw(100)→callback→deposit(100)→111 shares]", "[BOUNDARY:totalAssets=900 during callback]"],
    "missing_precondition": "",
    "postconditions_created": ["exchange rate permanently understated for other depositors"],
    "who_benefits": "Attacker"
  }
}
```

Example element (killed at Step 0.5 rather than by a gate match):

```json
{
  "id": "DA-2",
  "chain": "<chain>",
  "title": "setFeeRate() accepts zero",
  "severity": "Medium",
  "category": "input-validation",
  "status": "killed",
  "locations": [{"file": "src/FeeController.<ext>", "line_start": 31, "unit": "FeeController", "function": "setFeeRate"}],
  "discovery": {"phase": "detect", "lens": "A", "mindset": "edge-case", "consensus": "single", "unit": null},
  "description": "setFeeRate() does not reject a zero fee rate.",
  "verdict": {"gate": "impact-premise", "reason": "Harm: MECHANISM-ONLY. The candidate states that setFeeRate() accepts zero, but names no user class and no consequence of a zero fee.", "evidence_tag": null, "method": null, "original_severity": null},
  "audit_trail": {
    "step_execution": "Gates: A=✓ B=✓ C=✓ D=✗(Impact Premise) E=✓ F=✓ G=✓ H=✓",
    "rules_applied": ["R10:✓", "R11:✗(no external tokens)", "R16:✗(no oracle)"],
    "depth_evidence": [],
    "missing_precondition": "No user class loses anything when the fee is zero",
    "postconditions_created": [],
    "who_benefits": "No one"
  }
}
```

The new **Step Execution / Rules Applied / Depth Evidence / Precondition / Postcondition** fields are the **methodology audit trail** — see `engine/phases/detect.md` Step 6 for full definitions. Critic's `Step Execution` lists the 8 kill gates (A=Generic Best Practice, B=Theoretical/Unrealistic, C=Intentional Design, D=Speculative, E=Admin Trust, F=Dust, G=Out of Context, H=Publicly Known Issues). For invalid verdicts, the `Missing Precondition` field captures the specific blocker so future chain analysis can search for an enabler that creates it. All six are optional but strongly encouraged.

Then state the summary:
- Total candidates reviewed: X
- True Positives (`verified`): X
- Likely True (`verified-conditional`): X
- Downgraded (`downgraded`): X
- False Positives (`killed` by a gate, the Impact Premise or an FP pattern): X
- Insufficient Evidence (`killed`, `insufficient-evidence`): X

## Final Checks

- "Would a C4 judge accept this?" test
- Post-verification code check: re-read lines, verify quotes match

## Rules

- **Read every line you cite.** Do not trust the candidate's description blindly.
- **Trace inheritance chains completely.** Most FPs come from ignoring parent contracts.
- **Be ruthless.** A finding that "might" be exploitable is NOT verified. Either prove it or discard it.
- **Never add new findings.** Your job is to verify/falsify existing candidates, not find new ones. (Exception: cross-feed iteration can generate new candidates for immediate verification.)
- **Downgrade aggressively.** Many "CRITICAL" findings are actually MEDIUM when you check the actual impact path.
- **Zero false positives on H/M is the goal.** Users trust the report. Every FP destroys credibility.

## Repair pass
Input: the reject list printed by `scripts/validate-findings.py`. For each rejected id, re-open the
code and either supply the missing field (a `file` + `line_start` location, a one-sentence
`harm.who`/`harm.loses_what`, or a concrete step-by-step `exploit_trace`) or, if you cannot,
lower the finding's status/severity per the Impact Premise. A `duplicate-id` reject means two
elements share an id: renumber every repeat after the first to an unused id (`--downgrade` never
fixes this). Edit `A/verdicts.json` in place.
Never invent line numbers or traces you did not verify in the code.
