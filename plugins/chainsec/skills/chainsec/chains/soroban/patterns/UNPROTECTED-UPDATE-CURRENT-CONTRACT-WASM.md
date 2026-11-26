# UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM

> **Detector class**: Scout `unprotected-update-current-contract-wasm`
> **Inject into**: Lens A
> **Category**: Upgrades
> **Tier**: security
> **Related heuristics** (heuristics.md): UPG-01, AUTH-01
> **Module**: [modules/upgrades-and-init.md](../modules/upgrades-and-init.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/6-unprotected-update-current-contract-wasm.md, vulnerabilities/6 and test-cases; see ATTRIBUTION.md -->

## Description

`env.deployer().update_current_contract_wasm(hash)` replaces the contract's code. If the entry point that calls it does not require the admin's authorization, anyone can swap in their own wasm and take every asset the contract holds. Note the common shape where the admin is loaded from storage but `require_auth` is never called on it.

## Vulnerable pattern

```rust
pub fn upgrade(e: Env, new_wasm_hash: BytesN<32>) {
    e.deployer().update_current_contract_wasm(new_wasm_hash);
}
```

## Secure pattern

```rust
pub fn upgrade(e: Env, new_wasm_hash: BytesN<32>) {
    let admin: Address = e.storage().instance().get(&DataKey::Admin).unwrap();
    admin.require_auth();
    e.deployer().update_current_contract_wasm(new_wasm_hash);
}
```

## Detection

- `external_calls` with kind `upgrade` in `facts.json` whose entry point has empty `guards`.
- Auth taken from a caller-supplied `Address` argument instead of the stored admin.

## False-positive caveats (Gate C / FP-10 evidence)

- The guard sits in a helper (`require_admin(&e)`): facts show it as `... via <helper>`; read the helper.
- OpenZeppelin `#[only_owner]` / `#[only_role]` macros on the fn are a guard.
- A loaded-but-unused admin variable is the bug, not a guard.

## Minimum tests (PoC and regression targets)

- Call `upgrade` with no auth mocked (`env.set_auths(&[])`): it must panic with an auth error.
- With the admin's auth mocked the upgrade succeeds; with another address's auth it fails.
