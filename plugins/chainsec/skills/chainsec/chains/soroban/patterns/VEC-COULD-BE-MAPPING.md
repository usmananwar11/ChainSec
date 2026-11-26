# VEC-COULD-BE-MAPPING

> **Detector class**: Scout `vec-could-be-mapping`
> **Inject into**: Lens D
> **Category**: Gas usage
> **Tier**: quality
> **Related heuristics** (heuristics.md): STOR-04
> **Module**: [modules/storage-and-ttl.md](../modules/storage-and-ttl.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), detectors/vec-could-be-mapping/src/lib.rs lint text and test-cases (no standalone detector doc); see ATTRIBUTION.md -->

## Description

A stored `Vec<(K, V)>` searched with `find` or iterated to look up a key costs a full read of the entry and a linear scan, and the whole vector is rewritten on each add. A `DataKey::Item(K)` entry per key is O(1) and bounded in size.

## Vulnerable pattern

```rust
data.push_back((key, value));
env.storage().persistent().set(&DataKey::Data, &data);
```

## Secure pattern

```rust
env.storage().persistent().set(&DataKey::Data(key), &value);
```

## Detection

- `Vec<(Address, _)>` in storage with `.iter().find(...)` in a getter or setter.

## False-positive caveats (Gate C / FP-10 evidence)

- A small, admin-bounded list (a handful of signers) is fine as a Vec.
- Becomes a security finding as DOS-UNBOUNDED-OPERATION when users can grow it.
- Default tier is QA/Low.

## Minimum tests (PoC and regression targets)

- Add N entries and measure the lookup cost against the budget; show N where it fails if users can reach it.
