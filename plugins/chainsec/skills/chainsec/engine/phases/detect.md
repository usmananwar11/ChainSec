# Detection — Feynman Interrogation + Pattern-Aware Detection

> Phase 5 of the ChainSec pipeline (`engine/pipeline.md`). Runs after Recon.

Reads: `A/recon.md`, `A/known-issues.md`, `A/risk.json`, `A/facts.json` (plus `A/analyzers/*.md` if present)
Writes: `A/candidates/detect-<lens>.json` (one lens run, lens A, B, C or D), `A/candidates/detect.json` (consensus merge + Pass 3 sweep)

`A` = `TARGET/.audit/<chain>/`. This file has three sections:
- **Lens run** — what one lens subagent does (pipeline row 5, one per lens A–D, in parallel).
- **Consensus merge** — what the orchestrator does with the four lens files.
- **Pass 3 sweep** — the mechanical "What's Missing" sweep, run after the merge and appended to `A/candidates/detect.json`.

## Purpose

Find vulnerability CANDIDATES through systematic first-principles interrogation of every significant function, enhanced with knowledge of 40+ real exploit patterns. This phase maximizes RECALL — cast a wide net. The Critic phase will filter false positives later.

## Core Philosophy

The core philosophy and the four lens definitions (focus lists, mindset questions, inline modules, mandatory heuristics, module-to-lens mapping, cross-cutting perspective) are in `engine/mindsets.md`. Read it before you start.

---

## Lens run

You are ONE lens (`A`, `B`, `C` or `D`, from your prompt). You run Steps 1–6 below restricted to
your lens — its focus list, mindset questions, inline modules and mandatory heuristics from
`engine/mindsets.md`, plus the activated modules that inject into it — over the files your tier
strategy assigns. Write your candidates to `A/candidates/detect-<lens>.json`.

### Step 1: Load Context

