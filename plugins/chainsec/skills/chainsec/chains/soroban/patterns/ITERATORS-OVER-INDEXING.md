# ITERATORS-OVER-INDEXING

> **Detector class**: Scout `iterators-over-indexing`
> **Inject into**: Lens D
> **Category**: Gas usage
> **Tier**: quality
> **Related heuristics** (heuristics.md): RES-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/14-iterators-over-indexing.md and vulnerabilities/14-iterators-over-indexing.md; see ATTRIBUTION.md -->

## Description

Looping `for i in 0..N` and calling `vec.get(i)` costs a host call per element and panics or errors when the index is out of range. Iterating the `Vec` directly is cheaper and cannot go out of bounds.

## Vulnerable pattern

```rust
for i in 0..4 {
    ret = ret.checked_add(vec.get(i).ok_or(Error::NoData)?)...;
}
```

## Secure pattern

```rust
for i in vec {
    ret = ret.checked_add(i)...;
}
```

## Detection

- A numeric range loop whose body indexes a `Vec` with the loop variable; a hard-coded bound that may exceed `len()`.

## False-positive caveats (Gate C / FP-10 evidence)

- Ranges to `len()` do not warn in Scout and are mostly a cost nit.
- Indexing is needed when you must touch two positions at once or write back by index.
- Default tier is QA/Low; promote only when a short collection causes an attacker-reachable revert.

## Minimum tests (PoC and regression targets)

- Run with a vector shorter than the bound and assert the failure.
- Measure CPU budget difference only if a limit is actually at risk.
