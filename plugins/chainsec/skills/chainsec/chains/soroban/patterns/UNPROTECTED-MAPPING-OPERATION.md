# UNPROTECTED-MAPPING-OPERATION

> **Detector class**: Scout `unprotected-mapping-operation`
> **Inject into**: Lens A
> **Category**: Access control
> **Tier**: security
> **Related heuristics** (heuristics.md): STOR-02, AUTH-01
> **Module**: [modules/soroban-auth.md](../modules/soroban-auth.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/16-unprotected-mapping-operation.md, vulnerabilities/16 and test-cases; see ATTRIBUTION.md -->

## Description

A function that writes or removes a map entry under a caller-chosen `Address` key, without `require_auth` on that address, lets anyone set or delete other users' entries (balances, roles, votes) and bloat the map.

## Vulnerable pattern

```rust
state.balances.set(address, balance);
env.storage().persistent().set(&STATE, &state);
```

## Secure pattern

```rust
address.require_auth();
state.balances.set(address, balance);
env.storage().persistent().set(&STATE, &state);
```

## Detection

- Entry points with `Map::set`/`remove` or `storage().*.set(&DataKey::X(arg))` keyed by an `Address` argument and empty `guards`.

## False-positive caveats (Gate C / FP-10 evidence)

- The `require_auth` is on the same address used as the key (check it is that address, not another).
- Per-caller keys derived from an authenticated address cannot touch others' entries.
- Entries that only the key's owner can ever read back, with bounded size, may be benign spam.

## Minimum tests (PoC and regression targets)

- Call as address A to set or remove B's entry with only A's auth mocked; it must fail.
- Show the harm: unauthorized balance or role change.
