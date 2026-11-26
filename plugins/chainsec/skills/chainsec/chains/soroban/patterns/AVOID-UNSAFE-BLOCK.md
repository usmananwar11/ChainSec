# AVOID-UNSAFE-BLOCK

> **Detector class**: Scout `avoid-unsafe-block`
> **Inject into**: Lens D
> **Category**: Memory safety
> **Tier**: quality
> **Related heuristics** (heuristics.md): none
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/10-avoid-unsafe-block.md and vulnerabilities/10-avoid-unsafe-block.md; see ATTRIBUTION.md -->

## Description

`unsafe` bypasses Rust's memory-safety guarantees. Contract logic has no need for raw pointers, so an `unsafe` block is a place where undefined behaviour or wrong wasm semantics can hide.

## Vulnerable pattern

```rust
unsafe {
    let result_ptr: *mut f64 = &mut i;
    let result = *result_ptr;
}
```

## Secure pattern

```rust
// plain safe code, no raw pointer:
let result = i;
```

## Detection

- Grep `unsafe {` and `unsafe fn` in contract crates, including dependencies vendored into the repo.

## False-positive caveats (Gate C / FP-10 evidence)

- Unsafe in a well-known audited dependency is out of scope.
- Needed for FFI to the host? Contract code uses the SDK, not raw FFI; treat any use as suspicious.
- Default tier is QA/Low.

## Minimum tests (PoC and regression targets)

- Show an input that makes the unsafe block misbehave (out-of-bounds, aliasing); otherwise report as QA.
- Regression: replace with safe code and compare outputs on fuzzed inputs.
