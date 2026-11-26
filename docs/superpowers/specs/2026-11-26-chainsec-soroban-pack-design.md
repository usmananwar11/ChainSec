# ChainSec Soroban pack: design

**Scope:** Sub-project 3. A Stellar Soroban chain pack for the existing engine, built the same way as
the Cairo pack (`docs/superpowers/specs/2026-11-24-chainsec-cairo-pack-design.md`). Out of scope:
Stellar Classic operations (no contracts), pre-release SDKs (< 20), and auditing more than one root
per chain (still deferred in the engine).

**Approach:** port, then adapt. `chains/soroban/` mirrors `chains/cairo/`. Its security knowledge is
ported, with credit, from two sources:

| Source | License | What is ported |
|---|---|---|
| CoinFabrik `scout-soroban` (commit `53157fd`) | MIT | 23 detector classes → `patterns/<ID>.md`; vulnerable/remediated test cases → snippet regression suite |
| `stellar/stellar-dev-skill` `skills/smart-contracts/security.md` (commit `9098e8b`) | Apache-2.0 | 12 vulnerability classes, the threat model, "what the platform rules out", token-consumer review and checklists → `heuristics.md`, `patterns/`, `primers/` |

Apache-2.0 content keeps its license notice and a "modified by ChainSec" note in `ATTRIBUTION.md`.
Veridise's Soroban checklist and sorobansecurity.com have no clear license: link to them, do not copy.

ChainSec writes the parts the engine needs: `pack.json`, the extractor, the Scout summary, the PoC and
fuzz guides, the Soroban modules and FP patterns.

## 1. Engine changes

Kept small, as for Cairo. A neutrality pass over `engine/`, `prompts/` and `domains/` replaces the
EVM-only wording that misleads on Soroban (for example "1 wei", `payable`, "storage slot",
`delegatecall`) with generic terms; each pack's heuristics give the concrete forms. No new manifest
fields. Multiple roots per chain stay deferred.

## 2. Pack contents (`chains/soroban/`)

- `pack.json`:
  - chain `soroban`, prefix `SOROBAN`, extension `.rs`.
  - Detection marker `Cargo.toml` containing `soroban-sdk`. No fallback glob: `**/*.rs` would match
    every Rust project. Users of unusual layouts pass `--chain soroban`.
  - A workspace whose root `Cargo.toml` names `soroban-sdk` (usually in `[workspace.dependencies]`)
    is one root. A workspace that names it only in member crates gives several roots, and the
    engine's existing "one root per chain" stop applies.
  - Scope `src/**/*.rs`, `contracts/**/src/**/*.rs`, `crates/**/src/**/*.rs`,
    `packages/**/src/**/*.rs`. Excluded: `target/`, `tests/`, `test/`, `test.rs`, `tests.rs`,
    `test_*.rs`, `*_test.rs`, `testutils*`, `mock*/`, `fuzz/`, `benches/`, `build.rs`. Inline
    `#[cfg(test)] mod … { }` blocks are blanked by the extractor.
  - Tools: `python3` and `cargo` required (compile check, PoC, fuzz). Optional: `stellar` CLI
    (wasm build for the PoC fallback, ledger snapshots) and `cargo-scout-audit`.
  - Value unit stroop (7 decimals), code fence `rust`, unit of analysis `contract_crate`.
- `recon/extract.sh` + `recon/extract.py`: a Python standard-library parser over comment- and
  string-stripped Rust (raw strings, byte strings and char literals handled, lifetimes left alone).
  It emits `facts.json` (mode `regex`) with:
  - units: `#[contract]` structs (kind `contract`, parents = traits implemented in
    `#[contractimpl]` blocks), and `#[contractclient]` / `#[contracttrait]` traits (kind `interface`);
  - entry points: `pub fn` in inherent `#[contractimpl]` impls and every fn in trait
    `#[contractimpl]` impls; visibility `constructor` (`__constructor`), `check_auth`
    (`__check_auth`) or `external`; mutability `mutating` or `view`, resolved transitively through
    helper functions defined in scope;
  - guards: `require_auth(<receiver>)`, `require_auth_for_args(<receiver>)`, the same through a helper
    (`… via <helper>`), and OpenZeppelin Stellar auth macros (`#[only_owner]`, `#[only_role]`, …);
  - auth sites: `require_auth`, `require_auth_for_args`, `authorize_as_current_contract`,
    `auth_macro`, `check_auth`;
  - storage writes: `env.storage().{instance,persistent,temporary}().{set,remove,update,try_update}`,
    target `<tier>:<key>`;
  - external calls: `*Client::new(`, `invoke_contract`, `try_invoke_contract`, `deployer()`,
    `update_current_contract_wasm`;
  - value transfers: token `transfer`, `transfer_from`, `burn`, `burn_from`, `mint`, `clawback`;
  - counters per file: `external_calls`, `state_writers`, `upgrades`, `token_transfers`,
    `unchecked_math`, `unguarded_mutators` (mutating, non-constructor entry points with no guard);
  - top-level `compile` and `sdk` (soroban-sdk version from `Cargo.lock`, else `Cargo.toml`).

  `cargo check` runs only when `cargo` is present. Its target dir sits next to `facts.json`, so the
  project's `target/` is untouched; a `Cargo.lock` that the check creates is removed again.
