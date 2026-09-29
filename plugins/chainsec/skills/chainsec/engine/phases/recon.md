# Recon — Architecture & Attack Surface Mapping

> Phase 4 of the ChainSec pipeline (`engine/pipeline.md`). Run before any vulnerability detection.

Reads: `A/preflight.json`, `A/facts.json`, `A/risk.json` (plus the source, docs and config under ROOT)
Writes: `A/recon.md`, `A/known-issues.md` (plus `A/analyzers/<name>.md` for each analyzer that ran)

`A` = `TARGET/.audit/<chain>/`, `P` = `chains/<chain>/` (the pack folder).

## Purpose

Build a complete mental model of the protocol BEFORE looking for bugs. This phase identifies:
1. What the protocol does and what's worth stealing
2. How contracts relate to each other (trust boundaries, fund flows)
3. Where novel/custom logic lives (vs battle-tested library code)
4. What attack surfaces exist

## Orchestration notes

1. Create `A/` and `A/candidates/` if they don't exist (`A/facts.json` and `A/risk.json` are already there from pipeline phases 2–3).
2. Read README, docs, config files. **Extract known issues to `A/known-issues.md`** (Gate H): the README's "Known Issues", "Acknowledged" or "Publicly Known Issues" sections, linked previous audit acknowledgments, and the automated/bot report section. Write "None found" if there are none.
3. Save everything to `A/recon.md` — **MUST include File Risk Table with tiers**.

