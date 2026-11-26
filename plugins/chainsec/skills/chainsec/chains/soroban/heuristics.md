# Soroban heuristics

Stellar Soroban (Rust, `soroban-sdk`) heuristics. The core set is written for ChainSec from the
platform rules and security review notes in Stellar's `stellar-dev-skill` (Apache-2.0) and the
vulnerability classes of CoinFabrik's `scout-soroban` (MIT). Credit: [ATTRIBUTION.md](ATTRIBUTION.md).
Load together with `domains/defi/heuristics.md`. Vulnerability classes: [patterns/README.md](patterns/README.md).
Where Soroban behaviour differs from EVM habits: [primers/soroban-vs-evm.md](primers/soroban-vs-evm.md).
<!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0); modified by ChainSec; see ATTRIBUTION.md -->

## Core heuristics (Soroban)

Where the engine names a Solidity-era mandatory heuristic, use the Soroban equivalent:

| Engine ID | Soroban equivalent |
|---|---|
| SIG-01, SIG-02, REPLAY-01, PERMIT-01 | AUTH-04 (host-managed nonces for `require_auth`), ACCT-01, ACCT-02 (`__check_auth`), BYTES-02 (`ed25519_verify` / `secp256k1_recover` over app data needs its own replay key) |
| PRX-01, PRX-02 | UPG-01 to UPG-03, INIT-01, INIT-02 |
| AEC-01 to AEC-03 | XC-01, XC-02 |
| RE-01, ROR-01, CALLBACK-01, HOOK-01 | XC-03: the host rejects re-entry only into a contract already on the call stack, so same-contract reentrancy is not reachable; review ordering around failing calls, and calls from an attacker-controlled callee (TOK-03, XC-01) into a DIFFERENT protocol contract that holds stale state |
| ETH-01, ETH-02, MRV-01 | TOK-01 to TOK-05 (no value attached to calls; XLM is a Stellar Asset Contract) |
| BRIDGE-01 to BRIDGE-04 | XC-04 plus `domains/defi/modules/cross-chain-bridge.md` (no native messaging layer) |
| PACKED-01, HASH-01 | BYTES-01, BYTES-02, STOR-01 |
| MODIFIER-01 | AUTH-05 (OpenZeppelin Stellar auth macros) |
| TS-01, C2-01, C2-02 | No transient storage; deterministic deploys: DEPLOY-01 |

Note the engine's `TOK-01` (callback reentrancy) is not the Soroban `TOK-01` below (negative `i128` amounts); in this pack the IDs below win (the engine's callback-reentrancy `TOK-01` maps to XC-03). The engine's `TOK-02` and `TOK-03` (decimals) map to pack TOK-05, and the engine's mandatory "TOK-01 to TOK-03" reads as pack TOK-01 to TOK-05 here.

