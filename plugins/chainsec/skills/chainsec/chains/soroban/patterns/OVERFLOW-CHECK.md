# OVERFLOW-CHECK

> **Detector class**: Scout `overflow-check`
> **Inject into**: Lens B
> **Category**: Arithmetic
> **Tier**: security
> **Related heuristics** (heuristics.md): ARITH-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/4-overflow-check.md and vulnerabilities/4-overflow-check.md; see ATTRIBUTION.md -->

## Description

Rust integer overflow panics only when `overflow-checks` is on. Release builds default to it off, so a contract compiled without `overflow-checks = true` in `[profile.release]` wraps silently. Soroban deploys the release wasm, so the setting decides whether every unchecked `+`, `-`, `*` is safe.

## Vulnerable pattern

```toml
[profile.release]
overflow-checks = false
```

## Secure pattern

```toml
[profile.release]
overflow-checks = true
```

## Detection

- Read `Cargo.toml` of the crate and the workspace root; the profile must be set where the wasm is built.
- Also check `[profile.release-with-logs]` and any custom profile used by the deploy script.

## False-positive caveats (Gate C / FP-10 evidence)

- Explicit `checked_*` / `saturating_*` arithmetic everywhere lowers impact but does not make the setting irrelevant for the remaining operators.
- Workspace members inherit `[profile.*]` from the root manifest only; a profile in a member manifest is ignored.
- The key may be absent and still on if a parent profile it inherits from sets it.

## Minimum tests (PoC and regression targets)

- Build with the real release profile and run an add/sub that overflows `u32::MAX`; it must panic.
- Show a reachable unchecked operation to turn the config smell into a finding.
