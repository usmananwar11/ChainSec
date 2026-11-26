# ASSERT-VIOLATION

> **Detector class**: Scout `assert-violation`
> **Inject into**: Lens D
> **Category**: Error handling
> **Tier**: quality
> **Related heuristics** (heuristics.md): PANIC-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/15-assert-violation.md and vulnerabilities/15-assert-violation.md; see ATTRIBUTION.md -->

## Description

`assert!` panics when the condition fails, aborting the invocation with no typed error. Input validation reachable by users is better expressed as a `Result` with a `#[contracterror]`.

## Vulnerable pattern

```rust
assert!(value <= 10, "value should be less than 10");
```

## Secure pattern

```rust
if value > 10 { return Err(AVError::GreaterThan10); }
```

## Detection

- Grep `assert!`, `assert_eq!`, `assert_ne!` outside tests (and `debug_assert!`, which is stripped in release).

## False-positive caveats (Gate C / FP-10 evidence)

- `assert!` guarding an internal invariant that cannot be violated by input is acceptable.
- `debug_assert!` does not run in release builds: nothing is enforced, which can itself be the finding.
- Default tier is QA/Low.

## Minimum tests (PoC and regression targets)

- Call with a violating input and assert the panic vs the typed error after the fix.
- For `debug_assert!`, show the release build accepts the bad input.
