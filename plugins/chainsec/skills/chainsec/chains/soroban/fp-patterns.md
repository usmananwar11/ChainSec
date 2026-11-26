# Soroban false-positive patterns and gate overrides

## FP patterns

### FP-3: OpenZeppelin Stellar Contracts Standard Protection
The finding reports a vulnerability in code that embeds OpenZeppelin `stellar-contracts` building blocks:
- Fungible and non-fungible token traits with checked `i128` arithmetic and balance/allowance accounting
- Ownable and access-control helpers: `#[only_owner]`, `#[only_role]` and similar macros, expected to expand to `require_auth` on the stored owner or role holder
- Pausable and upgradeable helpers, and any `#[contractimpl(contracttrait)]` default methods (macro-generated, invisible to `facts.json`)

**Check**: Verify the exact `stellar-contracts` version in `Cargo.toml` / `Cargo.lock` and read the macro or default method it relies on; do not assume. Check how the contract wires it: a helper that is only internal (no auth of its own) is only as safe as the entry point that calls it; check overridden default methods and any entry point the contract adds beside the library's. Protection from a library the contract does not actually call is no protection.

### FP-7: Rust Integer Arithmetic Safety
The finding claims overflow/underflow but:
- `overflow-checks = true` is set in the `[profile.release]` that builds the wasm, so `+ - *` panic instead of wrapping
- The overflow would revert the transaction, not silently wrap
- This is a DoS (revert), not value extraction → lower severity (unless the engine's DoS exception applies: an unprivileged attacker permanently blocks a core lifecycle function)

**Check**: Is `overflow-checks` really on for the profile used for deployment (workspace root `Cargo.toml`; OVERFLOW-CHECK)? Is the arithmetic done through `wrapping_*`, `overflowing_*`, `saturating_*`, `unchecked_*` or an `as` cast? Those do not panic.

**IMPORTANT EXCEPTION**: with overflow checks off, plain operators wrap, and `as` casts and `wrapping_*` / `saturating_*` never panic regardless of the profile. Do NOT dismiss those findings with this FP pattern. Also not covered: an `i128` amount that is negative (no overflow, but a reversed flow: TOK-01) and truncating `as` casts of amounts into narrower types.

### FP-8: Read-Only / View Function Confusion
The finding claims state manipulation via a view function:
- Soroban has no `view` keyword; `facts.json` `mutability` is the extractor's guess from storage writes, external calls and token calls it can see
- The "vulnerability" only affects off-chain simulation reads

**Check**: A function that looks read-only can still write through a helper the extractor does not follow, through a storage handle passed as a parameter, or through a cross-contract call; read the body. Entry points are callable by anyone in a real transaction, not only in simulation. Only kill when the function makes none of these writes or calls (all of them resolved by reading the code, not by `view` in facts).

### FP-9: Test/Mock/Interface-Only (Soroban test files)
Soroban items of FP-9 (`engine/phases/verify.md`):
- Test files and folders: `test.rs`, `tests.rs`, `test_*.rs`, `*_test.rs`, `tests/`, `test/`, `testutils` modules
- Test-only code inside source files: `#[cfg(test)]` modules, `#[test]` functions and code behind the `testutils` feature
- Mocks (`mock/`, `mocks/`), `fuzz/`, `benches/`, `build.rs` and deployment scripts
- Interface-only items (`#[contractclient]` or `#[contracttrait]` traits with no implementation)

### FP-S1: Reentrancy claims
The finding says an external call can re-enter the contract before state is updated. The host rejects calls into a contract already on the call stack (direct or indirect, on normal cross-contract paths), so classic reentrancy is not reachable.

**Check**: Kill reentrancy claims that rely on the callee calling back. Do not kill: a claim about a failing, budget-burning or swallowed call (XC-04, RES-01), or ordering that matters when a `try_` call lets the caller continue after a failed callee (XC-03).

### FP-S2: Replay claims against `require_auth`
The finding says a signed authorization can be replayed or that a nonce is missing. Nonces and expirations on authorization entries are enforced by the host.

**Check**: Kill replay claims against plain `require_auth` / `require_auth_for_args`. Do not kill: a pre-signed auth tree consumed by a contract that never authorizes the user (AUTH-03), `require_auth_for_args` that omits a signed-off argument (AUTH-04), or a custom signature scheme over application data (`ed25519_verify` / `secp256k1_recover`) with no replay key (BYTES-02).

### FP-S3: Panic with no third-party victim
The finding says `unwrap`, `expect`, `panic!`, `assert!` or `Map::get` can abort an invocation. A panic reverts only the caller's own transaction.

**Check**: Quality tier (UNSAFE-UNWRAP, UNSAFE-EXPECT, AVOID-PANIC-ERROR, ASSERT-VIOLATION) → QA, not a finding, when only the caller is harmed. It survives only when an attacker can force the panic on another user's critical path (withdraw, liquidate, settle, a shared batch) or when attacker-shaped storage makes it permanent (PANIC-01, RES-02, UNSAFE-MAP-GET).

### FP-S4: `mock_all_auths` in tests
The finding says auth is bypassed because tests use `env.mock_all_auths()`. That only affects the test environment; it is a testing gap (AUTH-06), not a contract bug.

**Check**: Kill when the claim is only that the tests mock auth. Look at the contract code for the real `require_auth` (or its absence: MISSING-AUTH).

## Gate overrides and examples

Soroban examples for the gates in `engine/kill-gates.md`, keyed by gate letter. Several Scout classes
(`patterns/`) are quality-tier; these notes say when they survive.

### Gate A — Generic Best Practice
- Kill gate: "use `checked_add`" with `overflow-checks = true` on and no concrete path to a wrapping operator, "use `panic_with_error!` instead of `panic!`" (AVOID-PANIC-ERROR), "replace `unwrap` with a typed error" with no third-party victim (UNSAFE-UNWRAP, UNSAFE-EXPECT), "use iterators instead of indexing" (ITERATORS-OVER-INDEXING), "pin a newer `soroban-sdk`" (SOROBAN-VERSION) without a fixed issue that bites this contract, "missing event", randomness from `env.prng()` or ledger time without a concrete payout an attacker controls.
- Detection pre-filter: Do NOT report: quality-tier Scout classes as findings, generic "check `transfer`'s return value" (SEP-41 `transfer` panics on failure and returns no bool), generic centralization of a stored admin.

### Gate B — Theoretical or speculative
- Kill: a frozen or clawback-affected SAC claim that does not name the specific asset in the protocol's token list (TOK-02).
- Kill: `i128` overflow on values provably bounded far below the limit (a counter bumped once per call) — but state the bound.
- Kill: "TTL could lapse" for an entry the contract extends on every hot path, or that anyone can extend and the protocol keeps alive; survive when nothing extends it and funds would be stuck (TTL-01).

### Gate C — Design Is Intentional
- Detection pre-filter: patterns from reference implementations include OpenZeppelin `stellar-contracts`, Stellar's `soroban-examples` and the Stellar Asset Contract's classic-asset semantics (trustlines, `AUTH_REQUIRED`, issuer clawback and freeze).
- Example: issuer clawback and freeze on a SAC are asset properties, not contract bugs.
- Each pattern's "False-positive caveats" section lists the evidence that makes it intentional.

### Gate D — Speculative / No Concrete Exploit
- Kill: "a malicious token could re-enter" with no attacker-callable path (see FP-S1); "an oracle could return a bad price" without naming which oracle and what range the contract accepts (XC-02).
- Survives with numbers: a permissionless entry point lets an attacker append to a list the shared `withdraw` loops over; state the entry count at which the transaction exceeds the network limit and the cost to the attacker (RES-02).

### Gate E — Admin Trust Boundary
- Kill: ZERO-ADDRESS, a missing admin timelock, an immutable admin, or an upgrade path when the only way to abuse it is the trusted admin or deployer supplying a bad value (INIT-02, UPG-01).
- Survives under the gate's exception: `update_current_contract_wasm` reachable with no delay when users cannot exit before it takes effect — an irreversible destructive action (Medium at most unless the role is broad or reachable by non-admins).
- Never killed by this gate: the same classes when an UNPRIVILEGED caller reaches the path (MISSING-AUTH, UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM, REINITIALIZATION where `initialize` can be front-run, AUTH-REPLAY-MIDDLEWARE).

## Masking code examples

Soroban masking patterns for the state auditor Phase 7 (`engine/phases/state.md`):

- **Swallowed `try_` errors**: `match client.try_call(..) { Err(_) => { /* ignore */ } .. }`, `let _ = client.try_transfer(..)` or `.ok()`. A call expected to succeed is failing; what invariant does the continuation assume (XC-04)?
- **Silent defaults**: `.get(&key).unwrap_or(0)` or `unwrap_or_default()` on a balance, position or price turns a missing or archived entry into zero and hides why it is missing (TTL-01, TTL-02).
- **Saturating arithmetic**: `saturating_sub` / `saturating_add` clamps a divergence that a panicking operator would have exposed. Checked arithmetic prevents the wrap but doesn't fix why the values diverged.
- **Conversion with a default**: `x.try_into().unwrap_or(..)` or an `as` cast silences an out-of-range value. Why can the value exceed the target type?
