# Soroban vulnerability patterns

The 23 vulnerability classes of CoinFabrik's `scout-soroban` detector suite, ported with their IDs
unchanged (credit: [ATTRIBUTION.md](../ATTRIBUTION.md)). One file per class: description,
vulnerable pattern, secure pattern, detection cues, false-positive caveats and the minimum tests
that prove or disprove it.

How the engine uses them:

- **Detection**: a pattern is a lead, not a finding. A candidate still needs a concrete attack path
  (caller -> reachable entry point -> state change -> impact) and goes through `engine/kill-gates.md`.
- **Verification**: the "False-positive caveats" section lists the evidence that supports a Gate C
  or FP-10 kill; the "Minimum tests" section is the starting list for a PoC or regression test.
- **Cross-reference**: each header names the related heuristics in [heuristics.md](../heuristics.md)
  and the pack module, if any.
- **Tier**: `security` classes are reported at the severity their impact earns. `quality` classes
  are QA/Low unless an attacker can force the panic or cost onto another user's critical path.
- **Naming**: findings keep the pack's `SOROBAN-<n>` ID; a finding that matches a class cites the
  class ID (for example in its `category`) so it can be traced back. Scout's detector ID, upper-cased,
  is the pattern ID, which is how `recon/scout-summary.py` links Scout SARIF results to patterns.

| ID | Lens | Category | Tier | One-line description |
|---|---|---|---|---|
| [ASSERT-VIOLATION](ASSERT-VIOLATION.md) | D | Error handling | quality | `assert!` on user-reachable input panics instead of returning a typed error |
| [AVOID-CORE-MEM-FORGET](AVOID-CORE-MEM-FORGET.md) | D | Resource management | quality | `core::mem::forget` skips destructors and leaks or drops logic |
| [AVOID-PANIC-ERROR](AVOID-PANIC-ERROR.md) | D | Error handling | quality | `panic!` aborts the invocation and unwinds into the calling contract |
| [AVOID-UNSAFE-BLOCK](AVOID-UNSAFE-BLOCK.md) | D | Memory safety | quality | `unsafe` block in contract code bypasses Rust's safety guarantees |
| [DIVIDE-BEFORE-MULTIPLY](DIVIDE-BEFORE-MULTIPLY.md) | B | Arithmetic | security | Division before multiplication truncates fees, shares or prices |
| [DOS-UNBOUNDED-OPERATION](DOS-UNBOUNDED-OPERATION.md) | D | DoS | security | Loop bound from an argument or growing collection exceeds per-transaction limits |
| [DOS-UNEXPECTED-REVERT-WITH-VECTOR](DOS-UNEXPECTED-REVERT-WITH-VECTOR.md) | D | DoS | security | Anyone can grow a stored `Vec` until a shared function stops fitting limits |
| [INCORRECT-EXPONENTIATION](INCORRECT-EXPONENTIATION.md) | B | Arithmetic | security | `^` is XOR in Rust, not exponentiation |
| [INSUFFICIENTLY-RANDOM-VALUES](INSUFFICIENTLY-RANDOM-VALUES.md) | B | Randomness | security | Randomness derived from ledger timestamp or sequence |
| [INTEGER-OVERFLOW-OR-UNDERFLOW](INTEGER-OVERFLOW-OR-UNDERFLOW.md) | B | Arithmetic | security | Unchecked arithmetic wraps or panics on balances, counters and prices |
| [ITERATORS-OVER-INDEXING](ITERATORS-OVER-INDEXING.md) | D | Gas usage | quality | Index loop over a `Vec` costs more and can go out of bounds |
| [OVERFLOW-CHECK](OVERFLOW-CHECK.md) | B | Arithmetic | security | `overflow-checks` not enabled in `[profile.release]` |
| [SET-CONTRACT-STORAGE](SET-CONTRACT-STORAGE.md) | A | Access control | security | Storage written by an entry point with no `require_auth` |
| [SOROBAN-VERSION](SOROBAN-VERSION.md) | D | Dependencies | quality | Outdated `soroban-sdk` pinned in the manifest |
| [UNPROTECTED-MAPPING-OPERATION](UNPROTECTED-MAPPING-OPERATION.md) | A | Access control | security | Map entry set or removed under a caller-chosen `Address` key without auth |
| [UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM](UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM.md) | A | Upgrades | security | `update_current_contract_wasm` reachable without admin authorization |
| [UNRESTRICTED-TRANSFER-FROM](UNRESTRICTED-TRANSFER-FROM.md) | A + B | Token handling | security | `transfer_from` with a caller-supplied `from` spends a third party's allowance |
| [UNSAFE-EXPECT](UNSAFE-EXPECT.md) | D | Error handling | quality | `.expect()` aborts the invocation on `None`/`Err` |
| [UNSAFE-MAP-GET](UNSAFE-MAP-GET.md) | D | Error handling | security | `Map::get`/`get_unchecked` panics on missing or wrong-typed entries |
| [UNSAFE-UNWRAP](UNSAFE-UNWRAP.md) | D | Error handling | quality | `.unwrap()` aborts the invocation on `None`/`Err` |
| [UNUSED-RETURN-ENUM](UNUSED-RETURN-ENUM.md) | C | Error handling | security | `Result`-returning function never returns one of its variants on the live path |
| [VEC-COULD-BE-MAPPING](VEC-COULD-BE-MAPPING.md) | D | Gas usage | quality | Stored `Vec<(K, V)>` scanned with `find` where per-key entries fit |
| [ZERO-ADDRESS](ZERO-ADDRESS.md) | A | Initialization | security | Admin or owner `Address` stored without rejecting the zero account |

