# State Auditor — State Inconsistency & Coupled Pair Analysis

> Phase 8 of the ChainSec pipeline (`engine/pipeline.md`). Runs after Detection (and Rescan / per-unit), cross-feeds with it. Skipped with `--quick`.

Reads: `A/recon.md`, `A/facts.json` (`storage_writes`), `A/candidates/detect.json`
Writes: `A/candidates/state.json`

`A` = `TARGET/.audit/<chain>/`. Read `A/recon.md` and `A/candidates/detect.json` before starting.

## Purpose

Find bugs where operations mutate one piece of coupled state without updating dependent counterparts, causing silent data corruption. This is a STRUCTURAL analysis that catches bugs the Feynman interrogation misses — specifically, state desynchronization across functions and contracts.

## Core Concept

**Coupled state pairs** are storage values that maintain a required relationship (invariant). When one changes without proportional adjustment to its dependent, the invariant breaks silently.

Examples:
- `balance` ↔ `totalSupply` (sum of all balances must equal totalSupply)
- `stakedAmount` ↔ `rewardDebt` (reward calculation depends on both)
- `position.size` ↔ `position.accumulatedFunding` (funding rate depends on size)
- `shares` ↔ `totalAssets` (exchange rate derived from ratio)
- `collateral` ↔ `debt` (health factor derived from both)
- `lpBalance` ↔ `checkpoint` (reward tracking depends on both)

## Eight-Phase Methodology

### Phase 1: Dependency Mapping

Build a **Coupled State Dependency Map** for every contract.

For each storage variable, answer: **"What other storage MUST change when this one changes?"**

Format:
```
Contract: VaultManager
┌─────────────────┬────────────────────┬─────────────────────┐
│ State Variable   │ Coupled With       │ Invariant           │
├─────────────────┼────────────────────┼─────────────────────┤
│ totalDeposits    │ userDeposits[*]    │ sum(userDeposits) = │
│                  │                    │ totalDeposits       │
│ shares[user]     │ totalShares        │ sum(shares) =       │
│                  │                    │ totalShares         │
│ rewardPerToken   │ lastUpdateTime     │ rewardPerToken      │
│                  │                    │ must be fresh       │
│ userRewardDebt[u]│ stakedBalance[u]   │ debt reflects       │
│                  │                    │ current stake       │
└─────────────────┴────────────────────┴─────────────────────┘
```

**Key principle**: If State A and State B are coupled, then EVERY function that writes to A must also write to B (or provably preserve the invariant).

### Phase 2: Mutation Matrix

For each state variable, list EVERY code path that modifies it:

```
State: totalShares
├── mint()          — increments by shares minted
├── burn()          — decrements by shares burned
├── transfer()      — unchanged (internal redistribution)
├── _liquidate()    — decrements by liquidated shares
└── ???             — are there other paths? (admin override, migration, initialize)
```

Start from `A/facts.json` `storage_writes[]` (`unit`, `function`, `file`, `line`, `target`): every
entry whose `target` is the state variable is a direct write. The facts do not cover every path
below (implicit changes through internal calls, callbacks), so read the code for the rest.

Mark uncertain mutation points with `???` — these are PRIMARY audit targets.

Include:
- Direct writes (`totalShares += amount`)
- Increments/decrements
- Deletions (`delete mapping[key]`)
- Implicit changes through internal calls
- Batch operations that modify per-item
- External triggers (callbacks, hooks that modify state)

### Phase 3: Cross-Check Verification

This is the core analysis. For EVERY operation that modifies State A of a coupled pair:

**Does it update ALL dependent states?**

Specifically verify:
- **Full removal**: When an entity is fully removed (burn all shares, close position, full withdrawal), are ALL coupled states reset? Or does orphaned state remain?
- **Partial reduction**: When amount decreases partially, are coupled values proportionally adjusted? Or do they reflect the old full amount?
- **Increase**: When amount increases, do all coupled values propagate correctly?
- **Transfer/migration**: When ownership moves between entities, does ALL coupled state transfer? Or just the primary value?
- **Batch operations**: In loops processing multiple items, is per-iteration coupling maintained?

**Red flag format:**
```
DESYNC CANDIDATE: [function] writes to [State A] but does NOT write to [State B]
- Coupled pair: State A ↔ State B
- Invariant: [what should hold]
- Breaking operation: [the function that only updates one side]
- Consequence: [what happens when invariant is broken]
```

### Phase 4: Operation Ordering Analysis

