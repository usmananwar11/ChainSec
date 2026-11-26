# AVOID-PANIC-ERROR

> **Detector class**: Scout `avoid-panic-error`
> **Inject into**: Lens D
> **Category**: Error handling
> **Tier**: quality
> **Related heuristics** (heuristics.md): PANIC-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/9-avoid-panic-error.md and vulnerabilities/9-avoid-panic-error.md; see ATTRIBUTION.md -->

## Description

`panic!` aborts the invocation, and for a cross-contract call that failure unwinds into the caller. Returning a `#[contracterror]` enum gives callers something to match on (`try_*` client methods) and avoids reverting a whole batch.

## Vulnerable pattern

```rust
None => panic!("Overflow error"),
```

## Secure pattern

```rust
None => return Err(Error::OverflowError),
```

## Detection

- Grep `panic!(` in non-test code; also `unreachable!`, `todo!`, `unimplemented!`.

## False-positive caveats (Gate C / FP-10 evidence)

- `panic!` on a truly unreachable invariant is acceptable.
- `panic_with_error!(&e, Error::X)` is the SDK idiom and yields a typed error; it is not a finding.
- Default tier is QA/Low unless an attacker forces the branch on a critical path.

## Minimum tests (PoC and regression targets)

- Trigger the branch and assert the failure; check whether callers can recover (`try_` client).
- Regression: typed error returned.