Read `A/recon.md` and `A/known-issues.md` to understand:
- **File Risk Table** — The ranked table of files with RISK_SCORE and Tier assignments. This is your execution contract. Follow the tiers. The same tiers are in `A/risk.json` (`files[].tier`, `size`).
- Protocol type and relevant checklists
- Fund flows and trust boundaries
- **Known/acknowledged issues** — Do NOT generate candidates for these (Gate H)
- **Fork origin** — If this is a fork, what is the original? Inherited behavior = intentional design (Gate C)
- **Token context** — What SPECIFIC tokens does this protocol use? Every token-behavior finding must name a specific token from this list (Gate B)
- **Detection primer** — Read the protocol-specific primer(s) listed under "Detection Primer" in recon.md (core-relative paths). The primer's CRITICAL checks are your DEEP DIVE priorities.
- **Activated modules** — Read the "Activated Modules" table in recon.md. For each listed module that injects into your lens (module-to-lens table in `engine/mindsets.md`; a module's `**Inject into**` header is authoritative), read the full file at its core-relative path. These contain structured tables and step-by-step methodology. Spend 2-3x more time on activated modules vs general heuristics.

**Also read `A/facts.json`** — these are structural facts from the pack's extractor (compiler-verified when `mode` is `compiler`; pattern-matched and lower confidence when `mode` is `regex`):
- **`units[].parents`** (the inheritance tree): Use to verify modifier presence. A "missing" modifier may exist in a parent listed here. Do NOT report missing modifiers without checking the full inheritance chain.
- **`entry_points[]`** (the function registry: `visibility`, `mutability`, `guards`): Use to pre-populate the Function-State Matrix (Step 2). Copy verified function signatures, visibility, mutability, and modifiers — don't re-derive from scratch.
- **`external_calls[]`** (the call graph): Use during Pass 2 cross-contract reads to identify EXACTLY which files to open for each external call. Do NOT guess from interface names.
- **`auth_sites[]`** and `entry_points[].guards` (modifier usage): Cross-reference which functions use which modifiers. Siblings missing a modifier that others have = candidate.
- Do NOT override compiler-mode facts with your own inference. If the facts say function X has modifier Y, it has modifier Y.

**Also read `A/analyzers/*.md` if any exist** — these are static analysis findings from the pack's analyzers:
- Use as ADDITIONAL SIGNAL, not as auto-reported findings
- If an analyzer finding overlaps with one of your candidates → increased confidence
- If an analyzer flagged something you missed → investigate that area during Pass 2 lenses (reentrancy → Lens C, access control → Lens A, precision → Lens D)
- Focus on HIGH/MEDIUM analyzer findings only; ignore informational/low

**Apply the Detection pre-filter in `engine/kill-gates.md`** before recording any candidate.

### ADAPTIVE PASS STRATEGY

**The codebase size determines analysis depth. Count scope files from the recon.md risk table** (`A/risk.json` `size`: SMALL, MEDIUM or LARGE; each file's `tier`: DEEP = Tier 1, STANDARD = Tier 2, SCAN = Tier 3):

#### SMALL codebase (≤15 scope files): Full 3-Pass
All files get Tier 1 treatment. Every file gets full analysis + cross-contract read + what's-missing sweep.

#### MEDIUM codebase (16-40 scope files): Tiered 3-Pass
Follow the Tier 1/2/3 assignments from recon.md risk table exactly.
- **Tier 1** (top 5 by RISK_SCORE): Full 3-pass treatment with cross-contract reads
- **Tier 2** (next 10): Standard Pass 1 analysis only
- **Tier 3** (remaining): Quick scan — function signatures + obvious patterns only

#### LARGE codebase (40+ scope files): Budget-Controlled Triage
**You CANNOT deeply analyze 40+ files. Do not try. Instead:**
1. **Tier 3 files**: Read the FULL file but only analyze: function signatures, modifiers, access control, state-writing lines. ~1 min per file.
2. **Tier 2 files**: Standard Pass 1 (Function-State Matrix + Feynman on public/external only). ~2 min per file.
3. **Tier 1 files** (top 5): Full deep dive with cross-contract reads, line-by-line, all modules. **Spend 80% of total analysis time here.**
4. **CRITICAL promotion rule**: After Tier 1 analysis, check if any Tier 2/3 file is called by a Tier 1 file. If yes, promote to Tier 1 for cross-contract read. Max 3 promotions.

**FILE COVERAGE GUARANTEE**: Every scope file MUST be read at least once. Never skip a file because it "looks like a simple wrapper." 28% of missed findings in shadow audits were in files the agent never opened.

---

**Pass 1 — Tiered Scan:**
For Tier 1/2 files: apply Function-State Matrix (Step 2), Feynman Interrogation (Step 3), and Heuristic Triggers (Step 4). For Tier 3 files: scan function signatures and flag obvious patterns only. Record candidates.

**Pass 1→2 Handoff — Compile the Pass 1 Brief (MANDATORY):**

Before starting Pass 2, compile ALL Pass 1 candidates into a structured brief:
```
PASS 1 BRIEF:
- Candidates found: [list with file, line, severity, one-line summary]
- Files with NO candidates: [list — these need extra scrutiny in Pass 2]
- Suspicious areas flagged but not promoted to candidate: [list]
- Analyzer findings NOT yet covered by a candidate: [list from A/analyzers/*.md]
```

This brief is the INPUT to every Pass 2 lens. It ensures Pass 2 is INFORMED, not blind. The highest-impact findings in competitive benchmarks came from informed second passes (Ross 21-tool study: the "composite super-prompt" that fed prior results into a second pass found the single highest-severity finding that no individual tool caught alone).

In ChainSec each lens subagent runs its own Pass 1 and compiles its own brief, then runs Pass 2 for its lens with that brief as input.

**ANTI-ANCHORING RULE**: The brief tells you what was found — it does NOT tell you what is safe. If Pass 1 marked an area "no issues found," Pass 2 MUST NOT skip that area. Pass 1's "safe" verdicts are HYPOTHESES, not facts. 13% of all missed findings were in areas explicitly marked safe. Treat "no candidates in file X" as "file X is UNDER-ANALYZED," not "file X is clean."

**Pass 2 — Parallel Lens Deep Dive (Tier 1 files ONLY, max 5):**

Re-read the Tier 1 files from the recon.md risk table. Each lens receives the **Pass 1 Brief** as context. Each lens has TWO jobs:
1. **Validate & deepen**: For Pass 1 candidates in this lens's domain, re-examine with fresh eyes. Can you strengthen the exploit trace? Find a deeper root cause? Identify a more severe impact?
2. **Find what Pass 1 missed**: The brief tells you what was already found. Focus your time on areas/files where Pass 1 found NOTHING — those are the blind spots.

Your lens definition — its "From Pass 1 Brief" priority, activated and inline modules, mandatory heuristics, the four mindset questions and the "Focus EXCLUSIVELY on" list — is in `engine/mindsets.md`. If a module is activated and maps to your lens, you MUST execute the module's full methodology (structured tables, step-by-step checks — not just skim).

**Targeted analysis modules per lens** (Step 5 below). Krait's orchestrator assigns them as:

| Lens | Step 5 modules |
|---|---|
| A — Access Control, State & Governance | H, L, R, W |
| B — Value Flow & Economic Logic | D, I, K, O, V |
| C — External Interactions & Cross-Contract | A, C, J, P, S |
| D — Edge Cases, Math & Standards | B, E, F, G, M, X |

Modules N, Q and T are not assigned to a lens by Krait: every lens applies them.

**SAFE Verdict Challenge (applies to ALL lenses):** For every area verified as "safe," you MUST write: (a) the SPECIFIC invariant verified, (b) at least 3 edge cases explicitly checked. If you can't name 3 edge cases → not verified thoroughly enough. **13% of missed findings were in areas explicitly marked "safe."**

**Parameter flow tracing (during Lens C or D):** Pick 3 most critical params. Trace from entry through ALL internal calls. Where is validation missing?

Record any additional candidates from the deep dive.

### Step 2: Build Function-State Matrix

**If `A/facts.json` has `entry_points`**: Start from them. Copy the verified function signatures, visibility, mutability, and modifiers (`guards`). You only need to ADD: which state variables each function reads/writes (`storage_writes` gives the writes; reads are not in the facts) and any guards beyond modifiers (require/assert statements).

**If the facts have no entry points for a file**: Build from scratch by reading each contract.

For EACH core contract (skip libraries, interfaces, test files), build:

| Function | Visibility | Reads | Writes | Guards | External Calls | Payable? |
|----------|-----------|-------|--------|--------|----------------|----------|

This matrix is your map. It reveals:
- Functions that WRITE state but have NO guards
- Functions that make EXTERNAL CALLS after state changes (reentrancy)
- Functions that READ from external sources without validation (oracle trust)
- Pairs of functions that touch the same state (consistency requirements)

### Step 3: Systematic Interrogation

For every entry point (external/public function), apply these seven question categories. Not every question applies to every function — use judgment to focus on high-risk areas.

#### Category 1: PURPOSE — Why does this code exist?

- **Q1.1**: What invariant does this line/check protect? If you can't answer → suspicious.
- **Q1.2**: What breaks if I delete this line? Dead code, missing dependency, or critical guard?
- **Q1.3**: What specific attack motivated this check? If no clear attack → may be cargo-culted.
- **Q1.4**: Is this check SUFFICIENT? A `> 0` check doesn't prevent dust griefing. A `!= address(0)` doesn't prevent wrong-but-valid addresses.

#### Category 2: ORDERING — What if I move this?

- **Q2.1**: What if state-changing code moves BEFORE validation? → Check-effects-interactions violation.
- **Q2.2**: What if it moves AFTER downstream code? → Stale state read.
- **Q2.3**: Where is the FIRST state write? Where is the LAST state read? Is there a gap where external calls happen between them?
- **Q2.4**: If the function reverts halfway, what state persists? (Events emitted before revert are still logged; side effects from external calls may persist.)
- **Q2.5**: Can the ORDER in which users call this function matter? → Front-running, race conditions.
- **Q2.6 [CEI MANDATORY CHECK]**: For EVERY external call (transfer, safeTransfer, call, delegatecall), list ALL state updates. Are ALL state updates BEFORE the external call? If ANY state update (burn, balance decrement, flag reset) happens AFTER an external call → CEI violation → reentrancy candidate. This is the #1 missed HIGH across shadow audits.

#### Category 3: CONSISTENCY — Why does A have it but B doesn't?

- **Q3.1**: If function A has an access guard, do ALL functions modifying the same state have guards?
- **Q3.2**: If `deposit()` validates parameter X, does `withdraw()` validate the corresponding parameter? Paired operations MUST match.
- **Q3.3**: If one function checks for zero amounts, do sibling functions?
- **Q3.4**: If one function emits an event on state change, do all functions changing the same state? Missing events break off-chain tracking.
- **Q3.5**: Is overflow/underflow protection consistent across all arithmetic paths?
- **Q3.6 [TRANSFER STATE CHECK]**: When a token/NFT/position transfers between users, does ALL associated state (staking, rewards, risk, cooldowns) transfer or properly reset? If `transfer()` moves the token but not the staking data → desync.
- **Q3.7 [ACCESS CONTROL EXHAUSTIVE CHECK]**: List EVERY public/external function that writes state. For each: WHO can call it? Is that the right set of callers? Especially check: checkpoint/sync functions (often accidentally permissionless), functions that should be admin-only but aren't, functions that should validate the caller against a parameter but don't. (Chain wording: the pack's heuristics.md, section "Detector modules", "Question additions".)
- **Q3.8 [REWARD HARVEST CHECK]**: For EVERY function that changes a user's stake, balance, lock duration, or position — does it harvest/checkpoint accrued rewards FIRST? If `setLockDuration()` changes the lock but doesn't harvest pending rewards → user loses accrued rewards or games the system.
- **Q3.9 [PAIRED OPERATION SYMMETRY]**: For every setter, is there an inverse? `lock`↔`unlock`, `delegate`↔`undelegate`, `approve`↔`disapprove`, `add`↔`remove`. If one side is missing or has different constraints → stuck state.

#### Category 4: ASSUMPTIONS — What is implicitly trusted?

- **Q4.1**: What does this assume about the CALLER? (Identity, authorization, contract vs EOA)
- **Q4.2**: What does it assume about EXTERNAL DATA? (Token behavior, oracle freshness, API responses)
- **Q4.3**: What does it assume about CURRENT STATE? (Not paused, initialized, non-empty, not migrated)
- **Q4.4**: What does it assume about TIME/ORDERING? (block.timestamp can be manipulated ±15s; events may arrive out-of-order on L2s)
- **Q4.5**: What does it assume about PRICES/RATES? (Can they be stale, zero, max, or manipulated within one tx?)
- **Q4.6**: What does it assume about INPUT AMOUNTS? (What if 0? What if 1 wei? What if type(uint256).max?)

#### Category 5: BOUNDARIES & EDGE CASES

- **Q5.1**: First call with empty state? (First depositor, division-by-zero, share inflation, uninitialized mappings)
- **Q5.2**: Last call draining everything? (Dust trapped, rounding errors on final withdrawal, totalSupply == 0)
- **Q5.3**: Called twice in rapid succession? (Re-initialization, double-spending, nonce reuse)
- **Q5.4**: Two different functions called atomically? (Cross-function invariant violations, flash loan composability)
- **Q5.5**: Self-referential inputs? (Token A == Token B, sender == receiver, contract calling itself)
- **Q5.6 [MATH BOUNDARY CHECK]**: For every formula with configurable parameters (alpha, multiplier, weight), verify behavior at ALL boundary values: parameter=0, parameter=1, parameter=MAX, input=0, input=1. Especially: `x^0 should always be 1` (not 0), `x^1 should be x`, and division by zero should be impossible. Early-exit conditions like `if (x == 0) return 0` may be WRONG at specific parameter values.
- **Q5.7 [EPOCH/PERIOD BOUNDARY CHECK]**: For time-based systems (voting, rewards, locks): what happens at EXACTLY the epoch boundary? What if a user acts in the last second of an epoch vs the first second of the next? Can a user get rewards for an epoch they weren't active in? Can they vote/act after their lock expires but before the checkpoint runs? Is the epoch length enforced or just assumed (e.g., must a deposit last a FULL epoch to earn rewards)?

#### Category 6: RETURN VALUES & ERROR PATHS

- **Q6.1**: Can the caller IGNORE the return value? Is error handling forced by the language?
- **Q6.2**: What PERSISTS on the error path? Side effects before revert?
- **Q6.3**: Can external calls FAIL SILENTLY? (Chain examples: the pack's heuristics.md, section "Detector modules", "Question additions".)
- **Q6.4**: Is there a code path with NO return and NO error? (Missing else branch, uncovered enum case)

#### Category 7: EXTERNAL CALLS & CROSS-TX STATE

**Within one transaction:**
- **Q7.1**: If external call moves BEFORE state update → can callee exploit stale state?
- **Q7.2**: If external call moves AFTER → what changes? Original ordering may expose window.
- **Q7.3**: What can the CALLEE do with current state at call time? (Re-enter, read manipulated values, call other functions)
- **Q7.4**: What state MUST be updated before each external call? (Checks-effects-interactions)

**Across transactions:**
- **Q7.5**: Does the second call behave correctly given state from the first? (Rounding compounds, totals diverge)
- **Q7.6**: Does tx T2 revert/succeed unexpectedly after T1? (State drift, impossible conditions)
- **Q7.7**: Does accumulated state over many calls create unreachable conditions? (Dust accumulation, precision loss, ceiling hits)
- **Q7.8**: Can an attacker SEQUENCE transactions adversarially? (Normal single-call use works fine, but creative sequencing breaks invariants)

#### Category 8: EXTERNAL PROTOCOL INTEGRATION

When the contract integrates with external protocols (Convex, Aave, Uniswap, Chainlink, etc.):

- **Q8.1**: Can ANYONE call the external protocol's functions on behalf of this contract? (e.g., Convex getReward is permissionless — anyone can claim rewards for any address. If the contract assumes only IT triggers reward claims, an attacker can front-run and break the flow.)
- **Q8.2**: What happens if the external protocol SHUTS DOWN? (Pool shutdown, market deprecation, contract pause.) Does our function revert? Is there a recovery path?
- **Q8.3**: What happens if the external protocol CHANGES OPERATORS or MIGRATES? (e.g., CVX.mint() silently returns without minting if operator changes. If the contract calculates expected mint amount and then tries to transfer it → revert.)
- **Q8.4**: Does the contract ASSUME a return value or side effect from the external protocol? What if that side effect silently doesn't happen? (Silent no-ops are worse than reverts — the contract continues with wrong assumptions.)
- **Q8.5**: Is the external protocol UPGRADEABLE? If yes, ANY assumption about its behavior can break after an upgrade. Flag hardcoded assumptions.

#### Category 9: DERIVED CLASS & OVERRIDE COMPLETENESS

When a contract inherits from a base or implements hooks/callbacks:

- **Q9.1**: Does the derived class enforce ALL invariants from the parent? List every invariant the parent establishes and verify the child maintains each one.
- **Q9.2**: If the parent has N hook points, does the child implement ALL of them? A missing hook means that code path bypasses the child's logic.
- **Q9.3**: For authorization patterns: if function A checks `isAuthorized`, do ALL similar functions (B, C, D) also check? Compare every function in the same category.
- **Q9.4**: For fixed-term/time-locked patterns: can operations happen AFTER the term expires that shouldn't? Check every state-changing function against time boundaries.

### Step 4: Apply Audit Heuristics

**Read `domains/defi/heuristics.md`** — the chain-agnostic trigger-based checks, each extracted from
a real missed finding or a real exploit. **Read the pack's heuristics.md** (`chains/<chain>/heuristics.md`) —
its core heuristics and the "Extended heuristics" section, further vectors from open-source
community sources.

These are TRIGGERS, not a checklist to recite. For each file: match the trigger against the
code actually in front of you, then apply the check. A heuristic whose trigger is absent
costs nothing to skip; a heuristic whose trigger is present and skipped is how findings get
missed.

The mandatory-when-triggered set (each cost Krait a real finding in a prior shadow audit):
`MODIFIER-01` (sibling modifier diff), `CONST-01` (wrong constant / magic number),
`GAUGE-01` (removal unwind safety), `MISSING-01/02` (missing unsetters, restriction gaps),
`ECON-01/02` (circular collateral, liquidation profitability).

Per-lens mandatory heuristics are listed under each lens in `engine/mindsets.md`.

### Step 5: Targeted Analysis Modules (MANDATORY)

These modules address specific bug classes consistently missed by general interrogation. Apply each one assigned to your lens (table in Pass 2 above).

#### Module A: Untrusted Recipient Analysis
For every native-asset/token transfer to an address that is NOT the caller or a known trusted protocol address (chain wording: the pack's heuristics.md, section "Detector modules"):
1. Can the recipient reenter during the transfer callback? Map reachable functions and stale state.
2. Can the recipient revert and permanently DOS the function?
3. Is the same external source queried twice in one function? Can the value change between queries?
4. If a fee is added to a cost variable, does the corresponding transfer ALWAYS execute? Or is it conditional (e.g., `if recipient != address(0)`) while the cost is unconditional?

#### Module B: Type Cast Safety
→ See the pack's heuristics.md, section "Detector modules".

#### Module C: Transfer Order / Implicit Flash Loans
For functions involving both incoming and outgoing transfers:
1. Are assets transferred OUT before payment comes IN?
2. During the callback window, can the recipient use the asset (as collateral, for voting, etc.)?
3. Compare cost of this implicit flash loan vs explicit flashLoan() fee. If cheaper → bypass.

#### Module D: Fee Consistency Cross-Check
List ALL fee-charging functions. For each, compare:
- Fee calculation basis (gross amount? net? feeAmount?)
- Fee destinations (factory? pool? burned?)
- Decimal scaling method
- Zero-fee edge case handling (transfer of 0 attempted?)
Flag ANY inconsistency between functions.

#### Module E: → See `eip-standard-compliance.md` (the pack's module of that name, if the pack ships one)

#### Module F: Token Compatibility
→ See the pack's heuristics.md, section "Detector modules".

#### Module G: Factory/Deployment Patterns
→ See the pack's heuristics.md, section "Detector modules".

#### Module H: → See `domains/defi/modules/access-control-state.md` and the pack's module of the same name, if present

#### Module I: Weight/Proportionality
- When operations involve multiple weighted items: are fees/royalties per-item by weight, or averaged?
- If averaged: high-value items subsidize low-value → underpayment to fee recipients.

#### Module J: → See `domains/defi/modules/external-protocol-integration.md` and the pack's module of the same name, if present

#### Module K: → See `domains/defi/modules/multi-tx-attack.md` and `domains/defi/modules/flash-loan-interaction.md`

#### Module L: Derived Class / Override Completeness

When the protocol uses inheritance, hooks, or plugin patterns:

1. **Hook coverage**: List ALL hook points in the base contract. For each hook, verify the derived contract implements it. A missing hook = bypassed logic.
2. **Invariant inheritance**: List ALL invariants the base contract establishes (access control, time locks, balance checks). For each, verify the derived contract maintains it across ALL its functions.
3. **Authorization consistency**: Extract the authorization check from one function. Search for ALL functions that should have the same check. Flag any that don't.
4. **Time boundary enforcement**: If the protocol has time-bounded operations (fixed terms, vesting, lock periods), check EVERY state-changing function: does it enforce the time boundary? Functions added in derived classes often forget.

#### Module M: State Variable Lifecycle Tracing (MANDATORY for token/scoring systems)

For EVERY storage variable that tracks user state (balances, scores, timestamps, flags):

1. **Full lifecycle map**: Trace the variable through ALL code paths: creation → update → reset → deletion. For each admin function (issue, burn, upgrade, migrate), verify whether this variable is correctly handled.
2. **Mint/Burn/Re-mint cycle**: If a user can lose and regain their position (token burned then re-minted, account deactivated then reactivated), does the variable persist across the gap? Stale timestamps, unreset flags, or leftover balances can be exploited.
3. **Admin function side effects**: When governance issues/burns/upgrades a user's position, are ALL related state variables updated? The `issue()` function might set tokens[user].exists but forget to reset stakedAt, or the `burn()` function might reset score but not accrued interest.
4. **Counter consistency**: If there are counters (pendingUpdates, totalRequired), verify they stay in sync across ALL code paths. `claim()` might increment totalRevocable without updating pendingScoreUpdates.

#### Module N: DoS-to-Exploit Escalation

For EVERY DoS vulnerability found (gas griefing, revert conditions, infinite loops):

1. **Economic weapon**: Can the DoS be combined with another mechanism to create an economic exploit? (e.g., DoS of score updates → attacker keeps favorable old score → accrues outsized rewards)
2. **Selective targeting**: Can the attacker DoS SPECIFIC users while leaving themselves unaffected? (e.g., front-running updateScores for certain users)
3. **Time-sensitive exploitation**: Is there a time window during which the DoS creates a profit opportunity? (e.g., blocking liquidations during a price crash, blocking score updates after alpha change)

#### Module O: Payment/Distribution Flow Tracing (MANDATORY)

For EVERY function that distributes ETH or tokens to multiple recipients:

1. **Trace each payment**: For every outgoing value transfer — WHO is the actual recipient? Is it the contract's owner (deployer), the asset's holder, the caller, or a configured address? Verify the recipient is semantically correct (e.g., auction proceeds should go to token OWNER, not contract OWNER). (Chain transfer primitives and owner/holder accessors: the pack's heuristics.md, section "Detector modules".)
2. **Double payout check**: Can the same recipient receive payment twice? If function pays royalties to artists AND separately pays creators, can the same address appear in both lists?
3. **Payment-on-failure**: When a target call fails, are tokens/ETH properly refunded? Check: is the refund to the right address? Does the refund include ALL tokens (not just native ETH)?
4. **Conditional payment with unconditional cost**: If payment is conditional (`if (recipient != address(0))`) but the cost was already deducted unconditionally, funds are silently lost.

#### Module P: → See `domains/defi/modules/cross-chain-bridge.md` and the pack's module of the same name, if present

#### Module Q: NFT Attribute & Randomness Integrity

For NFT/Gaming protocols with attribute assignment:

1. **User-controlled attributes**: Can users influence their NFT attributes via function parameters? If `redeemMintPass(customAttributes)` lets users pick rarity → they'll always pick the best.
2. **Revert-to-reroll**: If attributes come from on-chain randomness (blockhash, prevrandao), can users revert if they don't like the result? Safe only with commit-reveal or VRF callback.
3. **Type parameter validation**: If per-type limits exist, verify the type parameter matches the actual item type. `reRoll(tokenId, wrongFighterType)` bypassing per-type limits.
4. **Initialization for new generations/collections**: When new NFT collections/generations are created, are ALL required mappings initialized? (numElements, maxSupply, etc.)

#### Module R: → See `domains/defi/modules/governance-voting.md` and the pack's module of the same name, if present

#### Module S: Cross-Contract State on Transfer

When NFTs or positions transfer between users:

1. **Associated state follows?**: When an NFT transfers, does ALL associated state (stake amounts, reward debt, risk, cooldowns, attributes) transfer with it? If staking state stays with old owner → new owner has clean slate.
2. **Underflow on associated state**: If old owner had stakeAtRisk and NFT transfers, does new owner's win try to reduce old owner's stakeAtRisk? → underflow revert.
3. **Counter/points persistence**: Do accumulated points/counters for the old token holder persist? Can they sell the NFT but keep accrued benefits?

#### Module T: Cross-Interaction Batch Analysis

For protocols with batch/multicall/router patterns:

1. **Intra-batch balance deltas**: In multicall systems, can a user reference token balances from earlier interactions that haven't been finalized? If the batch wraps tokens in step 1 but spends them in step 2, can step 2 reference the wrapped balance before step 1's transfer settles?
2. **Ocean-style delta accounting**: If the system tracks deltas rather than absolute balances, verify net settlement is correct. Can a user generate negative deltas in one interaction and positive in another, netting to zero cost but extracting real tokens?
3. **Shared state mutation order**: If batch operations A and B both read/write the same storage slot, does the order matter? Can reordering interactions within a batch create a different (exploitable) outcome?
4. **Balance snapshot timing**: When are balances snapshotted for each operation in the batch? Before the batch starts (stale for later ops) or inline (affected by earlier ops)?

#### Module U: → See `domains/defi/modules/external-protocol-integration.md` and `domains/defi/modules/oracle-analysis.md`, and the pack's modules of the same names, if present

#### Module V: → See `domains/defi/modules/economic-design.md`

#### Module W: Missing Functionality Detection

For identifying what SHOULD exist but doesn't:

1. **Missing unsetters**: For every admin setter (addChain, setOracle, addAsset, addOperator), does a corresponding REMOVER exist? If not → permanent misconfiguration.
2. **Missing pause/emergency**: For high-value operations (withdraw, liquidate, bridge), is there an emergency pause? Can the protocol respond to an active exploit?
3. **Missing migration path**: If the protocol upgrades (new oracle, new pool, new token), can existing positions migrate? Or are they permanently locked to the old integration?
4. **Incomplete restriction coverage**: If address X is restricted/blocklisted, check ALL exit paths: transfer, burn, withdraw, bridge, delegate. If ANY path is unrestricted → the restriction is useless.
5. **Missing return value handling**: External calls that return data — is the return value checked? Especially for ERC20 approve/transfer which may return false instead of reverting.

#### Module X: → See `eip-standard-compliance.md` (the pack's module of that name, if the pack ships one)

### Step 5b: Cross-Function Analysis

After individual function interrogation:

1. **Guard Consistency**: Group functions by shared state writes. If function A has `onlyOwner` but function B writes to the same mapping without it → finding.
2. **Inverse Operation Parity**: Compare deposit↔withdraw, mint↔burn, stake↔unstake. Verify they're symmetric. If deposit validates X, withdraw must validate the inverse.
3. **State Transition Integrity**: Can states be skipped, triggered out-of-order, or triggered by wrong actors?
4. **Value Flow Conservation**: Does value in == value out? Can value be created or destroyed unexpectedly?
5. **Look for what's NOT there**: For each state-changing function, ask: "What SHOULD this function also do that it doesn't?"

### Step 6: Record Candidates

For EVERY suspected vulnerability, create a candidate entry. Write a JSON array to
`A/candidates/detect-<lens>.json`; each element conforms to `engine/finding.schema.json`. Write
`[]` if you found nothing.

**Severity calibration** (apply BEFORE recording):
- **HIGH**: Direct fund loss, permanent fund lock, or permanent DoS on core function (deposit/withdraw/liquidate). If ANY user can lose >$100 or funds are permanently inaccessible → HIGH.
- **MEDIUM**: Conditional fund loss (requires specific timing/state), temporary DoS, broken invariant without direct fund loss, governance manipulation.
- Do NOT downgrade to MEDIUM just because the exploit requires multiple steps or specific ordering. Multi-step exploits that lead to fund loss are still HIGH.
- **Severity under-rating was the #1 calibration error in shadow audits.** When in doubt between H and M, rate HIGH — the Critic will downgrade if warranted.

Field mapping (Krait candidate field → schema field):

| Krait field | Schema field |
|---|---|
| `[CANDIDATE-XXX]` id | `id`: `D<lens>-<n>` (e.g. `DB-3`), numbered from 1 within your lens |
| Title | `title` |
| Severity (CRITICAL / HIGH / MEDIUM / LOW) | `severity` (`Critical` / `High` / `Medium` / `Low`) |
| File / Lines | `locations[]` (`file` relative to ROOT, `line_start`, `line_end`, `unit`, `function`) |
| Category | `category` |
| Discovery Method | `discovery` (`phase: "detect"`, `lens`, `mindset` per `engine/mindsets.md`, `consensus: null`); name the question or heuristic that exposed it (e.g. `Q2.6`, `MODIFIER-01`) in the first line of `description` as `Discovery: ...` |
| Description | `description` |
| Scenario | `exploit_trace` (one string per step) |
| Vulnerable Code | `vulnerable_code` (the actual lines, pasted; use the pack's `code_fence` when rendering) |
| Why This Is a Bug | `root_cause` |
| Step Execution | `audit_trail.step_execution` |
| Rules Applied | `audit_trail.rules_applied` |
| Depth Evidence | `audit_trail.depth_evidence` |
| Missing Precondition / Precondition Type | `preconditions[]` (`text`, `type`) + `audit_trail.missing_precondition` |
| Postconditions Created / Postcondition Types | `postconditions[]` (`text`, `type`) + `audit_trail.postconditions_created` |
| Who Benefits | `audit_trail.who_benefits` |
| Status: UNVERIFIED — needs Critic validation | `status: "candidate"` |

Set `chain` to the chain name. `harm` is optional at this stage (the Critic writes it in Step 0.5),
but fill it when you can already state WHO loses WHAT.

Example element:

```json
{
  "id": "DB-1",
  "chain": "<chain>",
  "title": "withdraw() decrements totalShares after the external transfer",
  "severity": "High",
  "category": "reentrancy",
  "status": "candidate",
  "locations": [{"file": "src/Vault.<ext>", "line_start": 142, "line_end": 150, "unit": "Vault", "function": "withdraw"}],
  "discovery": {"phase": "detect", "lens": "B", "mindset": "accountant", "consensus": null, "unit": null},
  "description": "Discovery: Q2.6 (CEI mandatory check). withdraw() reduces the caller's shares, transfers the assets, and only then reduces totalShares, so during the transfer callback totalShares is larger than the sum of shares.",
  "root_cause": "The coupled update to totalShares happens after the external call, so the exchange rate read in the callback window uses an inflated denominator.",
  "vulnerable_code": "shares[user] -= amount;\nasset.transfer(user, assets);\ntotalShares -= amount;",
  "harm": {"who": "remaining depositors", "loses_what": "part of their pro-rata assets", "magnitude": "up to the attacker's withdrawn amount per re-entry"},
  "exploit_trace": [
    "1. Attacker deposits 100 tokens through a contract that implements the transfer callback (shares = 100, totalShares = 1000, totalAssets = 1000).",
    "2. Attacker calls withdraw(100); line 146 transfers 100 tokens and triggers the callback while totalShares is still 1000.",
    "3. In the callback the attacker calls deposit(100) at the stale rate (900 assets / 1000 shares) and receives 111 shares.",
    "4. Result: after withdraw completes totalShares = 1011 against 1000 assets; the attacker's 111 shares redeem for about 109.8 tokens, 9.8 of which came from other depositors."
  ],
  "preconditions": [{"text": "the asset transfer hands control to the recipient", "type": "EXTERNAL"}],
  "postconditions": [{"text": "totalShares understates outstanding shares until the next full sync", "type": "STATE"}],
  "audit_trail": {
    "step_execution": "Lens: A=✗(N/A: no access check involved) B=✓ C=✓ D=?",
    "rules_applied": ["R8:✗(single-step)", "R10:✓(assessed at full-drain state)", "R11:✗(no external tokens)", "R12:✓(enumerated 2 paths to the stale-rate window)", "R15:✗(no flash-loan-accessible state)", "R16:✗(no oracle dependency)"],
    "depth_evidence": ["[BOUNDARY:amount=0 → no-op at L142]", "[TRACE:withdraw(100)→callback→deposit(100)→111 shares]"],
    "missing_precondition": "",
    "postconditions_created": ["totalShares understates outstanding shares until the next full sync"],
    "who_benefits": "Attacker"
  }
}
```

#### Methodology audit trail (the new fields)

These last six fields are the **methodology audit trail**. They are OPTIONAL but strongly encouraged — they show your work to downstream agents and feed future chain analysis.

- **Step Execution** (`audit_trail.step_execution`): which Pass-2 lenses you ran on THIS candidate (A=access/auth, B=value-flow, C=external/composability, D=design/spec). Format: ✓=ran, ✗=skipped with reason, ?=ran but uncertain.
- **Rules Applied** (`audit_trail.rules_applied`): cross-cutting rules independent of the kill gates. Pick from R8/R10/R11/R12/R15/R16:
  - **R8** — Cached parameter / stored external state — multi-step ops only
  - **R10** — Worst-state severity — assess impact at the worst realistic state, not the current snapshot (always required)
  - **R11** — Unsolicited token transfer — when external tokens are involved
  - **R12** — Exhaustive enabler enumeration — when the finding identifies a dangerous precondition state
  - **R15** — Flash-loan precondition manipulation — when balance/oracle/threshold preconditions are flash-loan-accessible
  - **R16** — Oracle integrity — when oracle-dependent logic is involved

  Mark `✗(reason)` for rules that don't apply. Don't fake `✓` — the Critic will check.
- **Depth Evidence** (`audit_trail.depth_evidence`): concrete-value tags. These prove you reasoned with real numbers instead of abstractly:
  - `[BOUNDARY:X=val]` — you substituted a boundary value into the expression
  - `[VARIATION:A→B]` — you traced behavior change when a parameter varies
  - `[TRACE:path→outcome]` — you traced execution to a terminal state (revert, return, state change)
- **Missing Precondition / Precondition Type** (`preconditions[]` + `audit_trail.missing_precondition`): if the attack is currently blocked, name the blocker. Lets future chain analysis look for an enabler. Types: STATE / ACCESS / TIMING / EXTERNAL / BALANCE. Optional.
- **Postconditions Created / Postcondition Types / Who Benefits** (`postconditions[]` + `audit_trail.postconditions_created`, `audit_trail.who_benefits`): if the attack succeeds, what conditions does it leave behind that another attack could chain off? Optional but valuable.

Save ALL candidates to `A/candidates/detect-<lens>.json`.

### Rules

- **MAXIMIZE RECALL, but not garbage.** Report anything suspicious that has a CONCRETE attack path. The Critic will filter further.
- **Every candidate MUST have file:line** (a `locations[]` entry with `file` and `line_start`). No generic warnings.
- **Read the actual code.** Never assume what a function does from its name.
- **Check inheritance.** A "missing" check may exist in a parent contract.
- **Track standard-library usage** (the pack's heuristics.md, section "Detector modules", names the libraries). Don't flag standard implementations as custom bugs.
- **Be concrete.** "This could be a problem" is worthless. "An attacker can call X with Y=0 to extract Z" is a finding.
- **Do NOT verify yet.** That's the Critic's job. Just find candidates.
- **PRE-FILTER:** Apply the Detection pre-filter in `engine/kill-gates.md` — do NOT generate candidates for those categories.

---

## Consensus merge

Run by the orchestrator after all four lens subagents have returned. Input:
`A/candidates/detect-A.json`, `A/candidates/detect-B.json`, `A/candidates/detect-C.json`,
`A/candidates/detect-D.json` (a missing lens file counts as `[]`; the pipeline's failure rules
decide whether that lens is re-run). Output: `A/candidates/detect.json`, a JSON array whose
elements conform to `engine/finding.schema.json`.

**After all 4 lenses complete — Consensus Merge:**
1. Merge all candidates from all 4 lens files.
2. Deduplicate: same file + same function + same root cause → keep the most detailed version. Two candidates are the same when they share a `file`, their line ranges (`line_start`–`line_end`) overlap, and they name the same root cause. Keep the richest `description` (and its `exploit_trace`, `root_cause`, `audit_trail`); list the ids of the others in `merged_from`.
3. **Cross-lens amplification**: If Lens A found a missing guard AND Lens B found a value extraction on the same function → the combined finding is stronger than either alone. Combine into a single high-confidence candidate.
4. **Consensus scoring** — count how many independent lenses reported the same root cause at overlapping lines, and set `discovery.consensus`:
   - **STRONG consensus (3+ sources)**: Almost certainly real. Tag as `consensus: strong`. Fast-track through critic.
   - **MODERATE consensus (2 sources)**: Confidence boost. Tag as `consensus: moderate`. Normal critic scrutiny.
   - **NO consensus (1 source)**: Tag as `consensus: single`. Critic applies extra scrutiny — why did the other passes miss it?
   - The consensus tag travels with the finding into state analysis and critic phases.
5. **Multi-mindset convergence bonus**: If the SAME finding was discovered by different mindset questions across lenses (e.g., Lens A's [Attacker] question and Lens B's [Accountant] question both found the same drain path), this is the strongest possible signal — independent reasoning paths converged on the same bug. Say so in the kept `description`.

The merged finding keeps the id, `discovery.lens` and `discovery.mindset` of the version whose
description was kept. Then run the Pass 3 sweep below and append its candidates.

---

## Pass 3 sweep

Run by the orchestrator right after the consensus merge. Its candidates are appended to
`A/candidates/detect.json` with ids `DP3-<n>` and `discovery: {"phase": "detect", "lens": "P3", "mindset": null, "consensus": "single", "unit": null}`,
in the same format as Step 6. Skip a candidate that duplicates one already in `A/candidates/detect.json`
(same file, overlapping lines, same root cause).

**Pass 3 — Mechanical "What's Missing" Sweep (Tier 1 + Tier 2 files):**
Separate pass focused exclusively on MISSING code. Do NOT combine with Pass 1/2:
1. **Missing inverse operations**: For every `set*`/`add*`/`grant*`/`lock*`/`delegate*`, search for corresponding `remove*`/`revoke*`/`unset*`/`unlock*`/`undelegate*`. If missing → candidate.
2. **Missing access control**: List every public/external function writing storage. Does each have an access modifier? If a state-writer has NO access control and isn't explicitly permissionless → candidate.
3. **Missing reward checkpoint**: For every function modifying stake/balance/lock/delegation, does it call reward update/checkpoint BEFORE the change? If not → candidate.
4. **Missing restriction coverage**: If protocol has pause/blocklist/freeze, list ALL value-exit functions. Does EVERY exit path enforce it? If one doesn't → candidate.
5. **Missing validation on paired operations**: For every deposit/lock/stake, find the corresponding withdraw/unlock/unstake. Compare parameter validation — if one validates but the other doesn't → candidate.
6. **Parameter transition safety**: For every admin setter (`setFee`, `setCooldown`, `setRate`, `setReserveRatio`, `setDuration`), ask: "What happens to IN-FLIGHT operations when this parameter changes?" If a user started an action (cooldown, auction, loan, vote) under old parameters, does the new value retroactively break them? If yes → candidate.
7. **DoS on core functions**: For every core lifecycle function (settle, liquidate, withdraw, claim, repay, unstake), check: (a) Does it loop over a user-controlled array? If unbounded → candidate. (b) Does it make an external call to a user-controlled address that can revert? If yes and no try/catch → candidate. (c) Can a permissionless function be called with dust (0, 1 wei) to grief state (reset timers, inflate arrays, block others)? If yes → candidate.

`A/facts.json` helps make the sweep mechanical: `entry_points[]` with `storage_writes[]` for check 2,
`auth_sites[]` and `entry_points[].guards` for checks 2 and 4, `external_calls[]` for check 7(b).
