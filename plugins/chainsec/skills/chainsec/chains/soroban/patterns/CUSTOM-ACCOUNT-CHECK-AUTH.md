# CUSTOM-ACCOUNT-CHECK-AUTH

> **Source class**: stellar-dev-skill security.md class 11
> **Inject into**: Lens A
> **Category**: Account abstraction
> **Tier**: security
> **Related heuristics** (heuristics.md): ACCT-01, ACCT-02
> **Module**: [modules/soroban-auth.md](../modules/soroban-auth.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 11; modified by ChainSec; see ATTRIBUTION.md -->

## Description

A contract implementing `CustomAccountInterface` is an account (smart wallet, multisig, passkey wallet); the host calls `__check_auth` to evaluate its policy whenever that contract address must authorize something. Pitfalls:

- Verify `signature_payload` itself. Verifying any other message authorizes arbitrary calls.
- Enforce policies from `auth_contexts` (spend limits, function allowlists). Ignoring it makes "policy" wallets decorative.
- Do not `require_auth` the account's own address inside `__check_auth`: it is evaluating auth, not consuming it.
- CAP-71 delegation (protocol 27 and later): `get_delegated_signers()` returns unsanitized input; verify each address is actually a registered delegate before calling `delegate_auth`.
- Keep it lean: its cost is added to every transaction the account signs, and unbounded signature counts exhaust the budget.

## Vulnerable pattern

```rust
fn __check_auth(
    env: Env,
    signature_payload: Hash<32>,
    signature: BytesN<64>,
    auth_contexts: Vec<Context>,
) -> Result<(), AccError> {
    // BAD: verifies a constant instead of signature_payload, ignores auth_contexts
    env.crypto().ed25519_verify(&pk, &Bytes::from_array(&env, &[0u8; 32]), &signature);
    Ok(())
}
```

## Secure pattern

```rust
fn __check_auth(
    env: Env,
    signature_payload: Hash<32>,
    signature: BytesN<64>,
    auth_contexts: Vec<Context>,
) -> Result<(), AccError> {
    let pk: BytesN<32> = env.storage().instance().get(&DataKey::Owner).unwrap();
    env.crypto().ed25519_verify(&pk, &signature_payload.into(), &signature);
    // enforce policy from auth_contexts: spend limits, function allowlists...
    Ok(())
}
```

## Detection

- `auth_sites` of kind `check_auth`; read the body of every `__check_auth`.
- Signature verification (`ed25519_verify`, `secp256r1_verify`, `secp256k1_recover`) over something other than `signature_payload`.
- `auth_contexts` unused, or matched with a catch-all arm that accepts unknown contexts.
- `require_auth` on `current_contract_address()` inside `__check_auth`; `get_delegated_signers()` results used without checking registration.
- Loops over signatures or contexts with no cap.

## False-positive caveats (Gate C / FP-10 evidence)

- The policy is deliberately "owner can do anything" with one verified signature over `signature_payload`; then ignoring `auth_contexts` is the design.
- The contract enforces the policy in a helper called with `auth_contexts`.
- Check the default arm for unrecognised contexts denies rather than allows.

## Minimum tests (PoC and regression targets)

- Sign something other than the payload and assert authorization fails.
- Present a context outside the policy (a different function or an amount above the limit) and assert it is rejected.
- Pass a delegate that is not registered and assert `delegate_auth` is not reached.
