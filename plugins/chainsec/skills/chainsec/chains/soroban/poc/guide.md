# Soroban PoC guide (soroban-sdk testutils)

Pack half of `engine/poc/workflow.md` for Soroban. Framework: `cargo test` with `soroban-sdk`
`testutils` (native, in-process `Env`). Verified on `tests/fixtures/soroban-basic` with cargo 1.99 /
soroban-sdk 26.1.1.

Placeholders used by `pack.json` `poc.run`: `<CORE>` = the engine's core skill folder (the same `CORE`
the pipeline uses to run the extractor); `<crate>` = contract crate folder relative to the audited root
(`.` for a single crate); `<ID>` = finding ID (`SOROBAN-001`); `<id>` = lower-case ID with `-` replaced
by `_` (`soroban_001`), because Rust test target names cannot contain `-`.

## soroban-sdk testutils workflow steps

### 1. Recon the PoC environment (MANDATORY)

- `Cargo.toml` needs `soroban-sdk` with `features = ["testutils"]` under `[dev-dependencies]`:

  ```toml
  [dev-dependencies]
  soroban-sdk = { version = "<same as [dependencies]>", features = ["testutils"] }
  ```

  Use the same `soroban-sdk` version as `[dependencies]`.

  If it is missing, add it in a **scratch copy** of the project, never in the user's tree.
- `[lib] crate-type` must include `"lib"` or `"rlib"` so an integration test can
  `use <crate_name>::...`. If it is `["cdylib"]` only, use the wasm fallback in step 2.
- Note `[package] name`: dashes become underscores in `use` (`chainsec-vault` -> `chainsec_vault`).
- A project with existing tests: run its own `cargo test` once first, in a **scratch copy** (the helper
  runs only `--test <name>`, never the project's whole suite) to confirm the toolchain and dependencies
  resolve.

### 2. Choose the harness: native, wasm import, or ledger snapshot

- **Native (default):** link the crate and `env.register(Contract, (ctor args,))`. Fast, full testutils.
- **Wasm fallback** (cdylib-only crate, or the bug depends on the compiled artifact): never build in
  the user's tree. Copy `<TARGET>/<root>` to `<TARGET>/.audit/soroban/wasm-src/` (excluding `target/` and
  `.audit/`) and build there with `CARGO_TARGET_DIR=<TARGET>/.audit/soroban/target stellar contract build
  --out-dir <TARGET>/.audit/soroban/wasm`. Path dependencies outside `<root>` break in the copy; if so,
  stop and report. Then in the test
  `mod c { soroban_sdk::contractimport!(file = "<TARGET>/.audit/soroban/wasm/<name>.wasm"); }` and
  `env.register(c::WASM, (args,))`. Use the absolute path: it resolves against the user crate's
  `CARGO_MANIFEST_DIR`.
- **Ledger snapshot** (contract already deployed): `stellar snapshot create --address <C> --output json
  --out <file>` and `Env::from_ledger_snapshot_file`. Needs an RPC/archive; without one, stay native.
  `from_ledger_snapshot_file` hard-codes the default config (snapshots on), so write
  `let mut env = Env::from_ledger_snapshot_file(..); env.set_config(EnvTestConfig { capture_snapshot_at_drop: false });`

### 3. Write the test

Tests live in `.audit/soroban/poc/<ID>/chainsec_poc_<id>.rs`. The pack's `poc.run` calls the helper
`chains/soroban/poc/run-test.sh <crate-dir> <test-file> <work-dir>`, which copies the file into the
crate's `tests/`, runs `cargo test --test chainsec_poc_<id>` with its target dir under
`.audit/soroban/target`, and then restores the crate exactly: the copied test and any `tests/` folder it
created are removed, `Cargo.lock` is restored byte-for-byte (or removed if it did not exist). It refuses
(exit 2) to overwrite an existing `tests/<name>`. Every test function name starts with
`chainsec_poc_<id>`.

Create the `Env` with `Env::new_with_config(EnvTestConfig { capture_snapshot_at_drop: false })`, not
`Env::default()`: the default writes `test_snapshots/*.json` into the audited crate every time an `Env`
drops. `EnvTestConfig` exists in soroban-sdk 21 and later; for older SDKs the helper removes a
`test_snapshots/` folder it created (one that already existed is left alone). That is why every `Env` must be snapshot-free: a
pre-existing `test_snapshots/` is not cleaned, so new files would leak into it.

Verified skeleton (planted bug: `withdraw` debits `from` without `from.require_auth()`):

