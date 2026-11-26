# AVOID-CORE-MEM-FORGET

> **Detector class**: Scout `avoid-core-mem-forget`
> **Inject into**: Lens D
> **Category**: Resource management
> **Tier**: quality
> **Related heuristics** (heuristics.md): none
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/7-avoid-core-mem-forget.md and vulnerabilities/7-avoid-core-mem-forget.md; see ATTRIBUTION.md -->

## Description

`core::mem::forget` consumes a value without running its destructor. It only matters for a type whose `Drop` does real work (a guard or custom wrapper meant to release or settle something); skipping it then leaves leaks or half-applied logic. SDK host values are plain handles, so forgetting those is harmless.

## Vulnerable pattern

```rust
core::mem::forget(n);
```

## Secure pattern

```rust
let _ = n;   // or let the value drop
```

## Detection

- Grep `mem::forget` / `core::mem::forget`.

## False-positive caveats (Gate C / FP-10 evidence)

- Forgetting a plain `Copy` or inert value changes nothing.
- Soroban host values (`Vec`, `Map`, `Address`) are handles whose Drop does nothing that matters; forgetting them is a code smell, not an exploit.
- Default tier is QA/Low.

## Minimum tests (PoC and regression targets)

- Show a type with a meaningful `Drop` whose side effect is skipped and the resulting state difference.
- Without a concrete effect, report as QA only.
