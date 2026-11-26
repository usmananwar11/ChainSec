# UNTRUSTED-RETURN-VALUE

> **Source class**: stellar-dev-skill security.md class 9
> **Inject into**: Lens C
> **Category**: Cross-contract calls
> **Tier**: security
> **Related heuristics** (heuristics.md): XC-02
> **Module**: [modules/cross-contract-calls.md](../modules/cross-contract-calls.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 9; modified by ChainSec; see ATTRIBUTION.md -->

## Description

Data returned by another contract is only as trustworthy as that contract. Allowlist oracles and tokens, sanity-check magnitudes and signs, and enforce freshness before using a returned price, rate, balance or timestamp in value-moving math.

## Vulnerable pattern

```rust
// Risky: oracle value used as is
let price: i128 = oracle_client.get_price(&asset);
let value = amount * price;
```

## Secure pattern

```rust
let price: i128 = oracle_client.get_price(&asset);
if price <= 0 || price > MAX_REASONABLE_PRICE {
    panic_with_error!(&env, Error::InvalidPrice);
}
```

## Detection

- `external_calls` whose return value (price, rate, balance, decimals, timestamp) flows into arithmetic or a transfer amount with no range, sign or staleness check.
- Oracle address from arguments or permissionless config (see ARBITRARY-CONTRACT-CALL).
- Balance read from a token before and after a `transfer`, or a raw `balance()` used as an accounting input (donation inflation).

## False-positive caveats (Gate C / FP-10 evidence)

- The callee is an allowlisted contract the protocol itself controls, and its output is bounded by construction.
- The check is performed in a helper or in the callee's typed wrapper.
- Bounds are enforced downstream before any value moves.
- A permissionless oracle choice that only affects the caller's own funds is a design choice, not a protocol finding.

## Minimum tests (PoC and regression targets)

- Mock the callee to return zero, negative, `i128::MAX` and stale values; assert the contract rejects each or cannot be drained.
- Assert the fix rejects a stale timestamp when freshness matters.
