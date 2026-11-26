# DIVIDE-BEFORE-MULTIPLY

> **Detector class**: Scout `divide-before-multiply`
> **Inject into**: Lens B
> **Category**: Arithmetic
> **Tier**: security
> **Related heuristics** (heuristics.md): ARITH-03
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/1-divide-before-multiply.md and vulnerabilities/1-divide-before-multiply.md; see ATTRIBUTION.md -->

## Description

Integer division truncates. Dividing first and multiplying afterwards throws away the remainder, so a fee, share or price can round to zero or come out noticeably smaller than the exact value. Whoever can pick the operand sizes (tiny deposits, many small calls) extracts the rounding error.

## Vulnerable pattern

```rust
let fee = amount / 10_000 * fee_bps;   // amount = 9_999 -> 0
```

## Secure pattern

```rust
let fee = amount * fee_bps / 10_000;   // 9_999 * fee_bps / 10_000
```

## Detection

- Grep for `/ ... *` in one expression, or a `let` holding a quotient later multiplied.
- `facts.json` `counters.unchecked_math` does not cover this; read the arithmetic in value-moving entry points.

## False-positive caveats (Gate C / FP-10 evidence)

- Intentional bucketing (`x / step * step`) to round down to a grid is not a bug.
- Multiply-first can overflow `i128`; if the product can exceed range, the correct fix is a wide/fixed-point helper (`fixed_mul_floor`), not a bare reorder.
- Check which side the rounding favours: rounding in the protocol's favour is usually accepted.

## Minimum tests (PoC and regression targets)

- Fuzz amounts 1..10_000 and compare against exact arithmetic; assert the result is never 0 for non-zero input where it should not be.
- Show a profitable sequence of small calls where the truncation accrues to the caller.
