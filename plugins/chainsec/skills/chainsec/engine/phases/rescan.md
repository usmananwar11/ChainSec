# Rescan — Second Pass with Exclusion List (B4)

> Phase 6 of the ChainSec pipeline (`engine/pipeline.md`). Runs after Detection, before per-unit and State Analysis.
> *(Methodology adapted from PlamenTSV/plamen, MIT — `phase3b-rescan-prompt.md`.)*

Reads: `A/candidates/detect.json`, `A/recon.md`, `A/risk.json`
Writes: `A/candidates/rescan.json`

`A` = `TARGET/.audit/<chain>/`.

## Purpose

Counter **attention saturation**. A first pass fixates on the most prominent bug in each file and under-reads everything around it. This phase re-runs broad analysis while explicitly told what pass 1 already found, so attention lands in the gaps instead of on the same bug a second time.

This is a **recall** phase. Everything it surfaces still goes through the Critic's kill gates — the zero-FP bar is unchanged.

## Hard exit rule (check FIRST)

Count pass 1 candidates (`A/candidates/detect.json`) above Informational severity (`severity` other than `Info`).

- **0 above Info** → **SKIP this phase entirely.** With no exclusion list there is nothing to diverge from; re-running the same broad analysis pays twice for one answer. Write `[]` to `A/candidates/rescan.json`, state one line "skipped: pass 1 produced no candidates above Info" and move on.
- **≥ 1 above Info** → proceed.

## Step 1: Build the Exclusion List

From `A/candidates/detect.json`, extract ONE LINE per candidate (`[severity] file:line_start — title`):

```
- [HIGH] src/Vault.<ext>:142 — withdraw() skips reward checkpoint
- [MEDIUM] src/Pool.<ext>:88 — fee applied on gross instead of net
```

Keep it terse. The agent needs to *recognise* a duplicate, not re-read the original analysis. Full descriptions both blow the budget and anchor the second pass on the first pass's conclusions.

## Step 2: Identify Blind Spots

List every scope file (`A/risk.json` `files[].file`) that produced **zero** candidates in pass 1.

**These are the priority targets.** A file with no findings is UNDER-ANALYZED, not clean — 13% of all historically missed findings were in areas an earlier pass explicitly marked safe.

## Step 3: Run the Rescan

Run **2 passes** over the codebase, each covering roughly half the scope files with deliberate overlap. Broader scope than pass 1 — you are looking for what falls *between* the areas pass 1 examined closely.

For each pass, hold this framing:

> A first pass already analyzed this code and found the listed issues. Your job is to find what it MISSED. You are not re-checking its work.

### What attention saturation hides

Focus on the classes that a fixated first pass systematically misses:

1. **Cross-function state inconsistencies** — function A assumes an invariant that function B breaks
2. **Asymmetric operations** — the deposit path handles X but the withdraw path does not
3. **Parameter encoding mismatches between paired functions** — create/consume, lock/unlock, deposit/refund, encode/decode. Do both sides use the same inputs in the same order?
4. **Economic assumptions violated at the edges** — first user, last user, zero state, max state
5. **Time-dependent state going stale** under a specific operation sequence
6. **The quiet file next to the interesting one** — the helper, the library, the base contract nobody opened

Do NOT re-analyze the patterns pass 1 already covered. Look in the gaps BETWEEN what was analyzed.

## Quality gates

- Every finding needs a specific `file:line` (a `locations[]` entry with `file` and `line_start`). No location → discard it yourself; the pipeline will drop it anyway.
- If a candidate matches an exclusion-list entry on **location AND root cause**, skip it silently.
- Same area, different exploit path = **not** a duplicate. Report it.
- Do not report generic best practice ("use a safe-transfer wrapper", "add events", "missing zero-address check"). Kill gate A removes those unconditionally, so they only cost budget.
- Record concrete values you tested as depth-evidence tags (`audit_trail.depth_evidence`): `[BOUNDARY:reserve=0]`, `[TRACE:redeem(MAX)→revert L88]`.

## Output

Write a JSON array to `A/candidates/rescan.json`; each element conforms to `engine/finding.schema.json`.
Use the standard candidate format (field mapping in `engine/phases/detect.md` Step 6), with IDs
`RS-1`, `RS-2`, …, `status: "candidate"` and `discovery.phase: "rescan"`.

Example element:

```json
{
  "id": "RS-1",
  "chain": "<chain>",
  "title": "refund() decodes the order fields in a different order than create() encodes them",
  "severity": "Medium",
  "category": "encoding-mismatch",
  "status": "candidate",
  "locations": [
    {"file": "src/Escrow.<ext>", "line_start": 77, "line_end": 84, "unit": "Escrow", "function": "refund"},
    {"file": "src/Escrow.<ext>", "line_start": 40, "line_end": 46, "unit": "Escrow", "function": "create"}
  ],
  "discovery": {"phase": "rescan", "lens": null, "mindset": "spec-auditor", "consensus": null, "unit": null},
  "description": "Discovery: rescan class 3 (parameter encoding mismatch). create() hashes (buyer, seller, amount) but refund() recomputes the key as (seller, buyer, amount), so a refund looks up a different order record.",
  "root_cause": "The paired encode/decode functions disagree on field order, so refund() never finds the stored order.",
  "vulnerable_code": "bytes32 key = hash(order.seller, order.buyer, order.amount);",
  "harm": {"who": "buyers of expired orders", "loses_what": "their escrowed payment, which can no longer be refunded", "magnitude": "the full order amount per expired order"},
  "exploit_trace": [
    "1. Buyer creates an order for 50 tokens; create() stores it under hash(buyer, seller, 50).",
    "2. The order expires; buyer calls refund(order).",
    "3. refund() computes hash(seller, buyer, 50), finds no record and reverts at line 81.",
    "4. Result: the 50 tokens stay locked in the escrow with no other exit path."
  ],
  "preconditions": [{"text": "an order reaches expiry without settlement", "type": "TIMING"}],
  "postconditions": [{"text": "escrowed funds are permanently locked", "type": "BALANCE"}],
  "audit_trail": {
    "step_execution": "Rescan: pass 1=✓ pass 2=✓",
    "rules_applied": ["R8:✗(no cached parameter)", "R10:✓(assessed with every order expired)", "R11:✗(no external tokens)", "R12:✓(refund is the only exit path)", "R15:✗(no flash-loan-accessible state)", "R16:✗(no oracle dependency)"],
    "depth_evidence": ["[TRACE:refund(expired order)→revert L81 \"unknown order\"]"],
    "missing_precondition": "",
    "postconditions_created": ["escrowed funds are permanently locked"],
    "who_benefits": "No one; buyers lose access to their funds"
  }
}
```

Then state: `Rescan complete: N new candidates ({H} high, {M} medium, {L} low)`.

## Non-goals

- Do NOT re-verify or overturn pass 1's findings. That's the Critic's job, then the Reviewer's.
- Do NOT deepen an existing candidate. If you find more evidence for a known finding, note it as a one-liner under `Reinforced:` after the `Rescan complete` line — it strengthens the existing candidate, it is not a new one, and it does not go into `A/candidates/rescan.json`.