**Authorization (AUTH-01 to AUTH-06):**
- **AUTH-01**: Every `mutating` entry point that moves value or rights of an `Address` argument calls `require_auth` on *that* address. For each `Address` argument ask: does the call spend, reduce or reconfigure something this address owns? Crediting a balance or reading public data needs no auth. Facts: empty `guards` on a `mutating` entry point, counter `unguarded_mutators` (MISSING-AUTH, SET-CONTRACT-STORAGE).
- **AUTH-02**: Admin and privileged paths authorize the admin loaded from storage, never an address taken from a parameter. `who.require_auth()` on a caller-supplied `who` proves only that the caller controls `who` (MISSING-AUTH, UNPROTECTED-MAPPING-OPERATION).
- **AUTH-03**: Re-authorize at every layer that spends a user's authority. A function that calls `token.transfer(&user, ..)` without `user.require_auth()` lets anyone consume a pre-signed auth tree that includes the inner call (AUTH-REPLAY-MIDDLEWARE).
- **AUTH-04**: Replay protection (nonces, expirations) for `require_auth` is handled by the host. Do not report a missing nonce on it. `require_auth_for_args` binds only the arguments listed: check they cover everything the user is meant to sign off on (recipient, amount, token, limits).
- **AUTH-05**: OpenZeppelin Stellar `#[only_owner]`, `#[only_admin]`, `#[only_role]` and `#[only_any_role]` authenticate (per OpenZeppelin's access-control docs they require auth from the stored holder; verify in the macro source for the version in use). `#[has_role]` and `#[has_any_role]` only check membership and do NOT call `require_auth`: the checked address must also be authorized explicitly (MISSING-AUTH). Then check role-admin paths (who can grant and revoke roles, ownership transfer, renounce).
- **AUTH-06**: Tests that call `env.mock_all_auths()` cannot show missing auth. Check that tests assert `env.auths()` for the sensitive entry points; absence is a testing gap, not a contract bug (FP-S4).

**Custom accounts (ACCT-01, ACCT-02):**
- **ACCT-01**: `__check_auth` verifies every signature over `signature_payload` (not over another message) and enforces policy per `auth_contexts` entry. It must not call `require_auth` on its own address (CUSTOM-ACCOUNT-CHECK-AUTH).
- **ACCT-02**: A policy that ignores `auth_contexts` it does not recognise (other contexts, other contracts, other function names) is decorative. With CAP-71 delegation, `get_delegated_signers()` returns unsanitised input: each address must be checked as a registered delegate before `delegate_auth` (verify the API against the SDK version in use).

**Initialization (INIT-01, INIT-02):**
- **INIT-01**: A guarded `initialize` can be front-run between deploy and init; `__constructor` (SDK 22 and later) runs atomically at deploy and cannot re-run. An unguarded `initialize` is REINITIALIZATION outright.
- **INIT-02**: `__constructor` or `initialize` arguments (admin, token, fee recipient, oracle) stored without validity checks (ZERO-ADDRESS). Gate E applies when only the trusted deployer supplies the bad value.

**Upgrades (UPG-01 to UPG-03):**
- **UPG-01**: `update_current_contract_wasm` (older API) and `update_current_contract(ContractExecutable::Wasm(hash))` (SDK 28 and later, per the Stellar guide) sit behind admin auth, with a delay when users are promised one (UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM). There is no proxy and no `delegatecall`: the contract's own code is replaced in place.
- **UPG-02**: New code must read old storage. `#[contracttype]` enum keys and struct fields are matched by name and shape, so renames and reshaping strand or fail to decode existing entries. Look for a stored schema version and an idempotent, admin-gated `migrate`. Error codes are public ABI and must not be renumbered.
- **UPG-03**: The upgrade takes effect after the current invocation; code in the same invocation still runs the old WASM. `__constructor` does not re-run on upgrade.

**Storage (STOR-01 to STOR-04):**
- **STOR-01**: Keys from different modules or tuple shapes that can collide, or untyped keys (`Symbol`, raw tuples) instead of one `#[contracttype]` enum (STORAGE-KEY-COLLISION).
- **STOR-02**: User-controlled keys written to storage: an attacker chooses which entry is overwritten or created (SET-CONTRACT-STORAGE, UNPROTECTED-MAPPING-OPERATION).
- **STOR-03**: Large or growing data in `instance()`: instance storage is one ledger entry loaded on every call, with a network-capped entry size (64 KB on mainnet at the time of the source notes; check live network settings). Per-user data never belongs there.
- **STOR-04**: A `Vec` or `Map` in a single entry that grows per user (VEC-COULD-BE-MAPPING, DOS-UNBOUNDED-OPERATION). Fine-grained per-user keys avoid both the size cap and the per-call read cost.

**TTL and archival (TTL-01 to TTL-03):**
- **TTL-01**: Persistent and instance entries archive when their TTL lapses; access then fails until restored. Stuck funds or a DoS when nothing extends or restores them (TTL-ARCHIVAL).
- **TTL-02**: Data that must survive (balances, positions, admin, config) in `temporary()` is deleted for good on expiry: no restore path.
- **TTL-03**: Check where `extend_ttl` runs: instance TTL on hot paths, per-user entries on each write. Anyone can extend any entry's TTL, so "an attacker keeps an entry alive" is not a finding by itself, but TTL expiry must never be the mechanism that ends a permission (store a deadline in the value and check it).

**Tokens (TOK-01 to TOK-05):**
- **TOK-01**: SEP-41 amounts are `i128` and signed. Reject `amount < 0` (and usually `<= 0`) at every entry point that takes an amount: a negative `transfer` amount reverses the flow (INTEGER-OVERFLOW-OR-UNDERFLOW, Stellar class 5).
- **TOK-02**: Stellar Asset Contract issuers can freeze (`set_authorized`) and `clawback`; accounts need trustlines. One frozen or unauthorised recipient can block a shared flow (batch payout, liquidation, withdraw queue). Name the specific asset before reporting (Gate B).
- **TOK-03**: A token address taken from arguments or user storage is untrusted: it can be any contract that mimics the interface (ARBITRARY-CONTRACT-CALL).
- **TOK-04**: `transfer_from` with a caller-supplied `from` spends a third party's allowance; the spender, not `from`, authorizes `transfer_from` (UNRESTRICTED-TRANSFER-FROM).
- **TOK-05**: SAC tokens have 7 decimals; custom tokens can differ. Read `decimals()` at registration and normalize; never assume 7 or 18.

**Arithmetic (ARITH-01 to ARITH-04):**
- **ARITH-01**: `overflow-checks = true` must be in `[profile.release]` of the workspace root (or the crate being built if it is not a workspace member); otherwise release builds wrap silently (OVERFLOW-CHECK). Check the profile the deploy script actually uses.
- **ARITH-02**: `+ - * /` on amounts, `as` casts between integer widths, and `checked_*` / `wrapping_*` / `saturating_*` choices. With overflow checks on, plain operators panic (a revert, FP-7); wrapping and saturating variants and `as` casts do not (INTEGER-OVERFLOW-OR-UNDERFLOW; counter `unchecked_math`).
- **ARITH-03**: Rounding direction in fixed-point math (`soroban-fixed-point-math` `fixed_mul_floor` / `fixed_mul_ceil`, if used) favours the protocol on mint, redeem, fee and debt calculations; division before multiplication truncates (DIVIDE-BEFORE-MULTIPLY).
- **ARITH-04**: `^` is XOR in Rust, not exponentiation (INCORRECT-EXPONENTIATION). Use `pow` / `checked_pow`.

**Cross-contract calls (XC-01 to XC-04):**
- **XC-01**: The called contract address comes from arguments or user-writable storage: arbitrary code that can fail, trap, burn budget or return lies (ARBITRARY-CONTRACT-CALL).
- **XC-02**: Return values from other contracts (prices, rates, balances) used without range, sign or freshness checks (UNTRUSTED-RETURN-VALUE).
- **XC-03**: Reentrancy: the host blocks re-entry only into a contract already on the call stack, so same-contract reentrancy is not reachable. It does not stop an attacker-controlled callee (arbitrary token or hook: TOK-03, XC-01) from calling a DIFFERENT protocol contract that is not on the stack and acting on stale state there (A calls the attacker's token before telling controller B to update; the attacker calls B directly). An external call is also a failure, budget and side-effect boundary: order state updates deliberately across contracts (FP-S1).
- **XC-04**: `try_invoke_contract` / `try_*` client errors swallowed, or a `Result` ignored, so the flow continues after a failed call (UNUSED-RETURN-ENUM). A plain call that fails reverts the whole transaction. Budget exhaustion is not catchable by `try_` calls.

**Resource limits (RES-01 to RES-03):**
- **RES-01**: Per-transaction CPU, memory and ledger-entry read/write limits are set by network configuration (read live values; do not hard-code). Loops over user-growable data or per-iteration storage reads, events or cross-contract calls hit them (DOS-UNBOUNDED-OPERATION, RESOURCE-EXHAUSTION).
- **RES-02**: One bad element must not revert a batch or a shared function: a loop over a list anyone can append to is a DoS (DOS-UNEXPECTED-REVERT-WITH-VECTOR).
- **RES-03**: Attacker-growable entries raise rent and fees for others, and unbounded signature counts in `__check_auth` raise the cost of every transaction the account signs (RESOURCE-EXHAUSTION).

**Panics and errors (PANIC-01):**
- **PANIC-01**: `unwrap`, `expect`, `panic!` and `assert!` revert the whole invocation. They are a finding only when an attacker can force them on another user's critical path (withdraw, liquidate, settle); otherwise quality tier (UNSAFE-UNWRAP, UNSAFE-EXPECT, AVOID-PANIC-ERROR, ASSERT-VIOLATION, UNSAFE-MAP-GET). Bare panics surface as opaque host errors that clients cannot match on; `panic_with_error!` or returned `Result` give typed errors.

**Randomness and time (RAND-01, TIME-01):**
- **RAND-01**: `env.prng()` is seeded from ledger state and is predictable; ledger fields are validator-influenced. Not for keys, auth, or payouts an attacker can time (INSUFFICIENTLY-RANDOM-VALUES). Gate A applies unless a concrete payout is attacker-controlled.
- **TIME-01**: `env.ledger().timestamp()` is ledger close time in seconds; `sequence()` counts ledgers (roughly five seconds each). Check staleness windows and deadlines for ledgers-vs-seconds mix-ups and for entry TTLs (counted in ledgers) used as time.

**Bytes and signatures (BYTES-01, BYTES-02):**
- **BYTES-01**: Fixed-offset `Bytes::slice` / `copy_into_slice` / `from_xdr` on caller-supplied bytes without a length check traps with a host error instead of a typed error. A `BytesN<N>` parameter rejects a wrong length before the body runs (MALFORMED-BYTES).
- **BYTES-02**: Custom signature schemes (`ed25519_verify`, `secp256k1_recover`) over application messages need domain separation (contract address, network, function) and their own nonce or replay key: the host's `require_auth` nonces do not apply to them.

**State consistency and deployment (CHK-01, DEPLOY-01):**
- **CHK-01**: Check-then-act split across two invocations, or a swap with no caller-supplied minimum (`min_out`): state can change between transactions (CHECK-THEN-ACT). The sandwich numbers requirement of Gate D still applies.
- **DEPLOY-01**: `deployer().with_address(addr, salt)` addresses are deterministic per (deployer, salt) and predictable: front-run deploys, and a deploy followed by a separate `initialize` (INIT-01).

## Extended heuristics

> **Usage**: Read during Tier 1 deep analysis in Pass 2. NOT a module — always available for reference.
> **Source**: the 23 Scout detector classes and the 12 Stellar security classes, IDs unchanged (credit: [ATTRIBUTION.md](ATTRIBUTION.md)).
> Each pattern file has the vulnerable and secure shapes, detection cues and false-positive caveats.

### Scout classes (23)

| Scout ID (pattern) | Heuristic family | Tier |
|---|---|---|
| ASSERT-VIOLATION | PANIC-01 | quality |
| AVOID-CORE-MEM-FORGET | Resource management (no heuristic; read the call) | quality |
| AVOID-PANIC-ERROR | PANIC-01 | quality |
| AVOID-UNSAFE-BLOCK | Memory safety (no heuristic; read the block) | quality |
| DIVIDE-BEFORE-MULTIPLY | ARITH-03 | security |
| DOS-UNBOUNDED-OPERATION | RES-01 | security |
| DOS-UNEXPECTED-REVERT-WITH-VECTOR | RES-02, STOR-04 | security |
| INCORRECT-EXPONENTIATION | ARITH-04 | security |
| INSUFFICIENTLY-RANDOM-VALUES | RAND-01 | security |
| INTEGER-OVERFLOW-OR-UNDERFLOW | ARITH-02, TOK-01 | security |
| ITERATORS-OVER-INDEXING | RES-01 (gas usage) | quality |
| OVERFLOW-CHECK | ARITH-01 | security |
| SET-CONTRACT-STORAGE | AUTH-01, STOR-02 | security |
| SOROBAN-VERSION | Dependencies (flag SDK below 22: no `__constructor`) | quality |
| UNPROTECTED-MAPPING-OPERATION | AUTH-01, STOR-02 | security |
| UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM | UPG-01 | security |
| UNRESTRICTED-TRANSFER-FROM | TOK-04 | security |
| UNSAFE-EXPECT | PANIC-01 | quality |
| UNSAFE-MAP-GET | PANIC-01 | security |
| UNSAFE-UNWRAP | PANIC-01 | quality |
| UNUSED-RETURN-ENUM | XC-04 | security |
| VEC-COULD-BE-MAPPING | STOR-04 | quality |
| ZERO-ADDRESS | INIT-02 | security |

### Stellar classes (11 new IDs; class 5 extends INTEGER-OVERFLOW-OR-UNDERFLOW)

| Stellar class (pattern) | Heuristic family | Tier |
|---|---|---|
| 1 MISSING-AUTH | AUTH-01, AUTH-02, AUTH-06 | security |
| 2 AUTH-REPLAY-MIDDLEWARE | AUTH-03 | security |
| 3 REINITIALIZATION | INIT-01 | security |
| 4 ARBITRARY-CONTRACT-CALL | XC-01, TOK-03 | security |
| 6 STORAGE-KEY-COLLISION | STOR-01 | security |
| 7 CHECK-THEN-ACT | CHK-01 | security |
| 8 TTL-ARCHIVAL | TTL-01 to TTL-03 | security |
| 9 UNTRUSTED-RETURN-VALUE | XC-02 | security |
| 10 RESOURCE-EXHAUSTION | RES-01, RES-03 | security |
| 11 CUSTOM-ACCOUNT-CHECK-AUTH | ACCT-01, ACCT-02 | security |
| 12 MALFORMED-BYTES | BYTES-01 | security |

`quality` tier classes are QA or Low unless an attacker can force the panic or cost onto another user's critical path.

## Lens B additions

Soroban items for Lens B (`engine/mindsets.md`):

- **[Edge Case]** What happens with `amount = 0`, `amount = 1` (one stroop for a 7-decimal SAC), a negative `i128`, `i128::MAX`, or the first and last depositor? Is the sign validated at the entry point (TOK-01)?
- **Rounding**: for each division in fee, share, price or debt math, which direction does the remainder go, and who gains by splitting one operation into many (ARITH-03)?
- **Decimals**: 7-decimal SAC amounts against custom tokens with other decimals; normalization at registration (TOK-05).
- **Casts and operators**: `as` casts, `wrapping_*` / `saturating_*`, `^` used as a power, and the release profile's `overflow-checks` (ARITH-01, ARITH-02, ARITH-04).
- **Payment destination correctness (Module O)**: is the recipient the stored admin, the caller-supplied `to`, or the token holder? Double payout? Conditional payment with unconditional cost?
- Value moves only through token contracts (XLM is a SAC): there is no native value attached to calls, but every token call is an external call (Lens C).

## Lens C additions

Soroban items for Lens C (`engine/mindsets.md`):

- **Callee identity**: every `*Client::new(&env, &addr)`, `invoke_contract` and `try_invoke_contract` whose `addr` comes from arguments or user storage (XC-01, TOK-03).
- **Return values**: price, rate and balance returns used without range, sign and freshness checks (XC-02).
- **Failure semantics**: a failing plain call reverts the whole transaction; `try_` calls let the caller continue, and what the continuation assumes is the bug (XC-04). Reentrancy is not reachable (XC-03).
- **Auth trees**: calls that consume a user's pre-signed auth without re-authorizing them (AUTH-03), and `authorize_as_current_contract` entries broader than the one sub-invocation needed.
- **Versions**: `soroban-sdk` version in `facts.json` `sdk` (below 22: no `__constructor`), and the OpenZeppelin `stellar-contracts` version (macro-generated entry points and guards differ across versions).

## Lens D additions

Soroban items for Lens D (`engine/mindsets.md`):

- **[Spec Auditor]** Does the token implementation match SEP-41 (amounts, auth of `from` vs `spender`, `approve` with `expiration_ledger`, event shapes)? Does an oracle consumer match SEP-40? Do upgradeable contracts follow their stated upgrade interface?
- **TTL**: for each persistent or instance entry, where is `extend_ttl` called and by whom; for each `temporary()` write, is the data expendable (TTL-01 to TTL-03)?
- **Storage layout**: key enum variants, tuple shapes and struct fields across versions (STOR-01, UPG-02); user-controlled keys (STOR-02); per-user lists in one entry (STOR-04); large `instance()` data (STOR-03).
- **Resource limits**: loops and batches over growable data, per-iteration storage reads and events, `__check_auth` signature counts (RES-01 to RES-03).
- **Errors**: `unwrap` / `expect` / `Map::get` on state an attacker can shape (PANIC-01); error-code renumbering across upgrades.

## Detector modules (Soroban)

Soroban items for the detector (`engine/phases/detect.md`).

### Module A: Untrusted Recipient Analysis

For every token `transfer` (and `transfer_from`, `burn`, `clawback`-exposed flows) to an `Address` that is NOT the authorizing caller or a known protocol address. Any `Address` may be a contract account with its own `__check_auth`, and a SAC recipient needs a trustline and an authorised account: a missing trustline or frozen recipient makes the transfer fail, which reverts the transaction. A plain token transfer does not call recipient code, so there is no receiver callback to exploit (XC-03); the failure mode is a revert in a shared flow (TOK-02, RES-02).

### Module B: Type Cast Safety

Check EVERY integer cast and conversion: `as` between widths (truncates silently), `try_into()` between `i128`, `u128`, `u64`, `u32` (returns `Result`; what does the `unwrap` or default do), `i128` amounts used as `u32` indexes or loop bounds, signed to unsigned. For each:
- Is the failure case `unwrap()` / `expect()` (panic DoS: who can trigger it, on whose path: PANIC-01) or replaced by a default (silent wrong value)?
- Is the sign of an `i128` amount checked before the cast or the math (TOK-01)?
- `BytesN<N>` / `Bytes` conversions and `from_xdr` on caller bytes (BYTES-01).

### Module F: Token Compatibility

- Token kind: SEP-41 custom contract, wrapped classic asset (SAC) or native XLM (SAC). Allowlisted or permissionless (TOK-03)?
- `transfer` panics on failure and returns no bool; do not report an unchecked return value on it. What happens when it fails (frozen, no trustline, insufficient balance): does the whole flow revert (TOK-02)?
- `decimals()` read, not assumed (TOK-05). Zero and negative amounts rejected (TOK-01).
- Received amount versus nominal amount for custom tokens that charge transfer fees: balance before and after, where it matters.
- `transfer_from` flows: spender authorized, `from` not caller-chosen (TOK-04); allowance expiry (`expiration_ledger`).

### Module G: Factory/Deployment Patterns

- `deployer().with_address(.., salt)` with a caller-chosen salt: can someone deploy the predicted address first (DEPLOY-01)?
- Separate deploy and `initialize` calls: can someone else initialize (INIT-01)? Is `__constructor` used with validated arguments (INIT-02)?
- Who may deploy, and does the factory remain admin of the children it deploys?

### Module O: Payment/Distribution Flow Tracing

1. **Trace each payment**: for every token `transfer`, `mint`, `burn` or SAC admin call — WHO is the actual recipient? The stored admin, a caller-supplied `to`, a configured fee recipient? Verify the recipient and the authorized payer are semantically correct (AUTH-01, AUTH-03).

### Question additions

- **Q3.7 [ACCESS CONTROL EXHAUSTIVE CHECK]**: List EVERY entry point of every `#[contractimpl]` block (including default methods of `#[contracttrait]` traits mixed in with `#[contractimpl(contracttrait)]`, from soroban-sdk or OpenZeppelin: open the trait) that writes storage, calls another contract or upgrades code. For each: WHO can call it? Which `Address` is authorized with `require_auth`, and is it the one whose rights are consumed (AUTH-01 to AUTH-03)? Especially: admin setters, `initialize`, `upgrade` / `migrate`, sync or checkpoint functions, and functions that pass a user's address to a token or another contract.
- **Q6.3**: Can external calls FAIL SILENTLY? (`try_invoke_contract` / `try_*` client errors ignored; a `Result` dropped; a `let _ =` on a call result: XC-04)

### Rules

- **Track OpenZeppelin `stellar-contracts` usage.** Don't flag standard library implementations as custom bugs; do check how they are wired (macro-generated entry points, overridden default methods, role-admin paths: AUTH-05, FP-3).
- **`view` and `guards` in `facts.json` are hints, never proof** (see "Extractor limits" under "Recon additions"). Empty `guards` on a `mutating` entry point is a strong lead; non-empty `guards` still needs the code read.

## Recon additions

Soroban items for recon (`engine/phases/recon.md`).

### Analyzer command (Step 2b)

(unverified: Scout's flags are from its README and Scout is not installed here; confirm with
`cargo scout-audit --help`.) `A` is the audit folder (`<TARGET>/.audit/soroban`), `<ROOT>` the workspace root
that holds `Cargo.toml`; both absolute. Step 1, the tool run:

```bash
bash CORE/chains/soroban/recon/run-scout.sh <ROOT> A
```

`recon/run-scout.sh` keeps the build out of the user's tree the way `recon/extract.sh` does: target dir under
`A`, `Cargo.lock` backed up to `A/Cargo.lock.chainsec-scout-backup` and restored byte-for-byte (or removed if it
did not exist), also when the run is interrupted. It refuses (exit 2) while any `A/Cargo.lock.chainsec-*-backup`
is left over from an earlier run: restore that lock first, as the message says. It writes SARIF to
`A/analyzers/scout.json` and keeps it whenever it is JSON with a `runs` list, even if Scout exits non-zero on
findings (exit 0); with no usable SARIF it removes the file and exits 1. A cold first run builds Scout's nightly
toolchain and dylint drivers and can take many minutes: give the command a long tool timeout (or run it in the
background and wait for it). Step 2, the analyzer `run` script from `pack.json`, is then
`python3 CORE/chains/soroban/recon/scout-summary.py A/analyzers/scout.json A/analyzers/scout.md`.

- Scout compiles the project and uses a pinned nightly through `cargo-dylint`; it can fail on a project whose toolchain or SDK it does not support. Failure (exit 1) is not a ChainSec error: treat the pre-scan as failed ("scout pre-scan: SKIPPED (failed)") and delete both files.
- `recon/scout-summary.py` maps each SARIF `ruleId` to its pattern ID and tier from `patterns/README.md` and lists security-tier rows first. Scout declares every lint `Warn` (its severity lives only in lint metadata), so the SARIF level carries no severity: security-tier classes are the H/M signal; quality-tier classes are QA (unwrap, expect, panic, iterators, `mem::forget`, SDK version). An `unknown` tier is a detector not in `patterns/README.md`: read its message before ranking it.
- Scout rule IDs map to the pack's pattern IDs (`patterns/README.md`): `_` becomes `-`, upper-cased, a `scout::` style prefix dropped, and three lint names that differ from their detector mapped (`unexpected_revert_warn`, `integer_overflow_underflow`, `iterator_over_indexing`). A hit is a lead for that pattern, not a finding.

### Project identification (Step 1)

- Manifests: workspace root `Cargo.toml` (`[workspace] members`, `[profile.release]`), each crate's `Cargo.toml` (`soroban-sdk` version, `crate-type = ["cdylib"]`), `Cargo.lock`, `stellar` CLI config.
- **Compile status**: `facts.json` `compile` is `ok` (`cargo check` passed), `failed`, `timeout` (`cargo check` ran past `CHAINSEC_COMPILE_TIMEOUT`, default 100 seconds) or `unknown` (no `cargo`, `CHAINSEC_NO_COMPILE=1`, or a stale `Cargo.lock` backup). Facts come from source either way. `failed`, `timeout` and `unknown` are a PoC prerequisite risk: note the status in recon.md, and before the PoC phase confirm the crate builds (a cold first build can take minutes).
- **SDK version**: read `facts.json` `sdk`. Flag SDK below 22: `__constructor` is unavailable, so a guarded `initialize` is the only init path (INIT-01).
- **Release profile**: read `[profile.release] overflow-checks` in the workspace root `Cargo.toml` (member manifests do not set profiles). Missing or `false` is OVERFLOW-CHECK (ARITH-01).
- **Workspace members**: list every member crate; which build to wasm (`cdylib`) and which are libraries shared by several contracts.
- **OpenZeppelin `stellar-contracts`**: `#[contractimpl(contracttrait)]` parents in `facts.json` `units[].parents` (`#[contracttrait]` is a soroban-sdk macro; OpenZeppelin uses it too) have default methods that become live entry points the extractor cannot list: open the trait to enumerate them (they can be permissionless or guarded by macro attributes).
- **Key dependencies**: OpenZeppelin `stellar-contracts`, `soroban-fixed-point-math`, Blend, Soroswap, Reflector oracle (SEP-40), Allbridge, other token and oracle crates.

### Extractor limits (read code, not just facts)

`recon/extract.py` is a line-based heuristic extractor. Its known limits:
- `require_auth` inside an `if` branch counts as a full guard: conditional auth looks guarded.
- Method-style helpers (`x.helper()`, `Storage::new(e).write_x()`) are not followed: effects and guards behind them are missed.
- A storage tier handle passed into a helper as a parameter is not tracked: writes look like "view".
- A `... via <helper>` guard can come from a same-name function in another in-scope crate when the caller's crate defines none: open the helper to confirm.
- Nested block comments are not handled.
- Any call named `update_current_contract(...)` or `update_current_contract_wasm(...)` counts as an upgrade, including a project helper with that name: confirm it reaches the deployer.
- Default methods of `#[contractimpl(contracttrait)]` impls (soroban-sdk `#[contracttrait]` traits, including OpenZeppelin's) are macro-generated and invisible; `units[].parents` lists those traits.
- `#[has_role]` / `#[has_any_role]` are not treated as guards (membership check only, no `require_auth`); `only_owner`, `only_admin`, `only_role` and `only_any_role` are (`auth_macro` sites). Whether those expand to `require_auth` is read from the macro source, not verified by the extractor.
- Not available in facts: function arguments, call targets, `extend_ttl` calls.

So `view` and non-empty `guards` are hints, never proof; empty `guards` on a `mutating` entry point is a strong lead.

### Scope expansion (Step 3)

- OpenZeppelin `stellar-contracts` is excluded (`pack.json` `novelty_allowlist`) — only project-specific crates.
- A project library crate (storage, admin or math helpers) used by contract crates is in scope and joins the cluster of every contract that uses it (`recon/clustering.md`).
- Crates a Tier 1 contract depends on (`path` dependencies, workspace library crates) that are not in the `novelty_allowlist` are scored and auto-promoted like parent contracts (`engine/phases/recon.md` Step 3).
- `novel_code_bonus` — `# +15 if NOT from OpenZeppelin stellar-contracts`

### Risk-score counters (Step 3)

Where (counted per file by `recon/extract.py`, weights in `pack.json` `risk_weights`):
- **external_calls** (×5): `*Client::new(..)` constructions, `invoke_contract` / `try_invoke_contract`, `deployer()` calls and `update_current_contract_wasm` / `update_current_contract` calls, inside functions. Client construction counts the callee, not each method call.
- **state_writers** (×4): entry points that contain a storage write (`instance()` / `persistent()` / `temporary()` `set`, `remove`, `update`, `try_update`), including writes reached through followed same-crate helpers.
- **upgrades** (×6): `update_current_contract_wasm` and `update_current_contract` calls: code replacement is the highest-impact operation.
- **token_transfers** (×5): method calls named `transfer`, `transfer_from`, `burn`, `burn_from`, `mint` or `clawback`. Soroban has no `payable`; this counter plays that role. Any method with one of those names counts, token or not.
- **unchecked_math** (×2): `wrapping_*`, `overflowing_*` and `unchecked_*` calls plus `as` casts to a primitive integer type: silent wrap or truncation. Plain `+ - *` are not counted; whether they panic depends on `overflow-checks` (ARITH-01).
- **unguarded_mutators** (×6): externally visible `mutating` entry points (not `__constructor` / `__check_auth`) with empty `guards`: the strongest signal for MISSING-AUTH (AUTH-01).
- **novel_code_bonus**: +15 if the file is not matched by `pack.json` `novelty_allowlist`.
- **value_handling_bonus**: +10 if the file moves tokens.
- Soroban has no `payable` functions, assembly or `unchecked` blocks; those Solidity terms score zero. Counters are line-based hints: confirm by reading the code.

### Untrusted Recipient Map (Step 3c)

List every token transfer where the recipient is NOT the authorizing caller and NOT a hardcoded protocol address:
- Caller-supplied `to` or `recipient` arguments, including contract accounts with `__check_auth`
- Fee, reward and refund recipients read from storage that a non-admin can influence
- SAC recipients that may lack a trustline or be unauthorised (transfer fails: TOK-02)
- Cross-chain recipients encoded in bridge payloads (`domains/defi/modules/cross-chain-bridge.md`)

### Attacker mindset (Step 4)

3. **What's novel?** What code was written specifically for this protocol (not OpenZeppelin `stellar-contracts`)? Novel code = novel bugs. Flag custom accounts (`__check_auth`), hand-rolled token implementations, custom upgrade and migration code, custom signature schemes over app data, and hand-rolled admin or role checks.

### Integration checklists (Step 5)

**Stellar Asset Contract (SAC) Integration**: token address allowlisted or permissionless; trustline and authorization failures survivable; issuer freeze (`set_authorized`) and clawback exposure; 7 decimals; transfers to or from the issuer mint or burn (verify against the asset's flags).

**OpenZeppelin Stellar Integration**: `stellar-contracts` version; which traits are mixed in with `#[contractimpl(contracttrait)]` and which default methods are overridden; `#[only_owner]` / `#[only_role]` on every admin path; role-admin and ownership-transfer flow; pausable and upgradeable helpers wired through the contract's own auth.

**Blend Integration** (lending pools with `submit`-style request batches): request types validated, health factor checked after the batch, backstop and pool addresses pinned, oracle reads checked (see Reflector).

**Soroswap Integration**: router and pair addresses pinned, `min_out` and deadline supplied by the caller, path tokens allowlisted, pair reserves not used as a spot oracle.

**Reflector oracle Integration** (SEP-40 `lastprice`): price positive, `timestamp` freshness against a ledger-time window, decimals read from the oracle and normalized per asset, oracle address pinned (XC-02).

## State audit additions

Soroban original of the Phase 4 operation-ordering example in `engine/phases/state.md`:

```
fn withdraw(env: Env, user: Address, amount: i128):
  1. READ  env.storage().persistent().get(&DataKey::Shares(user))   <- reads coupled state
  2. WRITE env.storage().persistent().set(&DataKey::Shares(user), s - x)  <- updates primary
  3. CALL  TokenClient::new(&env, &token).transfer(..)             <- EXTERNAL CALL
  4. WRITE env.storage().instance().set(&DataKey::TotalShares, t - x)     <- updates coupled AFTER external call!
```

A failing call reverts the whole transaction, so the ordering matters mainly when a `try_` call swallows the failure or when the callee is attacker-chosen and burns budget (XC-03, XC-04).

## Security strengths examples

Soroban examples for the Security Strengths section of `engine/report-template.md`:

- **Access control model**: Which pattern (stored admin with `require_auth`, OpenZeppelin `#[only_owner]` / `#[only_role]`, custom account)? Consistent across all `mutating` entry points and macro-generated methods?
- **Authorization hygiene**: every `Address` whose rights are consumed is authorized, at every layer that spends it (AUTH-03)?
- **Arithmetic safety**: `overflow-checks = true` in the release profile, `checked_*` on amounts, `i128` sign validated at entry points?
- **Initialization**: `__constructor` with validated arguments instead of a front-runnable `initialize`?
- **Upgrade safety**: `update_current_contract_wasm` behind admin auth and a delay? Versioned, admin-gated `migrate`? Key enums stable across versions?
- **TTL and storage hygiene**: critical entries extended on hot paths, nothing durable in `temporary()`, per-user data under fine-grained keys?
- **Battle-tested dependencies**: which `stellar-contracts` version? Current?

Example bullet: `- **[Category]**: [Specific observation with contract/file names — e.g., "All 6 state-mutating entry points in vault/src/lib.rs call require_auth on the stored admin or the debited user before any storage write"]`
