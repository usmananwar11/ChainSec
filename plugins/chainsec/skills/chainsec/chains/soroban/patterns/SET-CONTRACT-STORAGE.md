# SET-CONTRACT-STORAGE

> **Detector class**: Scout `set-contract-storage`
> **Inject into**: Lens A
> **Category**: Access control
> **Tier**: security
> **Related heuristics** (heuristics.md): STOR-02, AUTH-01
> **Module**: [modules/storage-and-ttl.md](../modules/storage-and-ttl.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/8-set-contract-storage.md, vulnerabilities/8 and test-cases; see ATTRIBUTION.md -->

## Description

A function that touches `env.storage()` with no authorization lets any caller write contract state, and worse when the key or value comes from arguments. Scout flags storage use without a preceding `require_auth`.

## Vulnerable pattern

```rust
fn set_contract_storage(env: Env) {
    let _storage = env.storage().instance();
}
```

## Secure pattern

```rust
fn set_contract_storage(env: Env, user: Address) {
    user.require_auth();
    let _storage = env.storage().instance();
}
```

## Detection

- `storage_writes` in `facts.json` inside an entry point whose `guards` is empty.
- Key built from an argument (`DataKey::Item(arg)`) with no tie to the authorizing address.

## False-positive caveats (Gate C / FP-10 evidence)

- Read-only getters and internal helpers are not exposed; only `pub` contract-impl fns matter.
- Storage written for the caller's own address under that caller's `require_auth` is fine.
- The Scout detector only checks the call, so many hits are false positives; confirm the write mutates shared or privileged state.

## Minimum tests (PoC and regression targets)

- Call the entry point with `env.set_auths(&[])` and assert it panics.
- Show the state another user or the admin relies on changed by an unauthorized caller.
