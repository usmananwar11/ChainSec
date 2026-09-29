# Lenses and mindsets

## Core Philosophy

**"If you cannot explain WHY a line of code exists, you do not understand it — and where understanding breaks down, bugs hide."**

Do NOT pattern-match. REASON about the code. Ask WHY each decision was made, WHAT breaks if it changes, and WHO benefits from an exploit.

## The four lenses

Analyze through **4 independent focused lenses**. Each lens looks at the SAME code but with a DIFFERENT mental model. This catches bugs that a single-pass analysis misses because it's impossible to hold all attack models simultaneously.

Each lens asks four mindset questions. The mindset tags map to the schema enum
`discovery.mindset` (`engine/finding.schema.json`): `[Attacker]` → `attacker`,
`[Accountant]` → `accountant`, `[Spec Auditor]` → `spec-auditor`, `[Edge Case]` → `edge-case`.
The lens letter goes in `discovery.lens`.

**Module-to-lens mapping**: Check the "Activated Modules" table in recon.md. Each activated module injects into specific lenses. Read the full module file and apply its methodology during the corresponding lens:

| Module File | Injects Into |
|---|---|
| `access-control-state.md` | Lens A |
| `governance-voting.md` | Lens A |
| `eip7702-delegation.md` | Lens A + Lens D |
| `account-abstraction-erc4337.md` | Lens A + Lens D |
| `economic-design.md` | Lens B |
| `erc4626-vault-deep.md` | Lens B + Lens D |
| `lending-liquidation-deep.md` | Lens B + Lens C |
| `amm-mev-deep.md` | Lens B + Lens C |
| `flash-loan-interaction.md` | Lens B + Lens C |
| `multi-tx-attack.md` | Lens B + Lens C |
| `oracle-analysis.md` | Lens B + Lens C |
| `token-flow-tracing.md` | Lens B + Lens C |
| `external-protocol-integration.md` | Lens C |
| `cross-chain-bridge.md` | Lens C |
| `eip-standard-compliance.md` | Lens D |

A module's `**Inject into**` header line is authoritative. A domain module and its pack half
share a file name; a module that the active pack does not ship is skipped, and a module missing
from this table (for example `vault-share-accounting.md`) follows its own header.

If a module is activated and maps to a lens, that lens MUST execute the module's full methodology (structured tables, step-by-step checks — not just skim).

### Lens A: Access Control, State Integrity & Governance
**From Pass 1 Brief**: Check which files had NO access-control candidates. Prioritize those.
**Activated modules (if in recon.md)**: `access-control-state.md`, `governance-voting.md`, `eip7702-delegation.md`, `account-abstraction-erc4337.md` — read full file methodology
**Inline modules (always)**: L (Derived Class/Override Completeness), W (Missing Functionality)
**Mandatory heuristics**: MODIFIER-01, AC-01 to AC-04, GOV-01, GOV-02, MISSING-01, MISSING-02, ZERO-WEIGHT-01

**Multi-Mindset Analysis** — For each function, ask ALL FOUR questions:
1. **[Attacker]** How would I exploit these permissions to drain funds or escalate privilege?
2. **[Accountant]** Do the access checks match the value at risk? Is a low-privilege function guarding high-value state?
3. **[Spec Auditor]** Do the modifiers/roles match what docs, comments, and NatSpec promise?
4. **[Edge Case]** What happens if caller is the contract itself, address(0), the owner, or a self-delegating governance token?

Focus EXCLUSIVELY on:
- WHO can call each function? Is that the right set of callers?
- Can functions execute in an order that breaks invariants?
- Are state transitions valid? Can states be skipped/reversed?
- Missing access modifiers — compare sibling functions (MODIFIER-01)
- Permissionless functions that should be restricted
- Cross-function state consistency (if A guards state X, do all writers of X have guards?)
- **Governance invariants (GOV-01)**: When tokens are burned/auctioned/locked, is voting power removed from quorum denominators? Inaccessible voting power → quorum unreachable.
- **Delegation integrity (GOV-02)**: Can a delegatee prevent redelegation? Checkpoint gas exhaustion?
- **Zero-supply edge (GOV-01 variant)**: What happens when totalSupply=0? Quorum=0 → anything passes.

### Lens B: Value Flow & Economic Logic
**From Pass 1 Brief**: Check which value-handling functions had NO candidates. Trace those first.
**Activated modules (if in recon.md)**: `economic-design.md`, `erc4626-vault-deep.md`, `lending-liquidation-deep.md`, `amm-mev-deep.md`, `flash-loan-interaction.md`, `multi-tx-attack.md`, `oracle-analysis.md`, `token-flow-tracing.md` — read full file methodology
**Inline modules (always)**: D (Fee Consistency), I (Weight/Proportionality), O (Payment/Distribution)
**Mandatory heuristics**: ECON-01, ECON-02, FDC-01, FDC-02, PR-01 to PR-03, FL-01, SI-01, TVL-01

**Multi-Mindset Analysis** — For each value-handling function, ask ALL FOUR questions:
1. **[Attacker]** How would I extract more value than I put in? Flash loan paths? Fee manipulation?
2. **[Accountant]** Trace every wei: entry amount → fees → shares → exit amount. Do debits equal credits?
3. **[Spec Auditor]** Do fee percentages, distribution ratios, and reward rates match what docs/comments specify?
4. **[Edge Case]** What happens with amount=0, amount=1 wei, amount=MAX, or first/last depositor? Plus the pack's heuristics.md "Lens B additions".

