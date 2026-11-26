# SOROBAN-VERSION

> **Detector class**: Scout `soroban-version`
> **Inject into**: Lens D
> **Category**: Dependencies
> **Tier**: quality
> **Related heuristics** (heuristics.md): none
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/12-soroban-version.md and vulnerabilities/12-soroban-version.md; see ATTRIBUTION.md -->

## Description

A pinned old `soroban-sdk` version can carry known bugs and miss host-function and protocol fixes. The finding is about the manifest, not a code path.

## Vulnerable pattern

```toml
soroban-sdk = { version = "=20.0.0" }
```

## Secure pattern

```toml
soroban-sdk = { version = "<current release>" }
```

## Detection

- `facts.json` `sdk` field and `Cargo.toml` / `Cargo.lock` versions of `soroban-sdk`.

## False-positive caveats (Gate C / FP-10 evidence)

- Check the version against the current SDK release and its security advisories before reporting; a newer-but-not-latest version is not a finding.
- A deployed contract's behaviour is fixed by the network protocol version at deploy time, not by a later SDK bump.
- Report only with a named advisory or fixed bug the contract is exposed to; otherwise QA/Low.

## Minimum tests (PoC and regression targets)

- Identify the specific fixed issue in the SDK changelog and show the contract uses the affected API.
