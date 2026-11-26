# REINITIALIZATION

> **Source class**: stellar-dev-skill security.md class 3
> **Inject into**: Lens A
> **Category**: Initialization
> **Tier**: security
> **Related heuristics** (heuristics.md): INIT-01
> **Module**: [modules/upgrades-and-init.md](../modules/upgrades-and-init.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 3; modified by ChainSec; see ATTRIBUTION.md -->

## Description

A guarded `initialize` function that does not refuse a second call lets anyone call it first (or again) and capture admin. Even a correctly guarded `initialize` leaves a window between deploy and init in which a front-runner can initialize the contract. A `__constructor` (soroban-sdk 22 and later) runs once, atomically, at deploy time and cannot be re-run, so it removes both problems. A contract deployed without one cannot gain one later.

## Vulnerable pattern

```rust
pub fn initialize(env: Env, admin: Address) {
    env.storage().instance().set(&DataKey::Admin, &admin);
}
```

## Secure pattern

```rust
// GOOD: refuses second call (prefer __constructor where the SDK supports it)
pub fn initialize(env: Env, admin: Address) {
    if env.storage().instance().has(&DataKey::Admin) {
        panic_with_error!(&env, Error::AlreadyInitialized);
    }
    env.storage().instance().set(&DataKey::Admin, &admin);
}

pub fn __constructor(env: Env, admin: Address, initial_value: u32) {
    env.storage().instance().set(&DataKey::Admin, &admin);
    env.storage().instance().set(&DataKey::Value, &initial_value);
}
```

## Detection

- `entry_points` named `initialize`/`init`/`setup` (visibility `external`, `mutating`) that write an admin or owner key (`storage_writes` target such as `instance:Admin`) with no `has`/flag check before the write and no `require_auth` on a pre-known authority.
- Absence of an entry point with visibility `constructor` combined with such an init function; check `sdk` for the version.
- An init that sets the admin from an argument and is reachable after the contract is live.

## False-positive caveats (Gate C / FP-10 evidence)

- The contract uses `__constructor`; there is then no callable `initialize`.
- The init authorizes a deployer-known address (for example one baked into the wasm or checked against `current_contract_address` deployer) so a front-runner cannot satisfy it.
- The "flag" check exists but guards a different key from the one written.
- Front-running of a correctly guarded `initialize` is a deployment-process issue; report it only when the deploy flow in scope does not initialize atomically.

## Minimum tests (PoC and regression targets)

- Call `initialize` twice with different admins: the second call must fail and the first admin must stay.
- Call `initialize` from an unrelated address on a freshly deployed instance and assert whether it succeeds; if it does, show the captured privileges.
- Regression for `__constructor`: assert the deployed contract has the expected admin with no further call.