## Stellar classes

The 12 classes of the `security.md` guide in Stellar's `stellar-dev-skill` (Apache-2.0), numbered
1 to 12 in the source; 11 are new files and class 5 (integer overflow) extends Scout's
INTEGER-OVERFLOW-OR-UNDERFLOW (see [ATTRIBUTION.md](../ATTRIBUTION.md)). All are `security` tier.

| ID | Lens | Category | Tier | One-line description |
|---|---|---|---|---|
| [MISSING-AUTH](MISSING-AUTH.md) | A | Access control | security | Mutating entry point never authorizes the address whose rights it consumes, or authorizes a caller-supplied one |
| [AUTH-REPLAY-MIDDLEWARE](AUTH-REPLAY-MIDDLEWARE.md) | A + C | Access control | security | Middleware calls a token or contract with a user's address without authorizing the user, consuming a pre-signed auth tree |
| [REINITIALIZATION](REINITIALIZATION.md) | A | Initialization | security | Unguarded or front-runnable `initialize`; prefer `__constructor` |
| [ARBITRARY-CONTRACT-CALL](ARBITRARY-CONTRACT-CALL.md) | C | Cross-contract calls | security | Token or contract address from arguments is called without an allowlist |
| [STORAGE-KEY-COLLISION](STORAGE-KEY-COLLISION.md) | D | Storage | security | Untyped or user-shaped keys overwrite unrelated entries |
| [CHECK-THEN-ACT](CHECK-THEN-ACT.md) | D | State consistency | security | Check and act split across transactions, or no caller-supplied slippage bound |
| [TTL-ARCHIVAL](TTL-ARCHIVAL.md) | D | Storage | security | Critical state expires or archives, or TTL is used as a security mechanism |
| [UNTRUSTED-RETURN-VALUE](UNTRUSTED-RETURN-VALUE.md) | C | Cross-contract calls | security | Returned price, rate or balance used without range, sign or freshness checks |
| [RESOURCE-EXHAUSTION](RESOURCE-EXHAUSTION.md) | D | DoS | security | Attacker-shaped input pushes cost past network limits; fee griefing |
| [CUSTOM-ACCOUNT-CHECK-AUTH](CUSTOM-ACCOUNT-CHECK-AUTH.md) | A | Account abstraction | security | `__check_auth` skips `signature_payload`, ignores `auth_contexts` or trusts delegates |
| [MALFORMED-BYTES](MALFORMED-BYTES.md) | B | Input validation | security | Short or odd `Bytes` input traps in `slice`, `copy_into_slice` or `from_xdr` |
| [INTEGER-OVERFLOW-OR-UNDERFLOW](INTEGER-OVERFLOW-OR-UNDERFLOW.md) | B | Arithmetic | security | Stellar class 5: also validate input sign and range; `i128` amounts can be negative |