<!-- chainsec:verified-poc-skeleton -->

```rust
//! PoC SOROBAN-001: withdraw debits `from` without `from.require_auth()`.
use chainsec_vault::{Vault, VaultClient};
use soroban_sdk::{
    testutils::{Address as _, EnvTestConfig},
    token, Address, Env,
};

#[test]
fn chainsec_poc_soroban_001_withdraw_without_auth() {
    // No test_snapshots/ files are written into the audited crate.
    let env = Env::new_with_config(EnvTestConfig { capture_snapshot_at_drop: false });
    let admin = Address::generate(&env);
    let victim = Address::generate(&env);
    let attacker = Address::generate(&env);
    let sac = env.register_stellar_asset_contract_v2(admin.clone());
    let token = token::Client::new(&env, &sac.address());
    let vault = env.register(Vault, (admin.clone(), sac.address()));
    let client = VaultClient::new(&env, &vault);

    env.mock_all_auths();
    token::StellarAssetClient::new(&env, &sac.address()).mint(&victim, &1_000);
    client.deposit(&victim, &1_000);
    env.set_auths(&[]); // from here on, no signature is mocked

    client.withdraw(&victim, &attacker, &1_000);

    assert!(env.auths().is_empty(), "no address authorized the withdrawal");
    assert_eq!(token.balance(&attacker), 1_000);
    assert_eq!(client.balance(&victim), 0);
}
```

Run through the helper on a copy of the fixture, it prints
`test chainsec_poc_soroban_001_withdraw_without_auth ... ok`. Negative control: adding
`from.require_auth();` as the first line of `withdraw` makes the same test FAIL with
`Error(Auth, InvalidAction)`, so the test asserts the bug and not the setup.

### 4. testutils features real PoCs use

| Need | API |
|---|---|
| Fresh accounts / contracts | `Address::generate(&env)` (`testutils::Address as _`) |
| Deploy with constructor | `env.register(Contract, (arg1, arg2))`; generated `ContractClient::new(&env, &id)` |
| Real token | `env.register_stellar_asset_contract_v2(admin)`, `token::Client`, `token::StellarAssetClient::mint` |
| Auth: allow everything | `env.mock_all_auths()` (use only for setup) |
| Auth: nothing signed | `env.set_auths(&[])`, then assert `env.auths().is_empty()` |
| Auth: specific signer | `env.mock_auths(&[MockAuth { address, invoke: &MockAuthInvoke { .. } }])` (import `soroban_sdk::testutils::{MockAuth, MockAuthInvoke}`) |
| Which auths were required | `env.auths()` |
| Time / ledger | `env.ledger().set_timestamp(t)` (needs `use soroban_sdk::testutils::Ledger as _;`), `env.ledger().with_mut(\|li\| li.sequence_number = n)` |
| Assert an error | `client.try_<fn>(..)` returns `Result`; match the `Err` |
| Resource DoS | `env.cost_estimate().budget()` / resources, after `env.cost_estimate().budget().reset_unlimited()` when setting up |

### 5. Assert the HARM, not the mechanism

Follow `engine/poc/assertion-protocol.md`: assert balances moved, admin changed, funds stuck, or an
invariant broken (as the skeleton asserts the attacker's token balance and the victim's vault balance).
"The call did not panic" is not harm.

### 6. Compile → run → fix

| Error | Fix |
|---|---|
| `no method ... register` / `Address::generate` not found | `testutils` feature missing under `[dev-dependencies]`, `testutils::Address as _` / `testutils::Ledger as _` not imported, or `MockAuth` / `MockAuthInvoke` not imported from `soroban_sdk::testutils` |
| `unresolved import <crate>` | crate is cdylib-only: add `"lib"` in a scratch copy or use the wasm fallback; check the underscore name |
| `Error(Auth, InvalidAction)` in a PoC meant to succeed | the target does call `require_auth`: the bug may not exist, or the PoC needs `mock_auths` for the right address |
| `#![no_std]` crate | the test file is a separate crate and may use `std`; add `extern crate std;` only if the lib's macros need it |
| Bug depends on `[profile.release] overflow-checks` | pass extra args through the helper: `... <work-dir> --release` |
| `test_snapshots/` appears | some `Env` still captures snapshots: `Env::default()`, or `from_ledger_snapshot_file` without `set_config(EnvTestConfig { capture_snapshot_at_drop: false })` |

After 5 failed compiles, stop and keep the finding at `[CODE-TRACE]` (see `engine/poc/workflow.md`).
