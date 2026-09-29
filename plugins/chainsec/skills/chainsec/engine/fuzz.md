# Invariant fuzzing

How to extract invariants from smart contracts and generate fuzz tests to verify them. Used by
`chainsec-fuzz`. The test framework, run command and test patterns come from the chain pack:
`pack.json` `fuzz.framework`, `fuzz.run` and `fuzz.guide` (the guide lives at
`chains/<chain>/<fuzz.guide>`).

## Outputs

| File | Content |
|---|---|
| `.audit/<chain>/fuzz/invariants.md` | Every extracted invariant: ID (INV-001, …), description, category, priority, formal expression, state variables involved, functions that could violate it |
| `.audit/<chain>/fuzz/tests/` | Generated fuzz tests, written per the pack's fuzz guide |
| `.audit/<chain>/fuzz/report.md` | HOLDS / VIOLATED / INCONCLUSIVE counts; violated invariants (the findings) with counterexample and impact; holding invariants by category; inconclusive ones with reasons |

## Core Principle

The LLM does NOT audit for vulnerabilities. It:
1. **Understands** the code deeply
2. **Documents** all invariants (properties that must always hold)
3. **Generates** tests in the pack's fuzzing framework (`pack.json` `fuzz.framework`) to verify those invariants
4. **Iterates** on test failures to distinguish test bugs from real violations

---

## Invariant Categories

| Category | Description | Example |
|----------|-------------|---------|
| **accounting** | Balance/supply consistency | `totalSupply == sum(balances[i])` |
| **access-control** | Permission boundaries | `onlyOwner can call pause()` |
| **state-transition** | Valid state machine flows | `state can only go ACTIVE → PAUSED → ACTIVE` |
| **economic** | Price/rate/value bounds | `exchangeRate >= 1e18` (never decreases) |
| **token-conservation** | No token creation/destruction | `tokensBefore + deposited == tokensAfter` |
| **ordering** | Temporal constraints | `withdrawTime > depositTime` |
| **bounds** | Value range constraints | `fee <= MAX_FEE` |
| **relationship** | Multi-variable relationships | `debt <= collateral * ltv / 1e18` |

---

## Invariant Extraction Methodology

### Step 1: State Variable Analysis

For each contract:
1. List ALL storage variables
2. Group related variables (e.g., `totalSupply` and `balances` mapping)
3. Identify computed relationships: does variable A depend on variable B?
4. Check constructor/initializer: what invariants are established at deployment?

### Step 2: Require/Assert Mining

Every `require()` and `assert()` is a developer-stated invariant. (Examples in the pack's
language: see the pack's fuzz guide, pack.json fuzz.guide.)

Also check modifiers — `onlyOwner`, `whenNotPaused`, `nonReentrant` all encode invariants.

### Step 3: Function-Level Invariants

For each state-changing function:
1. What are the preconditions? (checks at the top)
2. What are the postconditions? (state after execution)
3. What changes and what must stay the same?
4. Are there implicit invariants? (e.g., mapping doesn't have negative values)

### Step 4: Cross-Contract Invariants

When multiple contracts interact:
1. Do balances sum correctly across contracts?
2. If Contract A calls Contract B, does B's postcondition guarantee A's invariant?
3. Are there re-entrancy concerns that break invariants during callbacks?
4. Do oracle/price feed assumptions hold across the protocol?

### Step 5: Economic Invariants

For DeFi protocols:
1. Exchange rates: can they be manipulated? Do they only go in one direction?
2. Fee collection: are fees always collected? Never double-counted?
3. Liquidity: does the pool always have enough tokens to cover withdrawals?
4. Slippage: are bounds respected?

---

## Priority Guidelines

- **high**: Core protocol invariant. If broken, funds at risk or protocol fundamentally broken.
- **medium**: Important correctness property. Violation causes incorrect behavior but not immediate fund loss.
- **low**: Defensive check. Violation is unlikely or has minimal impact.

Extract 5-20 invariants per non-trivial contract. Err on the side of more.

---

## Test generation and the fix loop

Write and run the tests per the pack's fuzz guide (pack.json fuzz.guide): its test patterns,
its iterative fix loop, and its `fuzz.run` command.
