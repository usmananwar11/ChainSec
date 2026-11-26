# STORAGE-KEY-COLLISION

> **Source class**: stellar-dev-skill security.md class 6
> **Inject into**: Lens D
> **Category**: Storage
> **Tier**: security
> **Related heuristics** (heuristics.md): STOR-01, STOR-02
> **Module**: [modules/storage-and-ttl.md](../modules/storage-and-ttl.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 6; modified by ChainSec; see ATTRIBUTION.md -->

## Description

Untyped keys (raw `Symbol`s, tuples, strings or bytes) can silently overwrite unrelated data when two code paths build the same key, or when a user-controlled value forms part of the key. Always use a `#[contracttype]` key enum so each kind of data has its own variant. Keys that mix a user-supplied component need the variant to scope it so users cannot reach other namespaces.

## Vulnerable pattern

```rust
// BAD: the user-supplied Symbol is the whole key, so it can equal the admin key
env.storage().instance().set(&symbol_short!("admin"), &admin);
pub fn set_note(env: Env, user: Address, name: Symbol, value: Address) {
    user.require_auth();
    // a caller passing name = symbol_short!("admin") overwrites the admin entry
    env.storage().instance().set(&name, &value);
}
```

## Secure pattern

```rust
#[contracttype]
pub enum DataKey {
    Admin,
    Balance(Address),
    Allowance(Address, Address),
}
env.storage().persistent().set(&DataKey::Balance(user), &value);
```

## Detection

- `storage_writes` whose target key is a bare symbol, string, bytes or tuple rather than a `#[contracttype]` enum variant.
- The same key expression written by two code paths or modules for different meanings (same tier).
- Key components taken from arguments without a distinguishing variant (a user-chosen `Symbol` or `Bytes` used as the whole key).

## False-positive caveats (Gate C / FP-10 evidence)

- A single `#[contracttype]` enum used for all keys: distinct variants cannot collide.
- Two keys of the same shape deliberately share a value (an alias), or one is in a different tier and is a different entry.
- A bare `symbol_short!` constant used once, for one value type, in one place.
- Generic helpers that namespace keys by a stored prefix are fine if the prefix is not user-controlled.

## Minimum tests (PoC and regression targets)

- Write a value through one path and read through another with the colliding key; assert the unrelated value is untouched.
- Fuzz user-controlled key components and assert no write lands on `Admin` or another privileged key.
