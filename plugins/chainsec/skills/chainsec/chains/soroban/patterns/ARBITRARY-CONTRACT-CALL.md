# ARBITRARY-CONTRACT-CALL

> **Source class**: stellar-dev-skill security.md class 4
> **Inject into**: Lens C
> **Category**: Cross-contract calls
> **Tier**: security
> **Related heuristics** (heuristics.md): XC-01, TOK-03
> **Module**: [modules/cross-contract-calls.md](../modules/cross-contract-calls.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 4; modified by ChainSec; see ATTRIBUTION.md -->

## Description

Calling whichever address a user passes lets an attacker substitute a contract that mimics the expected interface. A user-supplied contract address is arbitrary code: it can fail, trap, burn the budget, return false data, emit misleading events, or call other contracts. It cannot re-enter your contract, but it can make your flow fail or mislead it. Treat any token, oracle or callback address that originates in arguments as untrusted unless it is checked against an allowlist or stored configuration.

## Vulnerable pattern

```rust
pub fn swap(env: Env, token: Address, amount: i128) {
    let client = TokenClient::new(&env, &token);
    let user: Address = env.storage().instance().get(&DataKey::Treasury).unwrap();
    client.transfer(&env.current_contract_address(), &user, &amount);
}
```

## Secure pattern

```rust
// GOOD: allowlist external contracts
pub fn swap(env: Env, token: Address, amount: i128) {
    let allowed: Vec<Address> = env.storage().instance().get(&DataKey::AllowedTokens).unwrap();
    if !allowed.contains(&token) {
        panic_with_error!(&env, Error::TokenNotAllowed);
    }
    let client = TokenClient::new(&env, &token);
    // ...
}
```

## Detection

- Use `facts.json` `external_calls` of kind `client`, `invoke_contract` or `try_invoke_contract` to find the calls, then read each call site to see whether the callee address comes from a function parameter rather than from storage.
- Permissionless registration of a token or oracle address that later flows into calls (factories, pool creation, listing).
- No comparison of the argument against a stored or allowlisted address on the path to the call.

## False-positive caveats (Gate C / FP-10 evidence)

- The contract is a generic router or aggregator whose design is to call any token; then the finding is about what trust it places in the result (see UNTRUSTED-RETURN-VALUE) and what it does with its own balances.
- The address is validated against storage or an allowlist in a helper.
- The call target cannot affect value: the contract holds no assets and the result is not used.
- Accepting a permissionless token is fine only if every consumer copes with non-standard behaviour (fee-on-transfer, failing calls, odd decimals).

## Minimum tests (PoC and regression targets)

- Deploy a malicious contract that implements the expected interface and returns inflated or false data (or traps); pass its address and assert the contract's funds or state are not harmed.
- Assert a non-allowlisted address is rejected after the fix.