Focus EXCLUSIVELY on:
- Where does value enter and exit? Trace every ETH/token transfer
- Fee calculations: consistent basis? consistent destination? zero-fee edge case?
- Rounding direction: who benefits? Can attacker force rounding to zero via flash loan?
- First depositor / share inflation attacks
- Liquidation profitability boundaries
- Circular collateral / reflexive valuation
- Payment-on-failure: are refunds correct?
- **Payment destination correctness (Module O)**: Is the recipient semantically correct (contract owner vs. asset holder)? Double payout? Conditional payment with unconditional cost? Plus the pack's heuristics.md "Lens B additions".

### Lens C: External Interactions & Cross-Contract
**From Pass 1 Brief**: Check which external calls were NOT investigated. Prioritize uncovered cross-contract interactions.
**Activated modules (if in recon.md)**: `external-protocol-integration.md`, `cross-chain-bridge.md`, `lending-liquidation-deep.md`, `amm-mev-deep.md`, `token-flow-tracing.md`, `flash-loan-interaction.md` — read full file methodology
**Inline modules (always)**: A (Untrusted Recipient), C (Transfer Order/Implicit Flash Loans), S (Cross-Contract State on Transfer)
**Mandatory heuristics**: AEC-01 to AEC-03, ROR-01, RE-01, EXT-01 to EXT-03, CALLBACK-01, HOOK-01, BRIDGE-01 to BRIDGE-04

**Multi-Mindset Analysis** — For each external call, ask ALL FOUR questions:
1. **[Attacker]** Can I deploy a malicious contract at the target address? What callbacks can I trigger?
2. **[Accountant]** Does value sent out match value expected back? Are return values checked and used correctly?
3. **[Spec Auditor]** Does the integration match the external protocol's documented interface and assumptions?
4. **[Edge Case]** What if the external contract reverts, returns empty data, self-destructs, or is upgraded?

Focus EXCLUSIVELY on:
- **MANDATORY Cross-Contract Read**: For each external call in Tier 1 files, ACTUALLY open and read the target. **FIRST**: Check the call graph (`external_calls`) in `A/facts.json` for exact targets. Then read each target and check: state modifications, callbacks, permissionless functions, ignored return values.
- CEI violations: ALL state updates BEFORE external calls?
- Reentrancy via callbacks. Plus the pack's heuristics.md "Lens C additions".
- External protocol integration: permissionless claims, shutdown, silent failures
- Version compatibility of integrated protocols, libraries and the language. Plus the pack's heuristics.md "Lens C additions".
- **This lens addresses the #1 structural reason for missed findings** — 14% of misses from analyzing contracts in isolation.

### Lens D: Edge Cases, Math & Standards
**From Pass 1 Brief**: Check which math-heavy functions and standard implementations had NO candidates. Those are likely under-analyzed.
**Activated modules (if in recon.md)**: `eip-standard-compliance.md`, `erc4626-vault-deep.md`, `eip7702-delegation.md`, `account-abstraction-erc4337.md` — read full file methodology
**Extended heuristics**: For Tier 1 deep analysis, also reference the pack's heuristics.md "Extended heuristics" — 58 advanced vectors covering assembly, storage, accounting, time-dependent, array/mapping, emergency, token, and cross-contract patterns.
**Inline modules (always)**: B (Type Cast Safety), F (Token Compatibility), G (Factory/Deployment), M (State Variable Lifecycle)
**Mandatory heuristics**: SIG-01, SIG-02, TOK-01 to TOK-03, ETH-01, ETH-02, PRX-01, PRX-02, INJ-01, PACKED-01, PERMIT-01, HASH-01, ID-01, LIB-01, CHAIN-01

**Multi-Mindset Analysis** — For each math-heavy or standards function, ask ALL FOUR questions:
1. **[Attacker]** Can I craft inputs that cause overflow, underflow, or division by zero to extract value?
2. **[Accountant]** Trace 3 concrete value sets through the arithmetic — does the output match what's expected?
3. **[Spec Auditor]** Does this standard implementation match its spec exactly? Plus the pack's heuristics.md "Lens D additions".
4. **[Edge Case]** What happens at param=0, param=1, param=MAX, empty array, sender==receiver, tokenA==tokenB?

Focus EXCLUSIVELY on:
- Parameter boundary testing: param=0, param=1, param=MAX, input=0
- Type cast safety: every narrowing cast — can source exceed target max? Plus the pack's heuristics.md "Lens D additions".
- Plus the pack's heuristics.md "Lens D additions".
- Epoch/period boundary behavior
- Division by zero paths
- Assembly correctness (if any): bounds, slot arithmetic, bit operations
- Standard compliance: actual vs spec. Plus the pack's heuristics.md "Lens D additions".
- **JSON/metadata injection (INJ-01)**: Does tokenURI or any string concatenation include user-controlled data without escaping?
- **State variable lifecycle (Module M)**: Trace every user-state variable through mint/burn/re-mint cycles. Admin functions update ALL related variables?
- **Mechanical arithmetic verification**: For the TOP 3 most complex arithmetic functions (by operator count), do NOT just read and judge. TRACE with concrete values: pick 3 sets of inputs (normal case, zero/boundary case, adversarial case) and manually compute each step. Compare your result with what the code produces. If they diverge → candidate. This catches bugs like `debtCeiling()` where 5 findings hid in one function that "looked correct."
- **Self-transfer / self-referential edge case**: For every transfer/swap function, check: what happens when sender==receiver, tokenA==tokenB, from==to? Memory-cached state may not reflect storage updates within the same call.

## Cross-cutting perspective

*(Source: PlamenTSV/plamen, MIT)*: For every finding, also ask the INVERSE: "What adjacent bug does this analysis OBSCURE?" and "What is the OPPOSITE interpretation of this code?" If a finding was refuted in one lens, re-examine in the next: "What enabler makes this exploitable after all?"
