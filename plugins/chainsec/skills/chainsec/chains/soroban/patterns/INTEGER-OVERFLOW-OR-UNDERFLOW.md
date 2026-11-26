# INTEGER-OVERFLOW-OR-UNDERFLOW

> **Detector class**: Scout `integer-overflow-or-underflow`
> **Inject into**: Lens B
> **Category**: Arithmetic
> **Tier**: security
> **Related heuristics** (heuristics.md): ARITH-01, ARITH-02
> <!-- Ported from CoinFabrik scout-soroban (MIT), detectors/integer-overflow-or-underflow/src/lib.rs lint text, vulnerabilities/integer-overflow-or-underflow and test-cases (no standalone detector doc); see ATTRIBUTION.md -->

## Description

Unchecked `+`, `-`, `*`, `pow` or negation on contract integers either panics (overflow-checks on) or wraps (off). A wrap on a balance, counter or price produces a wrong value the contract trusts. Scout rates the class Critical. With overflow checks on it is a revert-DoS instead of silent corruption.

## Vulnerable pattern

```rust
let new_value = current + value;
```

## Secure pattern

```rust
let new_value = current.checked_add(value).ok_or(Error::OverflowError)?;
```

## Detection

- `counters.unchecked_math` in `facts.json` for `wrapping_*`/`unchecked_*` ops and `as` narrowing casts.
- Plain operators on values influenced by arguments; check OVERFLOW-CHECK for the profile setting.

## False-positive caveats (Gate C / FP-10 evidence)

- Operands bounded by construction (loop counters, constants, small `u32` deltas on `u128`) cannot overflow.
- With `overflow-checks = true` the issue is a panic, not silent wrap; severity depends on who can trigger it.
- `saturating_*` is a deliberate choice; still check it does not hide a failed deduction.

## Minimum tests (PoC and regression targets)

- Set the state to `MAX`, add 1, and assert panic/Err; for subtraction use 0 - 1.
- Fuzz amounts near type bounds on every value-changing entry point.
