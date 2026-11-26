# UNRESTRICTED-TRANSFER-FROM

> **Detector class**: Scout `unrestricted-transfer-from`
> **Inject into**: Lens A + B
> **Category**: Token handling
> **Tier**: security
> **Related heuristics** (heuristics.md): TOK-04, AUTH-01
> **Module**: [modules/token-integration.md](../modules/token-integration.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/18-unrestricted-transfer-from.md, vulnerabilities/18 and test-cases; see ATTRIBUTION.md -->

## Description

A `transfer_from(spender, from, to, amount)` where `from` is a caller-supplied address spends whatever allowance `from` gave the contract. Bob calls the contract naming Alice and moves her approved tokens to himself or into a position he controls.

## Vulnerable pattern

```rust
pub fn deposit(env: Env, from: Address) {
    token_client.transfer_from(&me, &from, &me, &state.amount);
}
```

## Secure pattern

```rust
pub fn deposit(env: Env) {
    state.buyer.require_auth();
    token_client.transfer_from(&me, &state.buyer, &me, &state.amount);
}
```

## Detection

- `value_transfers` of `transfer_from` where `from` is an entry-point argument not covered by `require_auth` on that same address.

## False-positive caveats (Gate C / FP-10 evidence)

- `from.require_auth()` is called in the entry point (and the spender is the contract): the owner consented to this call.
- Plain `transfer(from, to, amt)` already requires `from`'s auth at the token, so it is a different case.
- Check the allowance requirement: if no allowance exists the call reverts, which limits impact.

## Minimum tests (PoC and regression targets)

- Alice approves the contract; Bob calls with `from = Alice` and only Bob's auth: it must fail.
- Show Alice's balance decreasing in the vulnerable version.
