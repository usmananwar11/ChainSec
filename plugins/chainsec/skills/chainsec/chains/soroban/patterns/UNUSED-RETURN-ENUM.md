# UNUSED-RETURN-ENUM

> **Detector class**: Scout `unused-return-enum`
> **Inject into**: Lens C
> **Category**: Error handling
> **Tier**: security
> **Related heuristics** (heuristics.md): XC-04
> **Module**: [modules/cross-contract-calls.md](../modules/cross-contract-calls.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/13-unused-return-enum.md and vulnerabilities/13-unused-return-enum.md; see ATTRIBUTION.md -->

## Description

A function typed `Result<T, E>` that never returns one of its variants on the live path (for example it computes `Ok` data, drops it, and always returns `Err`) usually hides a logic bug: callers branch on a result that does not reflect what happened.

## Vulnerable pattern

```rust
match 100u128.checked_mul(diff / sum) {
    Some(result) => result,   // value discarded
    None => panic!("Overflow"),
};
Err(Error::Overflow)
```

## Secure pattern

```rust
match 100u128.checked_mul(diff / sum) {
    Some(result) => Ok(result),
    None => Err(Error::Overflow),
}
```

## Detection

- Functions returning `Result` whose body ends in a bare `Err(...)` or `Ok(...)` ignoring earlier computed values.
- Ignored `Result` from calls (`let _ =`, bare statement) feeding a security decision.

## False-positive caveats (Gate C / FP-10 evidence)

- A function that always returns `Ok(())` after side effects is fine.
- Helper-built variants can trigger the Scout warning without a bug; trace to the caller.
- Security only when the wrong variant lets a caller proceed on a failed action.

## Minimum tests (PoC and regression targets)

- Call with inputs that should succeed and fail and assert both branches return the right variant.
- Show the caller acting on the wrong result.