**Scope rules:**
- **SKIP**: tests, scripts, mocks, interfaces-only, node_modules, lib/, build artifacts, >90% comments
- **SCOPE EXPANSION**: Base/parent contracts inherited by Tier 1 files auto-promote to minimum Tier 2 (standard libraries in the pack's `novelty_allowlist` excluded)

## Execution

### Step 1: Project Identification

Read the project root for context:
- README.md, docs/, any documentation
- Package manifests (package.json, Cargo.toml, and the pack's `detect.markers` files)
- Deployment scripts, configuration files

Determine:
- **Protocol type**: DEX/AMM, Lending, Stablecoin, Yield Vault, Governance/DAO, NFT Marketplace, Oracle, Staking, Bridge, or hybrid
- **Protocol name** and brief description
- **Key dependencies**: Chainlink, Uniswap, Aave, Compound, standard libraries, etc. (chain-specific examples: the pack's heuristics.md, section "Recon additions")
- **Compiler version** and any pragma constraints

### Step 2: Code Facts

Read `A/facts.json` (written by the pack's extractor in pipeline phase 2). If `mode` is `regex`,
note lower confidence in recon.md: "Facts mode: regex — structural facts are pattern-matched, not
compiler-verified (lower confidence)". Otherwise note "Facts mode: compiler".

Which facts fields feed which recon sections:

| `A/facts.json` field | Feeds |
|---|---|
| `units[]` (`name`, `kind`, `file`, `loc`) | Protocol Overview scope size; 3a Contract Role Map; File Risk Table LOC |
| `units[].parents` | 3e Unit graph; SCOPE EXPANSION (base/parent contracts) |
| `entry_points[]` (`visibility`, `mutability`, `guards`) | 3c Trust Boundary Map (permissionless surfaces); Detection's Function-State Matrix |
| `auth_sites[]` | 3c Trust Boundary Map (who can call what) |
| `storage_writes[]` | 3a key state variables; State analysis mutation matrix |
| `external_calls[]` | 3a external dependencies; 3c Untrusted Recipient Map; Attack Surface Priority |
| `value_transfers[]` (`asset`) | 3b Fund Flow Map; 3c Untrusted Recipient Map; `value_handling_bonus` |
| `counters{<file>}` | File Risk Table columns (LOC, Ext Calls, State Writers) via `A/risk.json` |

How the facts are used downstream:
- Use `counters` (through `A/risk.json`) for EXACT counts in the risk score (Step 3)
- Use `external_calls` during Detection Pass 2 to know exactly which contracts to read
- Use `units[].parents` to verify modifier presence before reporting "missing modifier" findings
- Use `entry_points` to pre-populate the Function-State Matrix in Detection

**CRITICAL: Facts are SUPPLEMENTS, not replacements.** You still MUST read every file. The facts tell you WHAT exists; only reading the code tells you WHY it exists and whether it's correct.

### Step 2b: Analyzer Pre-Scan (Optional)

For each `pack.json` `analyzers` entry whose `requires` tool is `OK` in `A/preflight.json` `tools`:

1. Run the tool to produce its JSON output at `A/analyzers/<name>.json`. The exact command is in the
   pack's heuristics.md, section "Recon additions".
2. Run the analyzer's `run` script with the tool's JSON output: `python3 CORE/P/<run> A/analyzers/<name>.json A/analyzers/<name>.md`
   when `run` ends in `.py` (otherwise `bash CORE/P/<run> ...` with the same arguments).

**If the analyzer runs successfully:**
- Raw JSON saved to `A/analyzers/<name>.json`
- Summary extracted to `A/analyzers/<name>.md` with: detector name, severity, file:line, and one-line description for each H/M finding
- These findings serve as ADDITIONAL SIGNAL during Detection Phase — they are NOT automatically reported
- Analyzer findings that overlap with ChainSec candidates increase confidence
- Analyzer findings that ChainSec missed should be investigated (potential recall boost)
- **IMPORTANT**: Many analyzer detectors produce informational/low noise. Only extract HIGH and MEDIUM severity analyzer findings for the summary.

**If the tool is not available or fails:**
- Skip silently. Note in recon.md: "<name> pre-scan: SKIPPED (not available)"
- This is purely optional — ChainSec works without it

### Step 3: File Inventory & Deterministic Risk Scoring

Scan all source files. **SKIP**: test files, scripts, mocks, interfaces-only files (no function bodies), node_modules, lib/, build artifacts, files >90% comments.

**SCOPE EXPANSION — Base/Parent Contracts**: If a core contract inherits from a non-library contract in the project (e.g., `base/`, `abstract/`, `common/`, `protocol-rewards/`), that base contract MUST be included in scope and scored. Any file imported and inherited by a Tier 1 file gets auto-promoted to minimum Tier 2. Standard library imports (the pack's `novelty_allowlist`) are excluded — only project-specific base contracts.

**Read `A/risk.json`** and copy each file's `score` and `tier` into the File Risk Table (`size` gives
the codebase size category; `promoted: true` marks a parent auto-promoted to STANDARD). Then judge
immaturity for each file and record adjustments:

- **immaturity_bonus**: +10 if the contract meets ANY of: (a) not present in any prior audit report linked in docs/README, (b) added/significantly modified after the last audit (check git history if available), (c) has no test coverage file (no corresponding test file in test/ directory), (d) contains TODO/FIXME/HACK comments indicating unfinished work. If prior audit reports exist, contracts NOT in the audit scope are immature by default.

Add +10 to the score of each immature file and write the reason in the Notes column
("immaturity +10: <reason>"). If the adjusted score moves a file above a file of a higher tier,
promote it to that tier and say so in Notes; never demote a tier `A/risk.json` assigned.

> **Note — the formula.** Weights come from pack.json; see `scripts/score-risk.py`. The formula
> as Krait wrote it, with ChainSec's weights taken from `risk_weights`, `loc_weight`,
> `novelty_bonus` and `value_bonus`:
>
> ```
> RISK_SCORE = (external_calls × 5) + (state_writing_functions × 4) + (payable_functions × 4)
>            + (assembly_blocks × 6) + (unchecked_blocks × 3) + (LOC × 0.05)
>            + (novel_code_bonus)      # +15 if NOT matched by the pack's novelty_allowlist
>            + (value_handling_bonus)   # +10 if handles native-asset or token transfers
>            + (immaturity_bonus)       # +10 if contract has NO prior audit coverage or is newly written
> ```
>
> The script computes every term except `immaturity_bonus`, which is your judgment above. What
> each counter counts in this chain: the pack's heuristics.md, section "Recon additions".

**RANK all files by RISK_SCORE descending and assign tiers** (`A/risk.json` already did this):
- **TIER 1 (DEEP)**: Top 5 files by score — get full 3-pass treatment in Detection
- **TIER 2 (STANDARD)**: Next 10 files — get standard Pass 1 analysis
- **TIER 3 (SCAN)**: Remaining files — quick scan only (function signatures + obvious patterns)

For SMALL codebases (≤15 files), all files are effectively Tier 1.

**This tier table is the CONTRACT between Recon and Detection. Detection MUST follow these tiers.**

### Step 3: Architecture Map

Build the following artifacts by reading the actual code:

#### 3a. Contract Role Map

For each core contract, identify:
- **Purpose**: What does this contract do in one sentence?
- **Risk level**: HIGH (handles funds, critical state), MEDIUM (access control, configuration), LOW (view-only, events)
- **Key state variables**: What persistent state does it manage?
- **External dependencies**: What does it call? What calls it?

#### 3b. Fund Flow Map

Trace how value moves through the system:
- Where do tokens/ETH enter? (deposit, mint, swap functions)
- Where do they exit? (withdraw, redeem, claim, liquidate)
- What intermediate state do they pass through?
- Who can trigger each flow?

#### 3c. Trust Boundary Map

Identify trust assumptions:
- Which addresses are trusted (owner, admin, oracle, keeper)?
- What can each trusted role do? Can they rug?
- Which functions are permissionless? What can any user trigger?
- Where does the protocol trust external data? (oracles, callbacks, user input)

#### 3d. Contract Maturity Assessment

For each core contract, assess maturity to inform the `immaturity_bonus` in RISK_SCORE:

| Contract | Prior Audit? | Test File? | TODO/FIXME? | Maturity |
|----------|-------------|------------|-------------|----------|

Check:
- **Prior audit coverage**: Does README or docs reference previous audits? Which contracts were in scope? Contracts NOT in any prior audit scope = immature.
- **Test coverage**: Is there a corresponding test file in `test/` or `tests/`? Untested contracts = immature.
- **Unfinished markers**: Search each file for `TODO`, `FIXME`, `HACK`, `XXX`, `TEMP`, `WORKAROUND` comments. Any present = immature.
- **Git recency** (if git history available): Was the contract recently added or significantly modified? `git log --oneline -5 <file>` shows recent changes.

Contracts flagged as immature get `immaturity_bonus = +10` in the RISK_SCORE formula, which may promote them to a higher tier.

#### 3e. Unit Graph

Unit graph: `facts.units[].parents`; cluster strategy per the pack's clustering file (`pack.json`
`clustering`). Map which units inherit from which, and what they import. Flag:
- Contracts that override virtual functions (modified behavior vs base)
- Multiple inheritance (diamond problem potential)
- Custom implementations of standard interfaces (ERC20, ERC721, ERC4626)

### Step 3b: Fee Path Mapping

List EVERY function that charges a fee. For each:
- What type of fee? (protocol fee, user fee, royalty, flash fee, change fee)
- How is it calculated? (basis points on gross? on net? flat amount? scaled by decimals?)
- Where is it sent? (factory, pool, recipient, burned)
- What happens when fee is 0?

This map is critical for cross-checking fee consistency in the Detection phase.

### Step 3c: Untrusted Recipient Map

List every native-asset/token transfer where the recipient is NOT the caller and NOT a hardcoded protocol address:
- Royalty recipients
- Callback receivers
- Fee recipients from external registries
- Oracle/external data sources

Chain-specific recipient sources (royalty registries, receiver callbacks): the pack's heuristics.md, section "Recon additions".

These are reentrancy and DOS surfaces.

### Step 4: Attacker Mindset Recon

Answer these four questions:

1. **What's worth stealing?** List all value stores — token balances, LP positions, collateral, reward pools, governance power, NFT ownership.

2. **What's the kill chain?** For each value store, what's the shortest path from "anyone can call this" to "value is extracted"? Identify the gates (access control, validation, timelocks) an attacker must bypass.

3. **What's novel?** What code was written specifically for this protocol (not copied from the standard libraries in the pack's `novelty_allowlist`)? Novel code = novel bugs. Flag any non-standard implementations of standard patterns.

4. **What's complex?** Which functions have: deep nesting, multiple external calls, state reads + writes + external interactions in one tx, callback patterns, assembly blocks?

### Step 5: Protocol-Specific Checklist Selection

Based on protocol type, select the relevant vulnerability checklist:

**DEX/AMM**: Price manipulation (flash loan spot price), LP accounting (first depositor), slippage/MEV (deadline, min output), fee-on-transfer tokens.

**Lending**: Oracle manipulation (stale price, flash loan inflate), liquidation logic (self-liquidate, bonus calc), interest rate rounding, bad debt scenarios.

**Stablecoin**: Peg mechanism gaming, undercollateralized minting, cascading liquidation death spirals.

**Yield Vault / ERC4626**: Share inflation (first depositor), deposit/withdraw rounding direction, donation attacks, strategy compromise.

**Governance/DAO**: Flash loan voting, snapshot manipulation, proposal replay, timelock bypass.

**NFT Marketplace**: Order replay, royalty bypass, ERC721 callback reentrancy, approval scope.

**Oracle**: Staleness checks, zero/negative price, L2 sequencer uptime, manipulation resistance.

**Staking**: Reward gaming (stake before distribution), unbonding bypass, dust precision loss.

Integration checklists for specific external protocols: the pack's heuristics.md, section "Recon additions".

**Record the protocol type(s) as `modules_by_protocol` keys** (a protocol can have several):

| Protocol type | `modules_by_protocol` key |
|---|---|
| DEX/AMM | `dex-amm` |
| Lending | `lending` |
| Yield Vault / ERC4626 | `vault` |
| Governance/DAO | `governance` |
| Staking | `staking` |
| NFT Marketplace, gaming | `nft-gamefi` |
| Bridge | `bridge` |
| Upgradeable proxy architecture | `proxy-upgradeable` |
| Smart wallet / account abstraction | `wallet-aa` |

Stablecoin and Oracle have no key of their own; their modules come from the triggers in Step 6.

### Step 6: Module Selection (Trigger Flag System)

Select modules: always `modules_by_protocol.always`; the lists for each protocol type chosen in
Step 5; plus any module whose trigger fires per `domains/defi/triggers.md` and the pack's
`module-triggers.md`. Record trigger evidence.

- `modules_by_protocol` paths are relative to the pack folder; write them core-relative in recon.md
  (`../../domains/defi/modules/<name>.md` → `domains/defi/modules/<name>.md`; `modules/<name>.md` → `chains/<chain>/modules/<name>.md`).
- Tier hierarchy and selection rules: `domains/defi/triggers.md`. Select ALL modules whose trigger
  condition is met — do not cap the count.
- The primers in the selected lists (`.../primers/*.md`) are the Detection Primer.

## Output

Save to `A/recon.md` with:

```markdown
# ChainSec Recon Report

## Protocol Overview
- Name: [name]
- Type: [type(s)] — keys: [modules_by_protocol keys]
- Dependencies: [list]
- Compiler: [version]
- Scope size: [X files, Y total LOC]
- Facts mode: [compiler / regex (lower confidence)]
- Analyzers: [<name>: ran / SKIPPED (not available)]
- Native asset price (USD, for Gate F): [price and source, or "not recorded"]

## File Risk Table (MANDATORY — Detection phase follows this)
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|------|------|-----------|------|-----|-----------|---------------|-------|
| 1 | src/Core.<ext> | 87 | DEEP | 450 | 12 | 8 | Handles all funds |
| 2 | ... | ... | ... | ... | ... | ... | ... |

Codebase size category: SMALL (≤15) / MEDIUM (16-40) / LARGE (40+)

## Fund Flows
[How value moves through the system]

## Trust Boundaries
[Who is trusted, what can they do, permissionless surfaces]

## Attack Surface Priority
1. [Highest-risk area and why]
2. [Second-highest]
3. ...

## Novel Code (not from libraries)
[Custom implementations to scrutinize]

## Detection Primer
Loaded: [core-relative primer path(s)]

## Activated Modules
| Module | Trigger Evidence |
|--------|-----------------|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/oracle-analysis.md | Found an external price-feed read in src/PriceFeed.<ext> |
| domains/defi/modules/token-flow-tracing.md | Found token transfers in src/Vault.<ext>, src/Pool.<ext> |
| ... | ... |

## Relevant Checklists
[Protocol-specific checks to apply]
```

## Rules

- **Read actual code, not just file names.** Open every core contract and understand it.
- **Do NOT start looking for bugs yet.** This phase is strictly reconnaissance.
- **Be honest about complexity.** If you don't understand a piece of code, flag it as needing deep analysis.
- **Track inheritance carefully.** Many "missing" checks exist in parent contracts. Use `A/facts.json` `units[].parents`.
- **Facts override manual counts.** `A/facts.json` `counters` and the scores in `A/risk.json` are ground truth for the RISK_SCORE formula. Do not re-count manually.
