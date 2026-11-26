# INCORRECT-EXPONENTIATION

> **Detector class**: Scout `incorrect-exponentiation`
> **Inject into**: Lens B
> **Category**: Arithmetic
> **Tier**: security
> **Related heuristics** (heuristics.md): ARITH-04
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/21-incorrect-exponentiation.md and vulnerabilities/21-incorrect-exponentiation.md; see ATTRIBUTION.md -->

## Description

In Rust `^` is bitwise XOR, not power. `255_u128 ^ 2` is 253, not 65025. Compounded values for fees, decimals scaling (`10 ^ 18`) or supply are silently wrong.

## Vulnerable pattern

```rust
&((255_u128 ^ 2) - 1)
```

## Secure pattern

```rust
&(255_u128.pow(2) - 1)   // or checked_pow
```

## Detection

- Grep `\^` between integer operands, especially `10 ^ n` and `2 ^ n`.

## False-positive caveats (Gate C / FP-10 evidence)

- Intentional XOR on bit flags or hashing is fine; check the surrounding intent.
- `pow` can overflow; prefer `checked_pow`.

## Minimum tests (PoC and regression targets)

- Evaluate the expression in a test and compare with `pow`; show the downstream value difference.
