# UNSAFE-EXPECT

> **Detector class**: Scout `unsafe-expect`
> **Inject into**: Lens D
> **Category**: Error handling
> **Tier**: quality
> **Related heuristics** (heuristics.md): PANIC-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/3-unsafe-expect.md and vulnerabilities/3-unsafe-expect.md; see ATTRIBUTION.md -->

## Description

`.expect(msg)` is `.unwrap()` with a message: it still aborts the invocation on `None`/`Err`. The message helps debugging but gives callers no typed error to handle.

## Vulnerable pattern

```rust
let v: i128 = e.storage().persistent().get(&key).expect("no balance");
```

## Secure pattern

```rust
let v: i128 = e.storage().persistent().get(&key).ok_or(Error::NoBalance)?;
```

## Detection

- Grep `.expect(` in non-test code.
- Same reachability ranking as UNSAFE-UNWRAP.

## False-positive caveats (Gate C / FP-10 evidence)

- Same as UNSAFE-UNWRAP: only a finding when an attacker or ordinary state drift forces the failing branch on a critical path.
- An invariant-guarding `expect` right after a check is fine.

## Minimum tests (PoC and regression targets)

- Trigger the failing branch in a test and assert the panic; show the blocked user flow.
- Regression: typed error returned after the fix.
