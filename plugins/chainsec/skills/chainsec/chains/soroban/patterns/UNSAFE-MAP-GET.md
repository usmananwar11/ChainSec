# UNSAFE-MAP-GET

> **Detector class**: Scout `unsafe-map-get`
> **Inject into**: Lens D
> **Category**: Error handling
> **Tier**: security
> **Related heuristics** (heuristics.md): PANIC-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/19-unsafe-map-get.md and vulnerabilities/19-unsafe-map-get.md; see ATTRIBUTION.md -->

## Description

`Map::get`, `get_unchecked` and `try_get_unchecked` convert host values to the declared types and panic on a type mismatch or (for `get_unchecked`) a missing key. A map built from untrusted `Val`s can hold entries of the wrong type, so a lookup can abort the call. `try_get` returns a `Result` instead.

## Vulnerable pattern

```rust
let map: Map<i32, i32> = val.try_into_val(&env).unwrap();
map.get(1)
```

## Secure pattern

```rust
map.try_get(key).map_err(Error::from)
```

## Detection

- `.get(`, `.get_unchecked(` on a `Map` whose contents originate outside the contract (arguments, other contracts).

## False-positive caveats (Gate C / FP-10 evidence)

- A `Map<K, V>` fully typed and written only by this contract cannot hold wrong-typed values; `get` returning `Option` is safe.
- `get_unchecked` after a `contains_key` check is fine for presence, not for type.
- Security when an attacker controls the element and the lookup sits on another user's path.

## Minimum tests (PoC and regression targets)

- Build a map with a mixed-type entry and call the lookup; assert the panic and that `try_get` returns `Err`.
