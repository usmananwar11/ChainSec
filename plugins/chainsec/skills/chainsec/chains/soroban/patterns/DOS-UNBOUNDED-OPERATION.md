# DOS-UNBOUNDED-OPERATION

> **Detector class**: Scout `dos-unbounded-operation`
> **Inject into**: Lens D
> **Category**: DoS
> **Tier**: security
> **Related heuristics** (heuristics.md): RES-01, STOR-04
> **Module**: [modules/resource-limits.md](../modules/resource-limits.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/11-dos-unbounded-operation.md, vulnerabilities/11 and test-cases; see ATTRIBUTION.md -->

## Description

A `for` or `while` loop whose bound is a caller argument or a growing collection can exceed the per-transaction CPU, memory or ledger-entry limits, so the call can never succeed. If other users depend on that call (settlement, payout), the contract is stuck.

## Vulnerable pattern

```rust
pub fn unrestricted_loop(for_loop_count: u64) -> u64 {
    for i in 0..for_loop_count { count += i; }
}
```

## Secure pattern

```rust
const FIXED_COUNT: u64 = 1000;
for i in 0..FIXED_COUNT { sum += i; }   // or paginate: start..start+limit with a cap
```

## Detection

- Loops in entry points bounded by an argument, `len()` of a stored `Vec`/`Map`, or a counter.
- Storage reads or cross-contract calls inside the loop body make the cost per iteration higher.

## False-positive caveats (Gate C / FP-10 evidence)

- The bound is clamped (`min(n, MAX)`) or only an admin can grow the collection and the size is small.
- A caller-chosen bound that only hurts the caller (their own call fails) is not a DoS.
- Scout notes false positives where the variable is set via controlled flows; verify the real maximum.

## Minimum tests (PoC and regression targets)

- Grow the collection or pass a large bound in a test with `env.cost_estimate().budget()` and show the budget is exceeded.
- Show a critical flow for another user that then fails.