Within each function, trace the sequential order of state changes (the chain-specific original of
this example: the pack's heuristics.md, section "State audit additions"):

```
function withdraw(amount):
  1. READ  shares[caller]            ← reads coupled state
  2. WRITE shares[caller] -= x       ← updates primary
  3. CALL  token.transfer(...)       ← EXTERNAL CALL
  4. WRITE totalShares -= x          ← updates coupled AFTER external call!
```

Check:
- Are coupled pairs consistent AFTER each step? (Between steps 2 and 4, shares[user] is updated but totalShares isn't → window of inconsistency)
- Could an external call at step 3 observe the inconsistent state?
- Would a re-entrant call between steps 2 and 4 exploit the desync?

### Phase 5: Parallel Path Comparison

Compare functions that perform SIMILAR operations on the same state:

```
┌──────────────┬─────────────┬──────────────┐
│ Operation    │ withdraw()  │ liquidate()  │
├──────────────┼─────────────┼──────────────┤
│ Updates shares│ ✅          │ ✅            │
│ Updates total │ ✅          │ ❌ MISSING!   │
│ Updates debt  │ ✅          │ ❌ MISSING!   │
│ Emits event   │ ✅          │ ❌ MISSING!   │
└──────────────┴─────────────┴──────────────┘
```

If Path A adjusts coupled state but Path B skips it — **that's a finding**.

Compare these pairs:
- `deposit` vs `mint` (both add value)
- `withdraw` vs `redeem` (both remove value)
- `withdraw` vs `liquidate` (both remove, different actors)
- `transfer` vs `transferFrom` (both move value)
- Normal flow vs emergency/admin flow

### Phase 6: Multi-Step User Journey Simulation

Test realistic sequences:

1. `deposit → partial withdraw → claim rewards` — After partial withdraw, are reward calculations still correct?
2. `stake → delegate → undelegate → claim` — Does delegation properly track coupled state?
3. `borrow → repay partial → borrow more → liquidation` — Does each step maintain invariants?
4. `create position → modify → close` — Is ALL state cleaned up on close?

After each step, verify: if a function reads BOTH sides of a coupled pair, would it get consistent values?

### Phase 7: Masking Code Detection

**CRITICAL**: Defensive code patterns that HIDE broken invariants rather than preventing them.

Identify and flag:
- **Ternary clamps**: `x > y ? x - y : 0` — This silences an underflow. Why would x ever be > y? The real bug is WHY the values diverged.
- **Early exits on zero**: `if (amount == 0) return;` — If amount should never be zero at this point, why is it? Masking a rounding bug?
- **Min/max caps**: `Math.min(calculated, available)` — If calculated should never exceed available, why is the cap needed?
- **Chain-specific masking patterns** (swallowed reverts, checked-arithmetic libraries): the pack's fp-patterns.md, section "Masking code examples".

For each masking pattern found:
- What invariant is ACTUALLY broken underneath?
- Which coupled pair desync is being hidden?
- Can the masked condition be triggered in a way that causes value loss (not just a harmless clamp)?

### Phase 8: Cross-Feed from Detector

Read `A/candidates/detect.json` and for each candidate:
- Does it involve a coupled state pair you identified?
- Does the Feynman finding expose a DEEPER state inconsistency?
- Are there additional candidates the Detector missed because they require structural analysis?

Generate NEW candidates based on cross-feed insights.

#### Cross-Feed Iteration (max 2 cycles)

State gaps → why doesn't function X update coupled state Y?
Detector suspects → does this happen during state inconsistency window?
Masking code → what invariant is broken underneath?

## Output

Write a JSON array to `A/candidates/state.json`; each element conforms to
`engine/finding.schema.json`. Write `[]` if you found nothing. The Coupled State Dependency Map
(Phase 1) and the Mutation Matrix (Phase 2) are your working notes: complete them before hunting,
but they are not part of the JSON output — each candidate carries its own pair, breaking operation
and invariant.

Field mapping (Krait state candidate field → schema field):

| Krait field | Schema field |
|---|---|
| `[STATE-XXX]` id | `id`: `STATE-<n>` |
| Title | `title` |
| Severity (CRITICAL / HIGH / MEDIUM / LOW) | `severity` (`Critical` / `High` / `Medium` / `Low`) |
| File / Lines | `locations[]` |
| Coupled Pair, Breaking Operation, Masking Code, Cross-Feed | labeled lines inside `description`: `Coupled Pair: StateA ↔ StateB`, `Breaking Operation: function_name()`, `Masking Code: ...` (if any), `Cross-Feed: <detect candidate id>` (if any) |
| Invariant | `root_cause`, as `Invariant: [what should always hold]` followed by why the breaking operation violates it |
| Breaking Scenario | `exploit_trace` (one string per step) |
| Step Execution | `audit_trail.step_execution`, listing Phases 1–8 |
| Rules Applied | `audit_trail.rules_applied` |
| Depth Evidence | `audit_trail.depth_evidence` |
| Missing Precondition / Precondition Type | `preconditions[]` + `audit_trail.missing_precondition` |
| Postconditions Created / Postcondition Types | `postconditions[]` + `audit_trail.postconditions_created` |
| Who Benefits | `audit_trail.who_benefits` |
| Status: UNVERIFIED | `status: "candidate"` |

Also set `chain`, `category` (e.g. `state-desync`), `discovery: {"phase": "state", ...}` and
`vulnerable_code` (the breaking lines; use the pack's `code_fence` when rendering).

Example element:

```json
{
  "id": "STATE-1",
  "chain": "<chain>",
  "title": "liquidate() burns shares without reducing totalShares",
  "severity": "High",
  "category": "state-desync",
  "status": "candidate",
  "locations": [{"file": "src/VaultManager.<ext>", "line_start": 210, "line_end": 224, "unit": "VaultManager", "function": "liquidate"}],
  "discovery": {"phase": "state", "lens": null, "mindset": "accountant", "consensus": null, "unit": "VaultManager"},
  "description": "Coupled Pair: shares[user] ↔ totalShares\nBreaking Operation: liquidate()\nMasking Code: previewRedeem() clamps with x > y ? x - y : 0\nCross-Feed: DB-4\nliquidate() zeroes the liquidated user's shares but never decrements totalShares, so the share price used by every later redeem is diluted.",
  "root_cause": "Invariant: sum(shares) = totalShares. liquidate() writes shares[user] but not totalShares, so after any liquidation totalShares exceeds the real share supply.",
  "vulnerable_code": "shares[user] = 0;\ncollateral[user] = 0;\n// totalShares not updated",
  "harm": {"who": "all remaining depositors", "loses_what": "the share of assets backing the phantom shares, which can never be redeemed", "magnitude": "liquidated shares / totalShares of the vault's assets per liquidation"},
  "exploit_trace": [
    "1. Vault holds 1000 assets, totalShares = 1000; user U holds 100 shares.",
    "2. U is liquidated; liquidate() sets shares[U] = 0, totalShares stays 1000.",
    "3. The liquidator removes U's 100 assets; the vault now holds 900 assets for 900 real shares.",
    "4. A depositor redeems 100 shares at 900/1000 = 0.9 assets per share and receives 90 instead of 100.",
    "5. Result: 10% of every remaining depositor's assets are stranded behind phantom shares."
  ],
  "preconditions": [{"text": "at least one position becomes liquidatable", "type": "STATE"}],
  "postconditions": [{"text": "share price permanently understated", "type": "STATE"}],
  "audit_trail": {
    "step_execution": "Phases: 1=✓ 2=✓ 3=✓ 4=✓ 5=✓ 6=✗(N/A: not multi-step) 7=✓ 8=✓",
    "rules_applied": ["R8:✓(totalShares cached across liquidate and redeem)", "R10:✓(severity at many liquidations)", "R11:✗(no external tokens)", "R12:✓(enumerated 3 writers of shares)", "R15:✗(no flash-loan-accessible state)", "R16:✗(no oracle dependency)"],
    "depth_evidence": ["[TRACE:liquidate(U)→shares[U]=0, totalShares unchanged]", "[VARIATION:liquidated shares 1→500 → loss grows linearly]"],
    "missing_precondition": "",
    "postconditions_created": ["share price permanently understated"],
    "who_benefits": "No attacker profit; depositors lose, dilution accrues to no one"
  }
}
```

The last six fields are the **methodology audit trail** — see `engine/phases/detect.md` Step 6 for full definitions of Step Execution, Rules Applied (R8/R10/R11/R12/R15/R16), Depth Evidence tags, and precondition/postcondition fields. State-auditor "Step Execution" lists Phases 1–8 from this file (Phase 1 = Dependency Map, Phase 2 = Mutation Matrix, etc.). All six are optional but strongly encouraged.

## Rules

- **Map ALL state before hunting.** Complete dependency map is mandatory before checking functions.
- **Every mutation path matters.** ALL functions modifying a state must update coupled state. Not just the "main" ones.
- **Partial operations are the primary source.** Partial withdrawals, partial liquidations, partial reductions are where coupled state updates are most commonly forgotten.
- **Compare parallel paths religiously.** If `withdraw` updates X but `liquidate` doesn't, that's almost always a bug.
- **Defensive code is a RED FLAG, not a safety net.** Clamping and try/catch hide broken invariants.
- **Evidence-based only.** Each finding must specify: the coupled pair, the breaking operation, a concrete trigger sequence, and the downstream consequence.