- `recon/clustering.md`: one `#[contract]` type, its `#[contractimpl]` blocks and the crate's helper
  modules it calls (storage, admin, events). Shared library crates join every cluster that uses them.
  Caps of ~1500 LOC and 8 clusters, the same as the other packs.
- `recon/scout-summary.py`: an optional analyzer table from Scout's SARIF output, like the Slither
  and Caracal summaries.
- `heuristics.md` (engine-ID mapping table, Soroban core heuristics, Scout and Stellar classes),
  `fp-patterns.md`, `module-triggers.md`, `primers/soroban-vs-evm.md`, and `modules/`:
  - `soroban-auth.md`: `require_auth` placement, auth trees, middleware replay, `__check_auth`;
  - `storage-and-ttl.md`: storage tiers, TTL and archival, key collisions, instance-storage growth;
  - `upgrades-and-init.md`: `update_current_contract_wasm`, `__constructor` vs `initialize`,
    migrations;
  - `token-integration.md`: SEP-41, the Stellar Asset Contract, `i128` amounts, clawback and
    authorization flags, decimals;
  - `cross-contract-calls.md`: untrusted contract addresses, `try_invoke` error handling, trusting
    return values, the host's reentrancy ban;
  - `resource-limits.md`: per-transaction CPU, memory and ledger-entry limits, unbounded `Vec`/`Map`.
- `patterns/`: 23 Scout classes (ID = detector name upper-cased, for example `UNSAFE-UNWRAP`) and the
  12 Stellar classes (for example `MISSING-AUTH`, `AUTH-REPLAY-MIDDLEWARE`), with `ATTRIBUTION.md`.
- `poc/guide.md`: soroban-sdk `testutils` integration tests (`Env::default()`, `register`,
  `mock_all_auths` vs explicit `mock_auths`, `ledger().set_timestamp`, `env.auths()`). If the crate
  is `cdylib`-only, the fallback imports the built wasm with `contractimport!`. Ledger snapshots
  (`stellar snapshot create`) stand in for fork tests.
- `fuzz/guide.md`: stateful invariant tests as integration tests that run seeded random action
  sequences with no new dependencies; `proptest` when the project already has it; `cargo-fuzz`
  for longer runs. It says plainly that there is no Foundry-style invariant runner.

## 3. Benchmark (`benchmarks/soroban/`)

- Regression suite: Scout's vulnerable/remediated test cases (47 pairs), grouped by class into
  Cargo workspaces and run with `chainsec-audit --quick`. Detected classes and flags on remediated
  cases are counted. This is a regression check, not acceptance: the patterns come from the same
  source.
- Acceptance: 2–3 public Code4rena Soroban contests with official High/Medium lists: Blend v2
  (2025-02), LayerZero Stellar endpoint (2026-04) and K2 (2026-04, optional). Baseline: the same
  agent and model with the official `stellar-dev-skill` loaded and asked for a High/Medium audit of
  the same commit and scope. Pass: ChainSec recall ≥ baseline and ChainSec FP ≤ baseline FP. Scoring
  reuses `tools/score_benchmark.py` (exact 1, partial 0.5).

## 4. Errors and degraded modes

- Without `cargo`, or when the check fails (old SDK, missing toolchain), facts still come from
  source and the compile status is `unknown` or `failed`.
- Without Scout, tooling is degraded and the analyzer table is skipped.
- No `soroban-sdk` crate found: detection returns nothing; `--chain soroban` still runs the extractor,
  and its facts are empty.

## 5. Testing

- Extractor unit tests on the fixture and on small generated trees: transitive guards and
  mutability, comment, string and char stripping, `#[cfg(test)]` blanking, contract traits as
  parents, workspace scope, `sdk` version.
- Detection tests: the real pack finds the fixture, ignores a plain Rust crate, collapses a workspace
  with a root `soroban-sdk` dependency, and reports two roots otherwise.
- The pack lint validates `pack.json` and the files it references (existing `tools/lint_skills.py`).
- Port coverage: every Scout test-case class has `patterns/<ID>.md`; every Stellar class heading has
  its pattern. Both skip when the sources are not on the machine.
- `tests/fixtures/soroban-basic`: a vault crate with a planted bug, a `withdraw(from, to, amount)`
  that debits `from` without `from.require_auth()`. Its PoC and fuzz examples are run with `cargo test`.
- Quick smoke test in Claude Code (and OpenCode when available).
