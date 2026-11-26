# AUTH-REPLAY-MIDDLEWARE

> **Source class**: stellar-dev-skill security.md class 2
> **Inject into**: Lens A + C
> **Category**: Access control
> **Tier**: security
> **Related heuristics** (heuristics.md): AUTH-03, AUTH-04
> **Module**: [modules/soroban-auth.md](../modules/soroban-auth.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 2; modified by ChainSec; see ATTRIBUTION.md -->

## Description

The cross-contract variant of missing auth. A contract that calls `token.transfer(&user, ...)` on behalf of `user` without authorizing `user` itself relies on the inner call to demand the signature. If `user` has pre-signed an auth tree that includes that inner `token.transfer`, anyone can call the middleware entry point with `user` as an argument and have the host consume that signed entry. The signature was meant for a different top-level call.

Re-authorize at every layer that exercises an address's authority, not only at the deepest call. Review rule: for each entry point, enumerate every `Address` argument and ask whose authority each state change or downstream call consumes.

## Vulnerable pattern

```rust
// BAD: never auths `user` here
pub fn settle(env: Env, user: Address, amount: i128) {
    token_client.transfer(&user, &recipient, &amount);
}
```

## Secure pattern

```rust
// GOOD: this layer binds the user's consent to this call and arguments
pub fn settle(env: Env, user: Address, amount: i128) {
    user.require_auth();
    token_client.transfer(&user, &recipient, &amount);
}
```

## Detection

- `external_calls` of kind `client` (or `invoke_contract`) whose arguments include an `Address` parameter of the entry point, in an entry point whose `auth_sites` do not cover that parameter.
- `require_auth_for_args` that binds fewer arguments than the downstream call consumes (the signed payload no longer pins amount or recipient).
- Helper or router contracts (settlers, relayers, batchers, aggregators) that forward user addresses into token or protocol calls.

## False-positive caveats (Gate C / FP-10 evidence)

- The `Address` argument is the contract itself or a stored authority that is authorized elsewhere in the same entry point.
- The entry point is an internal-only helper not exposed in the contract interface (`visibility` not `external`).
- The downstream call spends nothing of the address (read-only, or only credits it).
- `authorize_as_current_contract` is the contract authorizing its own sub-calls, not a user's; check it lists exactly the intended sub-invocations.

## Minimum tests (PoC and regression targets)

- Build an auth tree where `user` pre-signs only the inner `token.transfer`, then call `settle(user, ...)` from a third party: the call must fail once the outer `require_auth` exists, and succeeds (the bug) before.
- Assert via `env.auths()` that the entry point records an auth requirement for `user` at the outer layer.
