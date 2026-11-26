# RESOURCE-EXHAUSTION

> **Source class**: stellar-dev-skill security.md class 10
> **Inject into**: Lens D
> **Category**: DoS
> **Tier**: security
> **Related heuristics** (heuristics.md): RES-01, RES-02, RES-03
> **Module**: [modules/resource-limits.md](../modules/resource-limits.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 10; modified by ChainSec; see ATTRIBUTION.md -->

## Description

A function whose worst-case cost on attacker-shaped input exceeds network limits is a denial of service for legitimate users. Per-transaction CPU, memory and ledger read/write limits are set by network configuration. Hunt for loops bounded by user-controlled collections or entry counts, per-iteration storage reads or events, and unbounded signature counts in `__check_auth`. The same shape is fee griefing: an attacker who can grow an entry or footprint raises rent and fees for everyone who touches it. Cap iteration counts explicitly and keep footprints small.

## Vulnerable pattern

```rust
// Risky: cost grows with attacker-controlled data
pub fn distribute(env: Env) {
    let holders: Vec<Address> = env.storage().persistent().get(&DataKey::Holders).unwrap();
    for h in holders.iter() {
        pay(&env, &h);
    }
}
```

## Secure pattern

```rust
// GOOD: bounded work per call, resumable
pub fn distribute(env: Env, start: u32, max: u32) {
    if max > MAX_BATCH {
        panic_with_error!(&env, Error::BatchTooLarge);
    }
    // process at most `max` holders starting at `start`
}
```

## Detection

- Loops over a `Vec`/`Map` read from storage that anyone can append to (`storage_writes` on the collection from a permissionless entry point).
- Loop bounds taken from arguments with no cap; per-iteration storage reads/writes or `external_calls`.
- `__check_auth` iterating over a caller-supplied signature or context list.
- One entry holding all users' data so each call loads it (see also DOS-UNBOUNDED-OPERATION and DOS-UNEXPECTED-REVERT-WITH-VECTOR).

## False-positive caveats (Gate C / FP-10 evidence)

- The collection can only be grown by an authorized admin, or has a hard cap enforced on insert.
- The loop is bounded by a small constant.
- A failure costs only the caller who supplied the oversized input (self-DoS).
- Judge against the network's current resource limits; do not state a specific number without checking the target network's config.

## Minimum tests (PoC and regression targets)

- Grow the collection to the maximum an attacker can reach and measure the invocation cost (the budget/cost tooling in the test environment); assert the shared function still fits the limits.
- Regression: after capping, assert oversized batches are rejected and remaining work stays callable.
