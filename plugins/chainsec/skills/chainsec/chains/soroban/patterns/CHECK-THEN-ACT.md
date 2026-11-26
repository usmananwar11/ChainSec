# CHECK-THEN-ACT

> **Source class**: stellar-dev-skill security.md class 7
> **Inject into**: Lens D
> **Category**: State consistency
> **Tier**: security
> **Related heuristics** (heuristics.md): CHK-01
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 7; modified by ChainSec; see ATTRIBUTION.md -->

## Description

State can change between transactions: a check made in one transaction does not hold in the next. Perform checks and the state changes that depend on them atomically in one invocation, and take slippage bounds (`min_out`, `max_in`, a deadline) from the caller instead of assuming the current price stays. The token-allowance variant: SEP-41 `approve(from, spender, amount, expiration_ledger)` overwrites, so lowering a non-zero allowance can be front-run (the spender uses the old value, then the new one). The expiration ledger limits the window but does not remove the race. Approve to 0 first, or use exact-amount authorization instead of standing allowances. Transaction ordering is attacker-influenced: judge by who can place a transaction between two others and what that does to the victim's value.

## Vulnerable pattern

```rust
// Risky: output depends on state the caller cannot bound
pub fn swap(env: Env, user: Address, amount_in: i128) {
    user.require_auth();
    let amount_out = calculate_output(amount_in);
    // ... transfer amount_out regardless of how the price moved
}
```

## Secure pattern

```rust
pub fn swap(env: Env, user: Address, amount_in: i128, min_out: i128) {
    user.require_auth();
    let amount_out = calculate_output(amount_in);
    if amount_out < min_out {
        panic_with_error!(&env, Error::SlippageExceeded);
    }
    // update all state in this same invocation
}
```

## Detection

- Price- or rate-dependent entry points (`swap`, `deposit`, `withdraw`, `redeem`, `borrow`) with no caller-supplied minimum/maximum or deadline argument.
- Two-step flows (propose then execute, request then claim) where the second step trusts the first step's snapshot without revalidating it.
- Approval flows (`approve`) that overwrite a non-zero allowance.

## False-positive caveats (Gate C / FP-10 evidence)

- The state cannot be moved by an adversary between the check and the act (the contract is the only price source and updates are authorized).
- The bound is enforced elsewhere: a router or UI-side guard does not count unless it is on-chain in the same invocation.
- Intended asynchronous flows with explicit expiry and revalidation at the second step.

## Minimum tests (PoC and regression targets)

- Move the price or balance between the check and the act in a test (a swap in between) and assert the victim's call reverts or respects `min_out`.
- Regression: call with a tight `min_out` and assert `SlippageExceeded` after the state has moved.
