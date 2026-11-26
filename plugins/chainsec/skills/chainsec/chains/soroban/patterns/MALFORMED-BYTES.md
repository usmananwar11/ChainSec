# MALFORMED-BYTES

> **Source class**: stellar-dev-skill security.md class 12
> **Inject into**: Lens B
> **Category**: Input validation
> **Tier**: security
> **Related heuristics** (heuristics.md): BYTES-01
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 12; modified by ChainSec; see ATTRIBUTION.md -->

## Description

Raw byte operations trap on bad input instead of returning a typed error. The caller gets a generic failure, never your `#[contracterror]` code: a `try_` call sees `Err(Err(InvokeError::Abort))`, or `Err(Ok(Error(Context, InvalidAction)))` when the function does not return `Result`.

- `Bytes::slice` traps with `Error(Object, IndexBounds)` when the range runs past `len()`.
- `Bytes::copy_into_slice` panics when the target buffer length differs from `len()`.
- `FromXdr::from_xdr` traps when the bytes are not valid `ScVal` XDR. It returns `Err` only when valid XDR does not convert to the target type.
- A `BytesN<N>` parameter rejects a wrong-length argument before your function body runs.

This is a revert-only issue: report it when the trapping path is on another user's critical path or breaks an integration that expects typed errors.

## Vulnerable pattern

```rust
// BAD: traps with a host error when payload is shorter than 36 bytes
pub fn submit(env: Env, payload: Bytes) {
    let key = payload.slice(0..32);
    let mut nonce = [0u8; 4];
    payload.slice(32..36).copy_into_slice(&mut nonce);
    // ...
}
```

## Secure pattern

```rust
// GOOD: check the length first, fail with a typed error
pub fn submit(env: Env, payload: Bytes) -> Result<(), Error> {
    if payload.len() != 36 {
        return Err(Error::InvalidPayload);
    }
    let key: BytesN<32> = payload
        .slice(0..32)
        .try_into()
        .map_err(|_| Error::InvalidPayload)?;
    let mut nonce = [0u8; 4];
    payload.slice(32..36).copy_into_slice(&mut nonce);
    // ...
    Ok(())
}
```

## Detection

- Entry points taking `Bytes` (or `String`) that call `slice`, `copy_into_slice` or `from_xdr` with fixed offsets and no earlier `len()` check.
- Hand-rolled parsers for messages, signatures or proofs.
- Choosing the fix: fixed length and a call-boundary rejection is acceptable, take `BytesN<N>`; fixed length with a typed error, take `Bytes` and convert with `BytesN::<N>::try_from` (`Err(ConversionError)` on mismatch); variable length, check `len()` before every slice (`Bytes::get(i)` returns `None` out of bounds); structured input, prefer a `#[contracttype]` argument to XDR bytes.

## False-positive caveats (Gate C / FP-10 evidence)

- A `len()` check dominates the slice on every path.
- The parameter is `BytesN<N>`: a wrong length is rejected before the body runs.
- The trap only affects the caller who supplied the bad input (self-revert) with no shared state involved.
- Typically QA/Low unless it blocks another user's critical path or a protocol that relies on typed error codes.

## Minimum tests (PoC and regression targets)

- Call with empty, one-byte-short, and one-byte-long payloads via `try_` and assert the observed error shape; after the fix assert `Error::InvalidPayload`.
- Fuzz payload lengths from 0 to a few bytes above the expected size.
