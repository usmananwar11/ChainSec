# UNSAFE-UNWRAP

> **Detector class**: Scout `unsafe-unwrap`
> **Inject into**: Lens D
> **Category**: Error handling
> **Tier**: quality
> **Related heuristics** (heuristics.md): PANIC-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/2-unsafe-unwrap.md and vulnerabilities/2-unsafe-unwrap.md; see ATTRIBUTION.md -->

## Description

`.unwrap()` aborts the invocation when the value is `None` or `Err`. In a contract that means the whole call reverts with an opaque error. It is a finding only when an attacker can force the `None`/`Err` branch on another user's critical path. Ordinary state drift (an archived or missing storage entry) stays QA unless it locks funds or rights.

## Vulnerable pattern

```rust
let admin: Address = e.storage().instance().get(&DataKey::Admin).unwrap();
```

## Secure pattern

```rust
let admin: Address = e.storage().instance().get(&DataKey::Admin).ok_or(Error::NotInitialized)?;
```

## Detection

- Grep `.unwrap()` in non-test code; `get(...).unwrap()` on storage is the common shape.
- Rank by whether the `None`/`Err` branch is attacker-forceable on another user's path (state drift alone is QA unless it locks funds or rights).

## False-positive caveats (Gate C / FP-10 evidence)

- Unwrap after a proven check (`has(&key)`, a just-written value, a constant parse) cannot fail.
- Inside `#[cfg(test)]` or `testutils` code it is irrelevant.
- Default tier is QA/Low; raise it only with a concrete attacker-forced revert on another user's critical path (liquidation, withdrawal, settlement).

## Minimum tests (PoC and regression targets)

- Drive the call with the missing or expired entry and assert the panic; then show who can cause that state and what it blocks.
- Regression: after the fix the call returns the typed `Error`.
