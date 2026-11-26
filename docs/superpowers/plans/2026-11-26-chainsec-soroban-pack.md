# ChainSec Soroban Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Stellar Soroban chain pack (`chains/soroban/`) to the ChainSec engine, at the same level as the Cairo pack: manifest, facts extractor, Scout analyzer summary, ported security knowledge, PoC and fuzz guides, a fixture, a snippet regression suite and a contest benchmark registry.

**Architecture:** The engine stays chain-neutral. Everything Soroban-specific lives in `plugins/chainsec/skills/chainsec/chains/soroban/` and is wired in through `pack.json`, as for Cairo (`docs/superpowers/plans/2026-11-24-chainsec-cairo-pack.md`). Scripts are standard-library Python plus bash. Security knowledge is ported, with credit, from CoinFabrik Scout (MIT) and Stellar's `stellar-dev-skill` (Apache-2.0).

**Tech Stack:** Python ≥ 3.11 stdlib, bash, `unittest`; Rust `cargo` + `soroban-sdk` 26.x `testutils` for the fixture, PoC and fuzz; optional `stellar` CLI 27.x and `cargo-scout-audit`.

**Spec:** `docs/superpowers/specs/2026-11-26-chainsec-soroban-pack-design.md`

**Branch:** `feat/soroban-pack`, created from `feat/cairo-pack` (it needs the Cairo branch's engine generalization). Rebase it onto `main` once `feat/cairo-pack` is merged.

**Sources (clone once, read-only):**

```bash
git clone https://github.com/CoinFabrik/scout-soroban ~/src/scout-soroban
git -C ~/src/scout-soroban checkout 53157fd4ddd9e388bf91138699f4e27a500aaef3
git clone https://github.com/stellar/stellar-dev-skill ~/src/stellar-dev-skill
git -C ~/src/stellar-dev-skill checkout 9098e8ba24de3299cda24b21bb5cb80aa1cb5d2b
```

Below, `SCOUT/` = `~/src/scout-soroban/` and `STELLAR/` = `~/src/stellar-dev-skill/skills/smart-contracts/`.
`PK/` = `plugins/chainsec/skills/chainsec/chains/soroban/`.

## Global Constraints

- Scripts: Python ≥ 3.11 **standard library only**; shell wrappers in bash. No `jq`.
- Paths in pack markdown are relative to the core skill folder (`chains/soroban/...`, `domains/defi/...`); `pack.json` paths are relative to the pack folder. The lint (`tools/lint_skills.py`) resolves every backticked core path and markdown link.
- `engine/`, `prompts/`, `runtimes/`, `domains/` stay chain-neutral (lint list: `solidity`, `forge`, `foundry`, `slither`, `openzeppelin`, `solmate`, `.sol`, `msg.sender`). Do not add Soroban terms there either.
- Ported content keeps its source IDs (Scout detector names upper-cased; Stellar class names as in the map in Task 7) and carries a `<!-- Ported from ... ; see ATTRIBUTION.md -->` line. Scout is MIT: keep its copyright notice. `stellar-dev-skill` is Apache-2.0: keep its notice, ship the license text, and state that ChainSec modified the material.
- Do not copy Veridise's checklist or sorobansecurity.com content (no clear license); link only.
- Never touch the user's project tree during audits: compile, PoC and fuzz builds use `CARGO_TARGET_DIR=<TARGET>/.audit/soroban/target`; a `Cargo.lock` that a check creates is removed again.
- `bash tests/run.sh` passes at the end of every task.
- Git: one local commit per task on `feat/soroban-pack`. **No `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" line.** Do not push unless the user asks.

## File Map

```
docs/superpowers/specs/2026-11-26-chainsec-soroban-pack-design.md        (done)
docs/superpowers/plans/2026-11-26-chainsec-soroban-pack.md               (this file)
plugins/chainsec/skills/chainsec/engine|prompts|domains/**  (wording)    T1
plugins/chainsec/skills/chainsec/chains/soroban/
├── pack.json                                                            T2
├── recon/extract.sh, recon/extract.py                                   T4
├── recon/scout-summary.py                                               T5
├── ATTRIBUTION.md, LICENSE-APACHE-2.0.txt                               T6 (T7 adds Stellar)
├── patterns/README.md, patterns/<23 Scout IDs>.md                       T6
├── patterns/<11 Stellar IDs>.md, primers/soroban-vs-evm.md              T7
├── heuristics.md, fp-patterns.md, module-triggers.md                    T8
├── recon/clustering.md, modules/*.md (6)                                T8
├── poc/guide.md                                                         T9
└── fuzz/guide.md                                                        T10
tests/fixtures/soroban-basic/{Cargo.toml,Cargo.lock,src/*.rs}           T3
tests/test_detect_chain.py (additions)                                   T2, T3
tests/test_extract_soroban.py                                            T4
tests/test_scout_summary.py                                              T5
tests/test_port_coverage.py (additions)                                  T6 (constants + Scout), T7 (Stellar)
tests/test_soroban_snippets.py                                           T11
benchmarks/soroban/snippets/{README.md,import_scout.py,cases.jsonl,make_projects.py,score_snippets.py}   T11
benchmarks/soroban/registry.yaml                                         T12
README.md, INSTALL.md, docs/PROGRESS.md, docs/smoke-tests.md             T13
.gitignore (target/)                                                     T3
```

## Pre-verified

Every script, test and Rust file in this plan was run on 2026-11-26 against a scratch copy of the repo
(rustc 1.99, cargo 1.99, soroban-sdk 26.1.0, stellar 27.0.0). Expected outputs below are the
observed ones. The fixture's `cargo test` build took about 55 s cold.

---

### Task 1: Engine wording pass for Soroban

Like Cairo's Task 1: the shared methodology must not steer a Soroban audit with EVM-only terms.

**Files:**
- Modify: hits from the grep below in `plugins/chainsec/skills/chainsec/{engine,prompts,runtimes,domains}/**/*.md`

- [ ] **Step 1: List EVM-only wording in shared files**

```bash
cd plugins/chainsec/skills/chainsec
grep -rnE '\bwei\b|\bgwei\b|payable|msg\.value|tx\.origin|storage slot|delegatecall|selfdestruct|\bEOA\b|ecrecover|block\.number|block\.timestamp' engine prompts runtimes domains
```

Known hit: `engine/mindsets.md:75` "amount=0, amount=1 wei, amount=MAX".

- [ ] **Step 2: Rewrite each hit to a generic term**

Rules: if the line is an instruction every chain follows, rewrite it generically and let the pack's
heuristics give the concrete form (for example "amount=1 wei" → "amount=1 (the smallest unit)";
"`msg.value`" → "native value sent with the call"; "storage slot" → "storage location";
"`block.timestamp`" → "the chain's block/ledger time"). If the line is an EVM example inside a
passage that already says it is an example, leave it. Change only the matched words, nothing else
on the line.

- [ ] **Step 3: Verify**

Run: `bash tests/run.sh`
Expected: lint `0 error(s)`, all tests OK. Re-run the Step 1 grep: only deliberate EVM examples remain.

- [ ] **Step 4: Commit**

```bash
git add plugins/chainsec/skills/chainsec
git commit -m "Make shared engine wording chain-neutral for Soroban"
```

---

### Task 2: Pack manifest and detection

**Files:**
- Create: `PK/pack.json` and one-line stubs for every file it references
- Modify: `tests/test_detect_chain.py`

**Interfaces:**
- Produces: `pack.json` keys used by later tasks: `scope` (T4), `extractor` = `recon/extract.sh` (T4), `analyzers[0]` = scout / `recon/scout-summary.py` / requires `cargo-scout-audit` (T5), `risk_weights` keys = counter names emitted by T4 (`external_calls`, `state_writers`, `upgrades`, `token_transfers`, `unchecked_math`, `unguarded_mutators`), `poc.run` placeholders `<TARGET> <root> <crate> <ID> <id> <test file>` (T9), `fuzz.run` fixed file `chainsec_fuzz.rs` (T10).

- [ ] **Step 1: Write the failing detection tests**

Append inside `class DetectChainTest` in `tests/test_detect_chain.py` (the fixture test is added in Task 3):

```python
    def test_real_soroban_pack_ignores_plain_rust(self):
        from helpers import make_tree
        root = make_tree({"Cargo.toml": "[package]\nname = \"cli\"\n[dependencies]\nserde = \"1\"\n"})
        r = run_py("detect-chain.py", root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["chains"], [])

    def test_real_soroban_pack_workspace_roots(self):
        from helpers import make_tree
        member = "[package]\nname = \"{}\"\n[dependencies]\nsoroban-sdk = {{ workspace = true }}\n"
        with_dep = make_tree({
            "Cargo.toml": "[workspace]\nmembers = [\"contracts/*\"]\n[workspace.dependencies]\nsoroban-sdk = \"23\"\n",
            "contracts/a/Cargo.toml": member.format("a"), "contracts/b/Cargo.toml": member.format("b")})
        without_dep = make_tree({
            "Cargo.toml": "[workspace]\nmembers = [\"contracts/*\"]\n",
            "contracts/a/Cargo.toml": member.format("a"), "contracts/b/Cargo.toml": member.format("b")})
        r = run_py("detect-chain.py", with_dep)
        self.assertEqual(json.loads(r.stdout)["chains"], [{"chain": "soroban", "root": "."}])
        r = run_py("detect-chain.py", without_dep)
        self.assertEqual(json.loads(r.stdout)["chains"], [{"chain": "soroban", "root": "contracts/a"},
                                                         {"chain": "soroban", "root": "contracts/b"}])
```

- [ ] **Step 2: Run and see them fail**

Run: `cd tests && python3 -m unittest test_detect_chain -v`
Expected: `test_real_soroban_pack_workspace_roots` FAILS (no soroban pack, `chains` is `[]`).

- [ ] **Step 3: Write `PK/pack.json`**

```json
{
  "chain": "soroban",
  "id_prefix": "SOROBAN",
  "extensions": [".rs"],
  "detect": {
    "markers": ["Cargo.toml"],
    "contains": ["soroban-sdk"]
  },
  "scope": {
    "include": ["src/**/*.rs", "contracts/**/src/**/*.rs", "crates/**/src/**/*.rs", "packages/**/src/**/*.rs"],
    "exclude": ["**/target/**", "**/tests/**", "**/test/**", "**/test.rs", "**/tests.rs", "**/test_*.rs",
                "**/*_test.rs", "**/testutils*", "**/mock/**", "**/mocks/**", "**/fuzz/**", "**/benches/**",
                "**/build.rs"],
    "fallback_include": ["**/*.rs"]
  },
  "tools": {
    "required": [
      { "name": "python3", "check": "python3 --version", "install": "https://www.python.org/downloads/", "purpose": "ChainSec scripts" },
      { "name": "cargo", "check": "cargo --version", "install": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh", "purpose": "compile check, PoC and fuzz tests (soroban-sdk testutils)" }
    ],
    "optional": [
      { "name": "stellar", "check": "stellar --version", "install": "cargo install --locked stellar-cli", "purpose": "wasm build for the PoC fallback and ledger snapshots" },
      { "name": "cargo-scout-audit", "check": "cargo scout-audit --version", "install": "cargo install cargo-dylint dylint-link && cargo install cargo-scout-audit", "purpose": "Scout static-analysis signal table during recon" }
    ]
  },
  "extractor": "recon/extract.sh",
  "analyzers": [ { "name": "scout", "run": "recon/scout-summary.py", "requires": "cargo-scout-audit" } ],
  "risk_weights": { "external_calls": 5, "state_writers": 4, "upgrades": 6, "token_transfers": 5,
                    "unchecked_math": 2, "unguarded_mutators": 6 },
  "loc_weight": 0.05,
  "novelty_bonus": 15,
  "value_bonus": 10,
  "novelty_allowlist": ["**/stellar-contracts/**", "**/openzeppelin*/**"],
  "unit_of_analysis": "contract_crate",
  "clustering": "recon/clustering.md",
  "value_unit": { "name": "stroop", "decimals": 7 },
  "code_fence": "rust",
  "modules_by_protocol": {
    "always": ["../../domains/defi/modules/access-control-state.md", "modules/soroban-auth.md",
               "modules/storage-and-ttl.md", "primers/soroban-vs-evm.md"],
    "dex-amm": ["../../domains/defi/modules/amm-mev-deep.md", "../../domains/defi/modules/economic-design.md",
                "../../domains/defi/modules/flash-loan-interaction.md", "../../domains/defi/primers/defi-dex-amm.md",
                "modules/token-integration.md"],
    "lending": ["../../domains/defi/modules/lending-liquidation-deep.md", "../../domains/defi/modules/oracle-analysis.md",
                "../../domains/defi/modules/economic-design.md", "../../domains/defi/primers/defi-lending.md",
                "modules/token-integration.md"],
    "vault": ["../../domains/defi/modules/vault-share-accounting.md", "../../domains/defi/modules/flash-loan-interaction.md",
              "modules/token-integration.md"],
    "governance": ["../../domains/defi/modules/governance-voting.md", "../../domains/defi/primers/defi-staking-governance.md"],
    "staking": ["../../domains/defi/modules/economic-design.md", "../../domains/defi/primers/defi-staking-governance.md"],
    "nft-gamefi": ["../../domains/defi/primers/gamefi-nft.md"],
    "bridge": ["../../domains/defi/modules/cross-chain-bridge.md", "modules/cross-contract-calls.md",
               "../../domains/defi/primers/bridge-crosschain.md"],
    "proxy-upgradeable": ["modules/upgrades-and-init.md"],
    "wallet-aa": ["modules/soroban-auth.md"]
  },
  "poc": { "framework": "soroban-sdk-testutils", "run": "cd <TARGET>/<root>/<crate> && mkdir -p tests && cp <TARGET>/.audit/soroban/poc/<ID>/<test file> tests/ && CARGO_TARGET_DIR=<TARGET>/.audit/soroban/target cargo test --test chainsec_poc_<id> 2>&1; rm -f tests/<test file>", "guide": "poc/guide.md" },
  "fuzz": { "framework": "soroban-sdk-testutils-seeded", "run": "cd <TARGET>/<root>/<crate> && mkdir -p tests && cp <TARGET>/.audit/soroban/fuzz/tests/chainsec_fuzz.rs tests/ && CARGO_TARGET_DIR=<TARGET>/.audit/soroban/target cargo test --test chainsec_fuzz -- --nocapture 2>&1; rm -f tests/chainsec_fuzz.rs", "guide": "fuzz/guide.md" }
}
```

Notes for the implementer:
- No `fallback_glob`: `**/*.rs` would claim every Rust repo. Users with odd layouts pass `--chain soroban`.
- `<crate>` in `poc.run`/`fuzz.run` is the contract crate's folder relative to `<root>` (`.` for a single-crate project). Task 9's guide defines it for the PoC writer.
- `cargo-scout-audit` is the tool name that preflight checks; `analyzers[0].requires` must match it.

- [ ] **Step 4: Stub every referenced file so the pack lint passes**

```bash
PK=plugins/chainsec/skills/chainsec/chains/soroban
mkdir -p $PK/recon $PK/modules $PK/primers $PK/poc $PK/fuzz $PK/patterns
for f in heuristics.md fp-patterns.md module-triggers.md recon/clustering.md poc/guide.md fuzz/guide.md \
         modules/soroban-auth.md modules/storage-and-ttl.md modules/token-integration.md \
         modules/cross-contract-calls.md modules/upgrades-and-init.md primers/soroban-vs-evm.md; do
  printf '# %s\n\nWritten in a later task of docs/superpowers/plans/2026-11-26-chainsec-soroban-pack.md.\n' "$f" > $PK/$f
done
printf '#!/usr/bin/env bash\necho "soroban extractor: not implemented yet" >&2\nexit 1\n' > $PK/recon/extract.sh
printf '#!/usr/bin/env python3\nimport sys\nsys.exit("scout summary: not implemented yet")\n' > $PK/recon/scout-summary.py
```

(`modules/resource-limits.md` is created in Task 8; it is reached through `module-triggers.md`, not `pack.json`.)

- [ ] **Step 5: Verify**

Run: `bash tests/run.sh`
Expected: lint `0 error(s)`; `test_real_soroban_pack_ignores_plain_rust` and `test_real_soroban_pack_workspace_roots` PASS; everything else still passes.

- [ ] **Step 6: Commit**

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban tests/test_detect_chain.py
git commit -m "Add Soroban pack manifest and chain detection"
```

---

### Task 3: Fixture crate `soroban-basic`

A small token vault. **Planted bug:** `withdraw(from, to, amount)` debits `from` without
`from.require_auth()`, so anyone can move anyone's vault balance to themselves. Everything else is
deliberately correct, and the file holds decoys that the extractor must ignore: a commented-out
storage write, a string literal, an inline `#[cfg(test)]` module, a private helper fn inside
`#[contractimpl]`, and a guard reached through a helper (`require_admin`).

**Files:**
- Create: `tests/fixtures/soroban-basic/Cargo.toml`, `src/lib.rs`, `src/storage.rs`, `src/test.rs`, `Cargo.lock`
- Modify: `.gitignore` (add `target/`), `tests/test_detect_chain.py`

- [ ] **Step 1: Add the fixture detection test**

Append inside `class DetectChainTest`:

```python
    def test_real_soroban_pack_detects_fixture(self):
        r = run_py("detect-chain.py", os.path.join(FIXTURES, "soroban-basic"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["chains"], [{"chain": "soroban", "root": "."}])
```

Run: `cd tests && python3 -m unittest test_detect_chain -v`. Expected: the new test FAILS (fixture missing).

- [ ] **Step 2: Write `tests/fixtures/soroban-basic/Cargo.toml`**

```toml
[package]
name = "chainsec-vault"
version = "0.1.0"
edition = "2021"
publish = false

[lib]
crate-type = ["lib", "cdylib"]
doctest = false

[dependencies]
soroban-sdk = "26.1.0"

[dev-dependencies]
soroban-sdk = { version = "26.1.0", features = ["testutils"] }

[profile.release]
opt-level = "z"
overflow-checks = true
debug = 0
strip = "symbols"
debug-assertions = false
panic = "abort"
codegen-units = 1
lto = true
```

- [ ] **Step 3: Write `src/lib.rs`**

```rust
#![no_std]
//! ChainSec fixture: a token vault with one planted bug.
//! PLANTED BUG: `withdraw` debits `from` without `from.require_auth()`.
use soroban_sdk::{contract, contractimpl, token, Address, BytesN, Env};

mod storage;
use storage::{read_admin, read_balance, read_token, write_balance, DataKey};

#[contract]
pub struct Vault;

fn require_admin(env: &Env) {
    read_admin(env).require_auth();
}

#[contractimpl]
impl Vault {
    pub fn __constructor(env: Env, admin: Address, token: Address) {
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::Token, &token);
    }

    pub fn deposit(env: Env, from: Address, amount: i128) {
        from.require_auth();
        // decoy: env.storage().instance().set(&DataKey::Fake, &1);
        let client = token::Client::new(&env, &read_token(&env));
        client.transfer(&from, &env.current_contract_address(), &amount);
        write_balance(&env, &from, read_balance(&env, &from) + amount);
    }

    pub fn withdraw(env: Env, from: Address, to: Address, amount: i128) {
        let balance = read_balance(&env, &from);
        if amount > balance {
            panic!("insufficient balance");
        }
        write_balance(&env, &from, balance - amount);
        token::Client::new(&env, &read_token(&env)).transfer(&env.current_contract_address(), &to, &amount);
    }

    pub fn balance(env: Env, user: Address) -> i128 {
        read_balance(&env, &user)
    }

    pub fn set_admin(env: Env, new_admin: Address) {
        require_admin(&env);
        env.storage().instance().set(&DataKey::Admin, &new_admin);
    }

    pub fn upgrade(env: Env, wasm_hash: BytesN<32>) {
        require_admin(&env);
        env.deployer().update_current_contract_wasm(wasm_hash);
    }

    #[allow(dead_code)]
    fn bump(env: &Env) {
        env.storage().instance().extend_ttl(100, 1000);
    }
}

#[cfg(test)]
mod inline_tests {
    #[test]
    fn decoy() {
        let _x = "self.storage().instance().set(";
    }
}

#[cfg(test)]
mod test;
```

- [ ] **Step 4: Write `src/storage.rs`**

```rust
use soroban_sdk::{contracttype, Address, Env};

#[derive(Clone)]
#[contracttype]
pub enum DataKey {
    Admin,
    Token,
    Balance(Address),
}

pub fn read_admin(env: &Env) -> Address {
    env.storage().instance().get(&DataKey::Admin).unwrap()
}

pub fn read_token(env: &Env) -> Address {
    env.storage().instance().get(&DataKey::Token).unwrap()
}

pub fn read_balance(env: &Env, id: &Address) -> i128 {
    env.storage().persistent().get(&DataKey::Balance(id.clone())).unwrap_or(0)
}

pub fn write_balance(env: &Env, id: &Address, amount: i128) {
    env.storage().persistent().set(&DataKey::Balance(id.clone()), &amount);
}
```

- [ ] **Step 5: Write `src/test.rs` (the project's own honest test; out of audit scope)**

```rust
#![cfg(test)]
use super::*;
use soroban_sdk::{testutils::Address as _, Env};

#[test]
fn deposit_and_withdraw() {
    let env = Env::default();
    env.mock_all_auths();
    let admin = Address::generate(&env);
    let sac = env.register_stellar_asset_contract_v2(admin.clone());
    let vault = env.register(Vault, (admin.clone(), sac.address()));
    let client = VaultClient::new(&env, &vault);
    let user = Address::generate(&env);
    token::StellarAssetClient::new(&env, &sac.address()).mint(&user, &100);
    client.deposit(&user, &60);
    assert_eq!(client.balance(&user), 60);
    client.withdraw(&user, &user, &10);
    assert_eq!(client.balance(&user), 50);
}
```

- [ ] **Step 6: Build, test, pin the lockfile**

```bash
echo 'target/' >> .gitignore
cd tests/fixtures/soroban-basic
CARGO_TARGET_DIR=/tmp/chainsec-soroban-target cargo test 2>&1 | tail -5
```

Expected: `test inline_tests::decoy ... ok`, `test test::deposit_and_withdraw ... ok`,
`test result: ok. 2 passed`. A `Cargo.lock` now exists: keep it (it pins soroban-sdk for
reproducible PoC/fuzz runs, as `Scarb.lock` does for the Cairo fixture). Confirm the project folder
has no `target/` (the target dir was external).

- [ ] **Step 7: Verify and commit**

Run: `bash tests/run.sh` — expected all pass, including `test_real_soroban_pack_detects_fixture`.

```bash
git add .gitignore tests/fixtures/soroban-basic tests/test_detect_chain.py
git commit -m "Add soroban-basic fixture with a planted missing require_auth"
```

---

### Task 4: Facts extractor

**Files:**
- Replace stub: `PK/recon/extract.sh`, Create: `PK/recon/extract.py`
- Test: `tests/test_extract_soroban.py`

**Interfaces:**
- Consumes: `pack.json` `scope` (Task 2); `_common.load_json`, `_common.scope_files`, `_common.write_json` from `scripts/_common.py`; `engine/facts.schema.json`.
- Produces: `facts.json` per the schema, plus top-level `compile` (`ok|failed|unknown`) and `sdk` (string or `null`).
  - `entry_points[].visibility` ∈ `constructor|check_auth|external`; `mutability` ∈ `mutating|view`.
  - `entry_points[].guards`: `require_auth(<recv>)`, `require_auth_for_args(<recv>)`, `<guard> via <helper>`, or an auth-macro name (`only_owner`, `only_admin`, `only_role`, `only_any_role`, `has_role`, `has_any_role`). A receiver that is a call is written `name()`.
  - `auth_sites[].kind` ∈ `require_auth|require_auth_for_args|authorize_as_current_contract|auth_macro|check_auth`.
  - `storage_writes[].target` = `<instance|persistent|temporary>:<key head>`.
  - `external_calls[].kind` ∈ `client|invoke_contract|try_invoke_contract|deployer|upgrade`.
  - counters per file: `loc`, `external_calls`, `state_writers`, `upgrades`, `token_transfers`, `unchecked_math`, `unguarded_mutators`.

- [ ] **Step 1: Write the failing tests** — `tests/test_extract_soroban.py`:

```python
import os
import shutil
import sys
import tempfile
import unittest

from helpers import CORE, FIXTURES, SCRIPTS, load, make_tree, run

sys.path.insert(0, SCRIPTS)
from _schema import validate  # noqa: E402

EXTRACT = os.path.join(CORE, "chains", "soroban", "recon", "extract.sh")
PROJECT = os.path.join(FIXTURES, "soroban-basic")
PACK = os.path.join(CORE, "chains", "soroban", "pack.json")
SLOW = os.environ.get("CHAINSEC_SLOW_TESTS") == "1"


def extract(root=PROJECT, **env):
    out = os.path.join(tempfile.mkdtemp(), "facts.json")
    r = run(["bash", EXTRACT, root, out], env=dict(os.environ, CHAINSEC_PACK=PACK, **env))
    return r, (load(out) if r.returncode == 0 else None)


def crate(lib, extra=None, toml='[package]\nname = "x"\n[dependencies]\nsoroban-sdk = "22.0.1"\n'):
    files = {"Cargo.toml": toml, "src/lib.rs": lib}
    files.update(extra or {})
    return make_tree(files)


class ExtractSorobanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r, cls.facts = extract(CHAINSEC_NO_COMPILE="1")
        assert r.returncode == 0, r.stderr

    def test_schema_and_header(self):
        self.assertEqual(validate(self.facts, load(os.path.join(CORE, "engine", "facts.schema.json"))), [])
        self.assertEqual((self.facts["chain"], self.facts["mode"], self.facts["compile"]),
                         ("soroban", "regex", "unknown"))
        self.assertTrue(self.facts["sdk"].startswith("26."), self.facts["sdk"])

    def test_scope_excludes_tests(self):
        self.assertEqual(sorted(self.facts["counters"]), ["src/lib.rs", "src/storage.rs"])

    def test_units(self):
        self.assertEqual([(u["name"], u["kind"], u["parents"]) for u in self.facts["units"]],
                         [("Vault", "contract", [])])

    def test_entry_points(self):
        eps = {e["name"]: e for e in self.facts["entry_points"]}
        self.assertEqual(set(eps), {"__constructor", "deposit", "withdraw", "balance", "set_admin", "upgrade"})
        self.assertEqual(eps["__constructor"]["visibility"], "constructor")
        self.assertEqual(eps["balance"]["mutability"], "view")
        self.assertEqual(eps["deposit"]["mutability"], "mutating")
        self.assertEqual(eps["deposit"]["guards"], ["require_auth(from)"])
        self.assertEqual(eps["withdraw"]["guards"], [])
        self.assertEqual(eps["set_admin"]["guards"], ["require_auth(read_admin()) via require_admin"])
        self.assertEqual(eps["upgrade"]["guards"], ["require_auth(read_admin()) via require_admin"])

    def test_storage_writes_ignore_comments_and_test_mods(self):
        writes = sorted((w["unit"], w["function"], w["target"]) for w in self.facts["storage_writes"])
        self.assertEqual(writes, [("Vault", "__constructor", "instance:DataKey::Admin"),
                                  ("Vault", "__constructor", "instance:DataKey::Token"),
                                  ("Vault", "set_admin", "instance:DataKey::Admin"),
                                  ("Vault", "write_balance", "persistent:DataKey::Balance")])

    def test_calls_transfers_auth(self):
        calls = sorted((c["function"], c["kind"]) for c in self.facts["external_calls"])
        self.assertEqual(calls, [("deposit", "client"), ("upgrade", "upgrade"), ("withdraw", "client")])
        self.assertEqual(sorted(v["function"] for v in self.facts["value_transfers"]), ["deposit", "withdraw"])
        self.assertEqual(sorted(a["kind"] for a in self.facts["auth_sites"]), ["require_auth", "require_auth"])

    def test_counters(self):
        c = self.facts["counters"]["src/lib.rs"]
        self.assertEqual((c["external_calls"], c["state_writers"], c["upgrades"], c["token_transfers"],
                          c["unguarded_mutators"]), (3, 4, 1, 2, 1))


class ExtractSorobanEdgeTest(unittest.TestCase):
    def test_traits_macros_and_literals(self):
        root = crate(
            "#![no_std]\n"
            "/* env.storage().instance().set(&K::A, &1); */\n"
            "#[contract]\npub struct Tok;\n"
            "#[contractimpl(contracttrait)]\nimpl FungibleToken for Tok {\n    type ContractType = Base;\n}\n"
            "#[contractimpl]\nimpl Ownable for Tok {}\n"
            "#[contractclient(name = \"OracleClient\")]\npub trait Oracle { fn price(env: Env) -> i128; }\n"
            "#[contractimpl]\nimpl Tok {\n"
            "    #[only_owner]\n"
            "    pub fn mint_to<'a>(e: &'a Env, to: Address, amt: i128) {\n"
            "        let _c = '\"';\n"
            "        let _r = r#\"env.storage().persistent().set(&K::B, &2)\"#;\n"
            "        let _q = '\\'';\n"
            "        e.storage().persistent().set(&K::Bal(to), &(amt as u64));\n"
            "    }\n}\n"
            "#[cfg(not(test))]\nmod real { pub fn f(e: &Env) { e.storage().temporary().set(&1u32, &2u32); } }\n")
        r, facts = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        units = {u["name"]: u for u in facts["units"]}
        self.assertEqual(units["Tok"]["parents"], ["FungibleToken", "Ownable"])
        self.assertEqual(units["Oracle"]["kind"], "interface")
        self.assertEqual([(e["name"], e["guards"]) for e in facts["entry_points"]], [("mint_to", ["only_owner"])])
        self.assertEqual(sorted((w["function"], w["target"]) for w in facts["storage_writes"]),
                         [("f", "temporary:1u32"), ("mint_to", "persistent:K::Bal")])
        self.assertEqual([a["kind"] for a in facts["auth_sites"]], ["auth_macro"])
        self.assertEqual(facts["counters"]["src/lib.rs"]["unchecked_math"], 1)
        self.assertEqual(facts["sdk"], "22.0.1")

    def test_workspace_scope_and_unit_attribution(self):
        root = make_tree({
            "Cargo.toml": '[workspace]\nmembers = ["contracts/*"]\n[workspace.dependencies]\nsoroban-sdk = "23.0.2"\n',
            "contracts/a/Cargo.toml": '[package]\nname = "a"\n[dependencies]\nsoroban-sdk = { workspace = true }\n',
            "contracts/a/src/lib.rs": "#[contract]\npub struct A;\n#[contract]\npub struct B;\n"
                                      "#[contractimpl]\nimpl A { pub fn go(e: Env) { helper(&e); } }\n",
            "contracts/a/src/helpers.rs": "pub fn helper(e: &Env) { e.storage().instance().set(&K::X, &1); }\n",
            "contracts/a/src/test.rs": "fn t(e: &Env) { e.storage().instance().set(&K::T, &1); }\n",
            "contracts/a/tests/it.rs": "fn t(e: &Env) { e.storage().instance().set(&K::T, &1); }\n",
        })
        r, facts = extract(root, CHAINSEC_NO_COMPILE="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(facts["counters"]), ["contracts/a/src/helpers.rs", "contracts/a/src/lib.rs"])
        self.assertEqual([(w["unit"], w["function"]) for w in facts["storage_writes"]], [("helpers", "helper")])
        self.assertEqual([(e["name"], e["mutability"]) for e in facts["entry_points"]], [("go", "mutating")])
        self.assertEqual(facts["sdk"], "23.0.2")

    @unittest.skipUnless(shutil.which("cargo") and SLOW, "needs cargo and CHAINSEC_SLOW_TESTS=1")
    def test_compile_status_ok_without_touching_project(self):
        before = sorted(os.listdir(PROJECT))
        r, facts = extract()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(facts["compile"], "ok")
        self.assertEqual(sorted(os.listdir(PROJECT)), before)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd tests && python3 -m unittest test_extract_soroban -v`
Expected: errors — `setUpClass` fails with "soroban extractor: not implemented yet".

- [ ] **Step 3: Write `PK/recon/extract.sh`** (`chmod +x` it)

```bash
#!/usr/bin/env bash
# Soroban facts extractor. Usage: extract.sh <project-root> <facts.json>
# Runs `cargo check` with its target dir next to facts.json (the project's own target/ is not
# touched, and a Cargo.lock the check creates is removed again) to record compile status, then
# parses source. Env: CHAINSEC_NO_COMPILE=1 skips the check; CHAINSEC_PACK overrides the manifest.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${1:-.}" 2>/dev/null && pwd)" || { echo "no such root: ${1:-.}" >&2; exit 2; }
OUT="${2:-$ROOT/.audit/soroban/facts.json}"
PACK="${CHAINSEC_PACK:-$HERE/../pack.json}"
mkdir -p "$(dirname "$OUT")"
OUTDIR="$(cd "$(dirname "$OUT")" && pwd)"
STATUS=unknown
if [ "${CHAINSEC_NO_COMPILE:-0}" != "1" ] && command -v cargo >/dev/null 2>&1 && [ -f "$ROOT/Cargo.toml" ]; then
  WS="$(cd "$ROOT" && cargo locate-project --workspace --message-format plain 2>/dev/null)"
  LOCK="$(dirname "${WS:-$ROOT/Cargo.toml}")/Cargo.lock"
  HAD_LOCK=0
  if [ -f "$LOCK" ]; then HAD_LOCK=1; fi
  if (cd "$ROOT" && CARGO_TARGET_DIR="$OUTDIR/target" cargo check --quiet >/dev/null 2>&1); then
    STATUS=ok
  else
    STATUS=failed
    echo "cargo check failed; facts come from source only" >&2
  fi
  if [ "$HAD_LOCK" = 0 ]; then rm -f "$LOCK"; fi
fi
python3 "$HERE/extract.py" --root "$ROOT" --pack "$PACK" --out "$OUT" --compile "$STATUS"
```

- [ ] **Step 4: Write `PK/recon/extract.py`** (`chmod +x` it)

```python
#!/usr/bin/env python3
"""Soroban (Stellar) facts extractor for ChainSec.

Usage:
  extract.py --root DIR --pack PACK_JSON --out FACTS_JSON [--compile ok|failed|unknown]

Parses comment- and string-stripped Rust source of soroban-sdk contracts (mode "regex");
`--compile` records the result of the optional `cargo check` run by extract.sh.
Output conforms to engine/facts.schema.json, plus top-level "compile" and "sdk" fields.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
from _common import load_json, scope_files, write_json  # noqa: E402

TOKEN_CALLS = ("transfer_from", "transfer", "burn_from", "burn", "mint", "clawback")
AUTH_MACROS = ("only_owner", "only_admin", "only_role", "only_any_role", "has_role", "has_any_role")

_STRIP = re.compile(
    r'//[^\n]*|/\*.*?\*/'
    r'|(?<![\w])b?r(#*)".*?"\1'
    r'|(?<![\w])b?"(?:\\.|[^"\\])*"'
    r"|(?<![\w])b?'(?:\\(?:u\{[0-9a-fA-F]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'", re.S)
ATTR = r'#\[[^\]]*\]'
VIS = r'(?:pub(?:\([^)]*\))?\s+)?'
CFG_RE = re.compile(r'#\[cfg\(([^\]]*)\)\]\s*(?:' + ATTR + r'\s*)*' + VIS + r'mod\s+\w+\s*\{')
CONTRACT_RE = re.compile(r'#\[contract\]\s*(?:' + ATTR + r'\s*)*' + VIS + r'struct\s+([A-Za-z_]\w*)')
IMPL_RE = re.compile(r'#\[contractimpl(?:\s*\(([^\]]*)\))?\]\s*(?:' + ATTR + r'\s*)*'
                     r'impl(?:\s*<[^>{]*>)?\s+(?:([A-Za-z_][\w:]*)(?:<[^>{]*>)?\s+for\s+)?'
                     r'([A-Za-z_]\w*)[^{;]*\{')
IFACE_RE = re.compile(r'#\[(?:contractclient|contracttrait)\b[^\]]*\]\s*(?:' + ATTR + r'\s*)*' + VIS +
                      r'trait\s+([A-Za-z_]\w*)[^{;]*\{')
FN_RE = re.compile(r'((?:' + ATTR + r'\s*)*)(pub(?:\([^)]*\))?\s+)?(?:(?:const|unsafe|async|extern)\s+)*'
                   r'fn\s+([A-Za-z_]\w*)\s*(?:<[^>{]*>)?\s*\(')
WRITE_RE = re.compile(r'\.storage\(\)\s*\.\s*(instance|persistent|temporary)\(\)\s*\.\s*'
                      r'(set|remove|update|try_update)\s*\(\s*&?\s*(?:mut\s+)?([\w:]+)')
CLIENT_RE = re.compile(r'\b(?:[A-Za-z_]\w*::)*[A-Za-z_]*Client\s*::\s*new\s*\(')
EXT_RE = re.compile(r'\.(try_invoke_contract|invoke_contract)\b|\.(deployer)\s*\(\s*\)'
                    r'(?!\s*\.\s*update_current_contract_wasm)|\b(update_current_contract_wasm)\s*\(')
TOKEN_RE = re.compile(r'\.(' + "|".join(TOKEN_CALLS) + r')\s*\(')
AUTH_RE = re.compile(r'([A-Za-z_][\w.]*)(\s*\([^()]*\))?\s*\.\s*(require_auth_for_args|require_auth)\s*\(')
AS_CONTRACT_RE = re.compile(r'\.authorize_as_current_contract\s*\(')
UNCHECKED_RE = re.compile(r'\.(?:wrapping|overflowing|unchecked)_\w+\s*\(|\bas\s+[iu](?:8|16|32|64|128)\b')
CALL_RE = re.compile(r'(?<![\w.:])(?:[A-Za-z_]\w*::)*([a-z_]\w*)\s*\(')
SDK_LOCK_RE = re.compile(r'name\s*=\s*"soroban-sdk"\s*\nversion\s*=\s*"([^"]+)"')
SDK_TOML_RE = re.compile(r'soroban-sdk\s*=\s*(?:"([^"]+)"|\{[^}\n]*?version\s*=\s*"([^"]+)")')


def strip(src):
    """Blank comments, strings and char literals, keeping offsets and newlines."""
    return _STRIP.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), src)


def blank(text, a, b):
    return text[:a] + re.sub(r'[^\n]', ' ', text[a:b + 1]) + text[b + 1:]


def block_end(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def blank_test_mods(text):
    """Blank `#[cfg(test)] mod x { ... }` (and cfg(any(test, ..))) blocks; keep cfg(not(test))."""
    while True:
        m = next((m for m in CFG_RE.finditer(text)
                  if re.search(r'\btest\b', m.group(1)) and "not(" not in m.group(1)), None)
        if not m:
            return text
        text = blank(text, m.start(), block_end(text, m.end() - 1))


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def attrs_of(attr_text):
    return [a.strip() for a in re.findall(r'#\[([^\]]*)\]', attr_text or "")]


def functions(text, start, end):
    """Yield (name, attrs, is_pub, name_pos, body_open, body_close) for fns with bodies."""
    pos = start
    while True:
        m = FN_RE.search(text, pos, end)
        if not m:
            return
        brace = text.find("{", m.end(), end)
        semi = text.find(";", m.end(), end)
        if brace == -1 or (semi != -1 and semi < brace):
            pos = m.end()
            continue
        close = block_end(text, brace)
        yield m.group(3), attrs_of(m.group(1)), bool(m.group(2)), m.start(3), brace, close
        pos = close + 1


def analyze(text, b0, b1):
    body = text[b0:b1]
    ext = []
    for m in CLIENT_RE.finditer(body):
        ext.append(("client", b0 + m.start()))
    for m in EXT_RE.finditer(body):
        ext.append((m.group(1) or m.group(2) or "upgrade", b0 + m.start()))
    auth = [(m.group(3), m.group(1) + ("()" if m.group(2) else ""), b0 + m.start())
            for m in AUTH_RE.finditer(body)]
    return {"writes": [(f"{m.group(1)}:{m.group(3)}", b0 + m.start()) for m in WRITE_RE.finditer(body)],
            "ext": ext, "auth": auth,
            "as_contract": [b0 + m.start() for m in AS_CONTRACT_RE.finditer(body)],
            "tokens": [b0 + m.start() for m in TOKEN_RE.finditer(body)],
            "callees": {m.group(1) for m in CALL_RE.finditer(body)}}


def crate_of(root, rel):
    d = os.path.dirname(rel)
    while True:
        if os.path.isfile(os.path.join(root, d, "Cargo.toml")):
            return d
        if not d:
            return ""
        d = os.path.dirname(d)


def sdk_version(root):
    lock = os.path.join(root, "Cargo.lock")
    if os.path.isfile(lock):
        m = SDK_LOCK_RE.search(open(lock, encoding="utf-8", errors="replace").read())
        if m:
            return m.group(1)
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in {"target", ".git", ".audit", "node_modules"})
        if "Cargo.toml" in files:
            m = SDK_TOML_RE.search(open(os.path.join(dirpath, "Cargo.toml"), encoding="utf-8",
                                        errors="replace").read())
            if m:
                return (m.group(1) or m.group(2)).lstrip("=^~ ")
    return None


def parse_file(rel, src):
    text = blank_test_mods(strip(src))
    contracts = [(m.group(1), line_of(text, m.start(1))) for m in CONTRACT_RE.finditer(text)]
    impls = []
    for m in IMPL_RE.finditer(text):
        close = block_end(text, m.end() - 1)
        impls.append({"args": m.group(1) or "", "trait": m.group(2), "type": m.group(3),
                      "open": m.end() - 1, "close": close})
    ifaces = []
    for m in IFACE_RE.finditer(text):
        close = block_end(text, m.end() - 1)
        ifaces.append((m.group(1), line_of(text, m.start(1)), text.count("\n", m.end() - 1, close) + 1))
    fns = []
    for name, attrs, is_pub, npos, b0, b1 in functions(text, 0, len(text)):
        impl = next((i for i in impls if i["open"] < npos < i["close"]), None)
        entry = impl is not None and (impl["trait"] is not None or is_pub)
        fns.append({"name": name, "attrs": attrs, "pos": npos, "impl": impl, "entry": entry,
                    **analyze(text, b0, b1)})
    return {"rel": rel, "src": src, "text": text, "contracts": contracts, "impls": impls,
            "ifaces": ifaces, "fns": fns}


def resolve(parsed):
    """Transitive effects and auth guards through helper functions defined in scope."""
    by_name = {}
    for p in parsed:
        for f in p["fns"]:
            by_name.setdefault(f["name"], []).append(f)
    for f in (f for p in parsed for f in p["fns"]):
        f["effects"] = bool(f["writes"] or f["ext"] or f["tokens"])
        f["writes_t"] = bool(f["writes"])
        f["guards_t"] = {f"{k}({r})" for k, r, _ in f["auth"]}
    changed = True
    while changed:
        changed = False
        for f in (f for p in parsed for f in p["fns"]):
            for callee in f["callees"] - {f["name"]}:
                for g in by_name.get(callee, []):
                    if g["effects"] and not f["effects"]:
                        f["effects"] = changed = True
                    if g["writes_t"] and not f["writes_t"]:
                        f["writes_t"] = changed = True
                    for guard in g["guards_t"]:
                        via = guard if " via " in guard else f"{guard} via {callee}"
                        if guard not in f["guards_t"] and via not in f["guards_t"]:
                            f["guards_t"].add(via)
                            changed = True


def build_facts(root, rels, facts):
    parsed = []
    for rel in rels:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            parsed.append(parse_file(rel, fh.read()))
    resolve(parsed)
    crate_contracts = {}
    for p in parsed:
        for name, _ in p["contracts"]:
            crate_contracts.setdefault(crate_of(root, p["rel"]), []).append(name)
    units = {}
    for p in parsed:
        for name, line in p["contracts"]:
            units[name] = {"name": name, "kind": "contract", "file": p["rel"], "line": line, "loc": 1,
                           "parents": []}
    for p in parsed:
        for i in p["impls"]:
            u = units.get(i["type"])
            if u is None:
                continue
            u["loc"] += p["text"].count("\n", i["open"], i["close"]) + 1
            if i["trait"]:
                parent = i["trait"].split("::")[-1]
                if parent not in u["parents"]:
                    u["parents"].append(parent)
        for name, line, loc in p["ifaces"]:
            units.setdefault(name, {"name": name, "kind": "interface", "file": p["rel"], "line": line,
                                    "loc": loc, "parents": []})
    facts["units"] = sorted(units.values(), key=lambda u: (u["file"], u["line"]))
    for p in parsed:
        rel, text = p["rel"], p["text"]
        owners = crate_contracts.get(crate_of(root, rel), [])
        default_unit = owners[0] if len(owners) == 1 else os.path.splitext(os.path.basename(rel))[0]
        c = {"loc": p["src"].count("\n"), "external_calls": 0, "state_writers": 0, "upgrades": 0,
             "token_transfers": 0, "unchecked_math": len(UNCHECKED_RE.findall(text)), "unguarded_mutators": 0}
        for f in p["fns"]:
            unit, fname = (f["impl"]["type"] if f["impl"] else default_unit), f["name"]
            for target, pos in f["writes"]:
                facts["storage_writes"].append({"unit": unit, "function": fname, "file": rel,
                                                "line": line_of(text, pos), "target": target})
            for kind, pos in f["ext"]:
                facts["external_calls"].append({"unit": unit, "function": fname, "file": rel,
                                                "line": line_of(text, pos), "kind": kind})
                c["external_calls"] += 1
                c["upgrades"] += kind == "upgrade"
            for pos in f["tokens"]:
                facts["value_transfers"].append({"unit": unit, "function": fname, "file": rel,
                                                 "line": line_of(text, pos), "asset": "token"})
                c["token_transfers"] += 1
            for kind, _, pos in f["auth"]:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, pos), "kind": kind})
            for pos in f["as_contract"]:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, pos),
                                            "kind": "authorize_as_current_contract"})
            macros = [a.split("(")[0].strip() for a in f["attrs"] if a.split("(")[0].strip() in AUTH_MACROS]
            for _ in macros:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, f["pos"]),
                                            "kind": "auth_macro"})
            if fname == "__check_auth" and f["entry"]:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, f["pos"]),
                                            "kind": "check_auth"})
            if not f["entry"]:
                continue
            vis = {"__constructor": "constructor", "__check_auth": "check_auth"}.get(fname, "external")
            guards = macros + sorted(f["guards_t"])
            mutating = f["effects"]
            facts["entry_points"].append({"unit": unit, "name": fname, "file": rel,
                                          "line": line_of(text, f["pos"]), "visibility": vis,
                                          "mutability": "mutating" if mutating else "view",
                                          "guards": guards})
            c["state_writers"] += f["writes_t"]
            c["unguarded_mutators"] += mutating and not guards and vis == "external"
        facts["counters"][rel] = c


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract Soroban facts")
    ap.add_argument("--root", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--compile", default="unknown", choices=("ok", "failed", "unknown"))
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    pack = load_json(args.pack)
    facts = {"chain": "soroban", "mode": "regex", "root": root, "compile": args.compile,
             "sdk": sdk_version(root), "units": [], "entry_points": [], "auth_sites": [],
             "storage_writes": [], "external_calls": [], "value_transfers": [], "counters": {}}
    build_facts(root, scope_files(root, pack["scope"]), facts)
    write_json(args.out, facts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

How it works, for reviewers:
- `strip` blanks comments, strings, raw strings (`r#"…"#`) and char literals but not lifetimes (`'a`), keeping offsets so line numbers stay right. `blank_test_mods` then blanks `#[cfg(test)]` / `#[cfg(any(test, …))]` modules, keeping `#[cfg(not(test))]`.
- Entry points are `pub fn` in inherent `#[contractimpl]` impls and every fn in trait `#[contractimpl]` impls. Default methods of OpenZeppelin `#[contractimpl(contracttrait)]` impls are generated by the macro and invisible here; their trait names appear in the unit's `parents` so recon can list them (Task 8 heuristics say so).
- `resolve` propagates effects (storage writes, external calls, token calls) and `require_auth` guards through helper functions by name, across files, to a fixed point. Name collisions are merged conservatively.
- Free functions are attributed to the crate's only `#[contract]`, or to their file stem when a crate has several.

- [ ] **Step 5: Run the tests**

Run: `cd tests && python3 -m unittest test_extract_soroban -v`
Expected: 9 tests OK, 1 skipped (`test_compile_status_ok_without_touching_project`).
Then: `CHAINSEC_SLOW_TESTS=1 python3 -m unittest test_extract_soroban -v` → 10 OK (first run ≈ 1 min: `cargo check` builds soroban-sdk).

- [ ] **Step 6: Verify and commit**

Run: `bash tests/run.sh` — all pass.

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban/recon tests/test_extract_soroban.py
git commit -m "Soroban facts extractor: entry points, transitive auth guards, storage, calls"
```

---

### Task 5: Scout analyzer summary

**Files:**
- Replace stub: `PK/recon/scout-summary.py`
- Test: `tests/test_scout_summary.py`

**Interfaces:**
- Consumes: Scout SARIF 2.1.0 at `A/analyzers/scout.json` (written by the recon phase with the command that Task 8 records in `heuristics.md` "Recon additions" → "Analyzer command").
- Produces: `A/analyzers/scout.md`; exit 1 on missing or non-JSON input.

- [ ] **Step 1: Write the failing test** — `tests/test_scout_summary.py`:

```python
import json
import os
import sys
import tempfile
import unittest

from helpers import CORE, run

SCRIPT = os.path.join(CORE, "chains", "soroban", "recon", "scout-summary.py")


def sarif(*results):
    return {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "scout"}}, "results": list(results)}]}


def result(rule, uri, line, text, level="warning"):
    return {"ruleId": rule, "level": level, "message": {"text": text},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": line}}}]}


def summarize(content):
    d = tempfile.mkdtemp()
    src, out = os.path.join(d, "scout.json"), os.path.join(d, "scout.md")
    with open(src, "w") as f:
        f.write(content if isinstance(content, str) else json.dumps(content))
    r = run([sys.executable, SCRIPT, src, out])
    return r, (open(out).read() if r.returncode == 0 else "")


class ScoutSummaryTest(unittest.TestCase):
    def test_table(self):
        r, md = summarize(sarif(result("unsafe-unwrap", "src/lib.rs", 12, "Unsafe usage of `unwrap`\nmore"),
                                result("unprotected-update-current-contract-wasm", "src/lib.rs", 40,
                                       "a | b", level="error")))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Results: 2 from 2 detectors", md)
        self.assertIn("| unsafe-unwrap | warning | src/lib.rs:12 | Unsafe usage of `unwrap` |", md)
        self.assertIn("a \\| b", md)
        self.assertNotIn("more", md)

    def test_empty_and_bad_input(self):
        r, md = summarize(sarif())
        self.assertIn("Scout reported nothing.", md)
        r, _ = summarize("not json")
        self.assertEqual(r.returncode, 1)

    def test_missing_input(self):
        r = run([sys.executable, SCRIPT, "/nonexistent/scout.json", os.path.join(tempfile.mkdtemp(), "x.md")])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
```

Run: `cd tests && python3 -m unittest test_scout_summary -v` → FAIL (stub exits with "not implemented").

- [ ] **Step 2: Write `PK/recon/scout-summary.py`**

```python
#!/usr/bin/env python3
# Usage: scout-summary.py [scout-output] [out.md]
# Called during recon when cargo-scout-audit is installed. The input is Scout's SARIF 2.1.0 output
# (exact command: heuristics.md "Recon additions"). Rows are capped; the full file stays on disk.
import json
import os
import sys

MAX_ROWS = 200


def results(data):
    for run in data.get("runs") or []:
        for r in run.get("results") or []:
            phys = ((r.get("locations") or [{}])[0] or {}).get("physicalLocation") or {}
            uri = (phys.get("artifactLocation") or {}).get("uri", "?")
            line = (phys.get("region") or {}).get("startLine", "?")
            text = ((r.get("message") or {}).get("text") or "").strip().splitlines()
            msg = (text[0] if text else "").replace("|", "\\|")
            yield r.get("ruleId") or "?", r.get("level") or "warning", f"{uri}:{line}", msg


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    src = argv[0] if argv else ".audit/soroban/analyzers/scout.json"
    out = argv[1] if len(argv) > 1 else ".audit/soroban/analyzers/scout.md"
    if not os.path.isfile(src):
        print(f"No Scout results found at {src}", file=sys.stderr)
        return 1
    try:
        with open(src, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Scout output at {src} is not SARIF JSON: {e}", file=sys.stderr)
        return 1
    rows = sorted(set(results(data)))
    rules = sorted({r[0] for r in rows})
    md = ["# Scout summary", "",
          f"Results: {len(rows)} from {len(rules)} detectors. Signal only: every item still needs a "
          "ChainSec trace and the kill gates. A detector ID upper-cased is its `patterns/` class.", ""]
    if not rows:
        md.append("Scout reported nothing.")
    else:
        md += ["| Detector | Level | Location | Message |", "|---|---|---|---|"]
        md += [f"| {r} | {lvl} | {loc} | {msg} |" for r, lvl, loc, msg in rows[:MAX_ROWS]]
        if len(rows) > MAX_ROWS:
            md.append(f"\n(truncated: {len(rows) - MAX_ROWS} more results in {src})")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Confirm the real Scout flags (only if `cargo scout-audit` is installed)**

Run `cargo scout-audit --help` and note the flags for SARIF output and output path. Task 8 writes
that exact command into `heuristics.md` "Recon additions". If Scout is not installed, write the
command from Scout's README (`SCOUT/README.md`, "Usage") and mark it "unverified" there.

- [ ] **Step 4: Verify and commit**

Run: `bash tests/run.sh` — `test_scout_summary` 3 OK, all others pass.

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban/recon/scout-summary.py tests/test_scout_summary.py
git commit -m "Soroban: Scout SARIF summary for recon"
```

---

### Task 6: Port Scout's 23 vulnerability classes

**Files:**
- Create: `PK/patterns/README.md`, `PK/patterns/<ID>.md` × 23, `PK/ATTRIBUTION.md`
- Modify: `tests/test_port_coverage.py`

**Interfaces:**
- Produces: pattern IDs (file stems) used by `heuristics.md` (Task 8), `scout-summary.py` (detector ID upper-cased = pattern ID) and the snippet suite's `class_id` (Task 11).

ID = Scout's `test-cases/<name>` folder upper-cased. Sources per ID (`D/` = `SCOUT/docs/docs/detectors/`, `V/` = `SCOUT/docs/docs/vulnerabilities/`, `T/` = `SCOUT/test-cases/`, `S/` = `SCOUT/detectors/`):

| Pattern ID | Docs | Lens | Tier |
|---|---|---|---|
| DIVIDE-BEFORE-MULTIPLY | D/1, V/1 | B | security |
| UNSAFE-UNWRAP | D/2, V/2 | D | quality |
| UNSAFE-EXPECT | D/3, V/3 | D | quality |
| OVERFLOW-CHECK | D/4, V/4 | B | security |
| INSUFFICIENTLY-RANDOM-VALUES | D/5, V/5 | B | security |
| UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM | D/6, V/6 | A | security |
| AVOID-CORE-MEM-FORGET | D/7, V/7 | D | quality |
| SET-CONTRACT-STORAGE | D/8, V/8 | A | security |
| AVOID-PANIC-ERROR | D/9, V/9 | D | quality |
| AVOID-UNSAFE-BLOCK | D/10, V/10 | D | quality |
| DOS-UNBOUNDED-OPERATION | D/11, V/11 | D | security |
| SOROBAN-VERSION | D/12, V/12 | D | quality |
| UNUSED-RETURN-ENUM | D/13, V/13 | C | security |
| ITERATORS-OVER-INDEXING | D/14, V/14 | D | quality |
| ASSERT-VIOLATION | D/15, V/15 | D | quality |
| UNPROTECTED-MAPPING-OPERATION | D/16, V/16 | A | security |
| DOS-UNEXPECTED-REVERT-WITH-VECTOR | D/17, V/17 | D | security |
| UNRESTRICTED-TRANSFER-FROM | D/18, V/18 | A + B | security |
| UNSAFE-MAP-GET | D/19, V/19 | D | security |
| ZERO-ADDRESS | D/20 (`20-zero-or-test-address.md`) | A | security |
| INCORRECT-EXPONENTIATION | D/21, V/21 | B | security |
| INTEGER-OVERFLOW-OR-UNDERFLOW | no doc: `S/integer-overflow-or-underflow/src/lib.rs` lint text + `T/` | B | security |
| VEC-COULD-BE-MAPPING | no doc: `S/vec-could-be-mapping/src/lib.rs` lint text + `T/` | D | quality |

"Tier" is the default report treatment: **quality** classes are QA/Low unless an attacker can force
the panic or cost onto another user's critical path; Task 8's `fp-patterns.md` encodes this.

- [ ] **Step 1: Write the failing coverage test**

In `tests/test_port_coverage.py`, add after the Cairo constants:

```python
# CoinFabrik scout-soroban (MIT) at commit 53157fd and stellar/stellar-dev-skill (Apache-2.0) at
# commit 9098e8b, the sources the Soroban pack was ported from. Override with SCOUT_SOROBAN_SRC /
# STELLAR_DEV_SKILL_SRC; the tests skip when a source is not on this machine.
SCOUT_SRC = os.environ.get("SCOUT_SOROBAN_SRC", os.path.expanduser("~/src/scout-soroban"))
STELLAR_SRC = os.environ.get("STELLAR_DEV_SKILL_SRC", os.path.expanduser("~/src/stellar-dev-skill"))
SOROBAN_PATTERNS = os.path.join(CORE, "chains", "soroban", "patterns")
# stellar-dev-skill security.md "### <n>." classes -> pattern IDs. Class 5 (integer overflow) is
# covered by Scout's INTEGER-OVERFLOW-OR-UNDERFLOW and OVERFLOW-CHECK.
STELLAR_CLASSES = {1: "MISSING-AUTH", 2: "AUTH-REPLAY-MIDDLEWARE", 3: "REINITIALIZATION",
                   4: "ARBITRARY-CONTRACT-CALL", 5: "INTEGER-OVERFLOW-OR-UNDERFLOW",
                   6: "STORAGE-KEY-COLLISION", 7: "CHECK-THEN-ACT", 8: "TTL-ARCHIVAL",
                   9: "UNTRUSTED-RETURN-VALUE", 10: "RESOURCE-EXHAUSTION",
                   11: "CUSTOM-ACCOUNT-CHECK-AUTH", 12: "MALFORMED-BYTES"}
```

and inside `class PortCoverageTest`:

```python
    def test_every_scout_class_has_a_pattern(self):
        cases = os.path.join(SCOUT_SRC, "test-cases")
        if not os.path.isdir(cases):
            self.skipTest(f"scout-soroban source not found at {SCOUT_SRC}")
        ids = sorted(d.upper() for d in os.listdir(cases) if os.path.isdir(os.path.join(cases, d)))
        self.assertEqual(len(ids), 23)
        missing = [i for i in ids if not os.path.isfile(os.path.join(SOROBAN_PATTERNS, i + ".md"))]
        self.assertEqual(missing, [], f"{len(missing)} Scout classes have no patterns/<ID>.md")
```

Run: `cd tests && SCOUT_SOROBAN_SRC=~/src/scout-soroban python3 -m unittest test_port_coverage -v`
Expected: `test_every_scout_class_has_a_pattern` FAILS (23 patterns missing). The Stellar test is added in Task 7.

- [ ] **Step 2: Write one pattern per ID, in this exact layout** (same section names as the Cairo patterns, because the engine's verify phase reads "False-positive caveats" and "Minimum tests"). Worked example, `PK/patterns/UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM.md`:

````markdown
# UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM

> **Detector class**: Scout `unprotected-update-current-contract-wasm`
> **Inject into**: Lens A (Access/State)
> **Category**: Upgrades
> **Tier**: security
> **Related heuristics** (heuristics.md): UPG-01, AUTH-01
> **Module**: [modules/upgrades-and-init.md](../modules/upgrades-and-init.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/6-unprotected-update-current-contract-wasm.md and test-cases; see ATTRIBUTION.md -->

## Description

`env.deployer().update_current_contract_wasm(hash)` replaces the contract's code. If the entry point
that calls it does not require the admin's authorization, anyone can swap in their own wasm and take
every asset the contract holds.

## Vulnerable pattern

```rust
pub fn upgrade(e: Env, new_wasm_hash: BytesN<32>) {
    e.deployer().update_current_contract_wasm(new_wasm_hash);
}
```

## Secure pattern

```rust
pub fn upgrade(e: Env, new_wasm_hash: BytesN<32>) {
    let admin: Address = e.storage().instance().get(&DataKey::Admin).unwrap();
    admin.require_auth();
    e.deployer().update_current_contract_wasm(new_wasm_hash);
}
```

## Detection

- `external_calls` with kind `upgrade` in `facts.json` whose entry point has empty `guards`.
- Auth taken from a caller-supplied `Address` argument instead of the stored admin.

## False-positive caveats (Gate C / FP-10 evidence)

- The guard sits in a helper (`require_admin(&e)`): facts show it as `… via <helper>`; read the helper.
- OpenZeppelin `#[only_owner]` / `#[only_role]` macros on the fn are a guard.

## Minimum tests (PoC and regression targets)

- Call `upgrade` with no auth mocked (`env.set_auths(&[])`): it must panic with an auth error.
- With the admin's auth mocked, the upgrade succeeds; with another address's auth, it fails.
````

For each other ID: Description from the doc's "Why is this bad?"/vulnerability text, rewritten for
Soroban auditors; Vulnerable/Secure pattern = the minimal diff between
`T/<name>/<name>-1/vulnerable-example/src/lib.rs` and `remediated-example` (trimmed to the lines
that matter); Detection = which `facts.json` fields or greps find it; FP caveats and Minimum tests
written for this pack. Keep each file under ~60 lines.

- [ ] **Step 3: Write `PK/patterns/README.md`**

Same structure as `chains/cairo/patterns/README.md`: how the engine uses patterns (lead, not finding;
FP caveats → Gate C / FP-10 evidence; minimum tests → PoC start list), naming (findings keep
`SOROBAN-<n>` IDs and cite the class ID in `category`), then one table row per pattern:
`| [ID](ID.md) | Lens | Category | Tier | One-line description |`. Leave a "Stellar classes" heading
with the note "added in the next task" (Task 7 fills it).

- [ ] **Step 4: Write `PK/ATTRIBUTION.md`**

Sections: "CoinFabrik Scout for Soroban" (repo URL, commit `53157fd4ddd9e388bf91138699f4e27a500aaef3`,
what was ported: `patterns/` 23 classes and `benchmarks/soroban/snippets/cases.jsonl`, the full MIT
license text copied from `SCOUT/LICENSE` including `Copyright (c) 2023 CoinFabrik`). Leave a
"Stellar Development Foundation" heading for Task 7.

- [ ] **Step 5: Verify and commit**

Run: `cd tests && SCOUT_SOROBAN_SRC=~/src/scout-soroban python3 -m unittest test_port_coverage -v`
Expected: `test_every_scout_class_has_a_pattern` PASS.
Run: `bash tests/run.sh` — all pass (the Scout test reads the default `~/src/scout-soroban`).

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban tests/test_port_coverage.py
git commit -m "Soroban: port Scout's vulnerability classes as patterns"
```

---

### Task 7: Port Stellar's security classes and the primer

**Files:**
- Create: `PK/patterns/<ID>.md` × 11, `PK/primers/soroban-vs-evm.md` (replaces stub), `PK/LICENSE-APACHE-2.0.txt`
- Modify: `PK/patterns/README.md`, `PK/ATTRIBUTION.md`

Map (also in the test from Task 6, `STELLAR_CLASSES`): `STELLAR/security.md` "### n." →

| n | Pattern ID | Lens | Notes |
|---|---|---|---|
| 1 | MISSING-AUTH | A | most common Soroban High; "right address" = policy authority from storage, not a caller-supplied param |
| 2 | AUTH-REPLAY-MIDDLEWARE | A + C | a pre-signed auth tree consumed by a contract that never auths the user itself |
| 3 | REINITIALIZATION | A | guarded `initialize` vs `__constructor` (SDK ≥ 22) |
| 4 | ARBITRARY-CONTRACT-CALL | C | token/contract address from arguments |
| 5 | (Scout INTEGER-OVERFLOW-OR-UNDERFLOW, no new file) | B | add Stellar's text to that pattern's Description as a second paragraph, with its own port comment |
| 6 | STORAGE-KEY-COLLISION | D | |
| 7 | CHECK-THEN-ACT | D | |
| 8 | TTL-ARCHIVAL | D | |
| 9 | UNTRUSTED-RETURN-VALUE | C | |
| 10 | RESOURCE-EXHAUSTION | D | fee griefing included |
| 11 | CUSTOM-ACCOUNT-CHECK-AUTH | A | `__check_auth` pitfalls |
| 12 | MALFORMED-BYTES | B | short/odd `Bytes` inputs, slicing panics |

- [ ] **Step 0: Add the failing Stellar coverage test** inside `class PortCoverageTest` in `tests/test_port_coverage.py` (the `STELLAR_CLASSES` map was added with the constants in Task 6):

```python
    def test_every_stellar_class_has_a_pattern(self):
        missing = [i for i in STELLAR_CLASSES.values()
                   if not os.path.isfile(os.path.join(SOROBAN_PATTERNS, i + ".md"))]
        self.assertEqual(missing, [], f"{len(missing)} Stellar classes have no patterns/<ID>.md")
        sec = os.path.join(STELLAR_SRC, "skills", "smart-contracts", "security.md")
        if not os.path.isfile(sec):
            self.skipTest(f"stellar-dev-skill source not found at {STELLAR_SRC}")
        with open(sec, encoding="utf-8") as f:
            numbers = [int(n) for n in re.findall(r"^### (\d+)\.", f.read(), re.M)]
        self.assertEqual(sorted(numbers), sorted(STELLAR_CLASSES), "source classes changed; update the map")
```

Run: `cd tests && STELLAR_DEV_SKILL_SRC=~/src/stellar-dev-skill python3 -m unittest test_port_coverage -v` → `test_every_stellar_class_has_a_pattern` FAILS (11 patterns missing; `INTEGER-OVERFLOW-OR-UNDERFLOW` exists from Task 6).

- [ ] **Step 1: Write the 11 patterns** in the Task 6 layout. Header comment:
  `<!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class <n>; modified by ChainSec; see ATTRIBUTION.md -->`.
  Code examples come from the source section; Detection, FP caveats and Minimum tests are written for this pack (use `facts.json` fields: for MISSING-AUTH, a `mutating` entry point with empty `guards` whose arguments include an `Address` that loses balance or rights; counter `unguarded_mutators`).

- [ ] **Step 2: Write `PK/primers/soroban-vs-evm.md`** (title "ChainSec Detection Primer: Soroban for EVM-Trained Auditors", like `chains/cairo/primers/starknet-vs-evm.md`). Sections:
  1. Threat model (ported from `STELLAR/security.md` "Threat model").
  2. What the platform rules out (ported: no `delegatecall`, no reentrancy, host-managed auth replay protection, explicit authorization) — and what each rule does **not** remove (external calls still fail or exhaust budget; forgetting `require_auth` is the bug to hunt).
  3. Translation table EVM → Soroban: `msg.sender` → no implicit caller, `Address::require_auth`; `payable`/ETH → XLM is a Stellar Asset Contract token; proxies → `update_current_contract_wasm` in place; storage slots → typed keys in three tiers with TTL; `uint256` → `i128` amounts (signed!); events → `env.events().publish`; block.timestamp → `env.ledger().timestamp()` (~5 s ledgers).
  4. Habits to drop (reentrancy findings, unchecked-call-return of `transfer` (SEP-41 panics, no bool), gas-griefing via 63/64).

- [ ] **Step 3: Update `patterns/README.md`** (fill the "Stellar classes" table) **and `ATTRIBUTION.md`** ("Stellar Development Foundation — stellar-dev-skill": repo URL, commit `9098e8ba24de3299cda24b21bb5cb80aa1cb5d2b`, files ported (`skills/smart-contracts/security.md` → 11 patterns, primer sections 1–2, heuristics in Task 8), the statement "ChainSec modified this material: reorganized into per-class files, rewrote detection/FP/test sections, added Soroban engine mappings", and a pointer to `LICENSE-APACHE-2.0.txt`). Copy `~/src/stellar-dev-skill/LICENSE` to `PK/LICENSE-APACHE-2.0.txt` unchanged.

- [ ] **Step 4: Verify and commit**

Run: `cd tests && SCOUT_SOROBAN_SRC=~/src/scout-soroban STELLAR_DEV_SKILL_SRC=~/src/stellar-dev-skill python3 -m unittest test_port_coverage -v` → all OK.
Run: `bash tests/run.sh` → all pass, lint resolves every link.

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban
git commit -m "Soroban: port Stellar security classes, primer and Apache attribution"
```

---

### Task 8: Heuristics, FP patterns, module triggers, modules, clustering

**Files (replace stubs / create):** `PK/heuristics.md`, `PK/fp-patterns.md`, `PK/module-triggers.md`, `PK/recon/clustering.md`, `PK/modules/{soroban-auth,storage-and-ttl,upgrades-and-init,token-integration,cross-contract-calls,resource-limits}.md`

**Interfaces:**
- Consumes: pattern IDs (Tasks 6–7), facts fields (Task 4), the section names the engine reads (below).
- Produces: heuristic IDs cited by patterns (`AUTH-*`, `UPG-*`, `INIT-*`, `STOR-*`, `TTL-*`, `TOK-*`, `ARITH-*`, `XC-*`, `RES-*`, `PANIC-*`, `RAND-*`, `TIME-*`, `BYTES-*`, `ACCT-*`, `DEPLOY-*`).

The engine reads these exact `heuristics.md` sections (grep `engine/` and `prompts/` for proof): "Extended heuristics", "Lens B additions", "Lens C additions", "Lens D additions", "Detector modules" (with "Question additions" and "Rules"), "Recon additions", "State audit additions", "Security strengths examples". Copy the heading skeleton from `chains/cairo/heuristics.md` and fill it for Soroban.

- [ ] **Step 1: `heuristics.md` — header and engine-ID mapping table**

```markdown
| Engine ID | Soroban equivalent |
|---|---|
| SIG-01, SIG-02, REPLAY-01, PERMIT-01 | AUTH-04 (host-managed nonces for `require_auth`), ACCT-01, ACCT-02 (`__check_auth`), BYTES-02 (`ed25519_verify` / `secp256k1_recover` over app data needs its own replay key) |
| PRX-01, PRX-02 | UPG-01 to UPG-03, INIT-01, INIT-02 |
| AEC-01 to AEC-03 | XC-01, XC-02 |
| RE-01, ROR-01, TOK-01, CALLBACK-01, HOOK-01 | XC-03: the host rejects re-entry into a contract already on the call stack, so classic reentrancy is not reachable; review ordering around failing calls instead |
| ETH-01, ETH-02, MRV-01 | TOK-01 to TOK-05 (no value attached to calls; XLM is a Stellar Asset Contract) |
| BRIDGE-01 to BRIDGE-04 | XC-04 plus `domains/defi/modules/cross-chain-bridge.md` (no native messaging layer) |
| PACKED-01, HASH-01 | BYTES-01, BYTES-02, STOR-01 |
| MODIFIER-01 | AUTH-05 (OpenZeppelin Stellar auth macros) |
| TS-01, C2-01, C2-02 | No transient storage; deterministic deploys: DEPLOY-01 |
```

- [ ] **Step 2: `heuristics.md` — "Core heuristics (Soroban)"**, one bullet per ID, each 1–3 lines, citing pattern IDs:
  - **AUTH-01** every `mutating` entry point that moves value or rights of an `Address` argument calls `require_auth` on *that* address (MISSING-AUTH; facts: empty `guards`, counter `unguarded_mutators`). **AUTH-02** admin auth must use the stored admin, not a parameter. **AUTH-03** re-auth at every layer that spends a user's authority (AUTH-REPLAY-MIDDLEWARE). **AUTH-04** `require_auth` replay is host-handled; `require_auth_for_args` binds only the listed args — check the args cover everything the user signs off on. **AUTH-05** `#[only_owner]`/`#[only_role]` expand to `require_auth` on the stored owner/role holder; check role admin paths. **AUTH-06** tests that call `env.mock_all_auths()` cannot show missing auth; check `env.auths()` assertions exist.
  - **ACCT-01** `__check_auth` verifies every signature over `signature_payload` and enforces policy per `auth_contexts` entry (CUSTOM-ACCOUNT-CHECK-AUTH). **ACCT-02** policy must not ignore contexts it does not recognise.
  - **INIT-01** guarded `initialize` can be front-run between deploy and init (REINITIALIZATION); prefer `__constructor`. **INIT-02** `__constructor` args stored without zero/validity checks (ZERO-ADDRESS).
  - **UPG-01** `update_current_contract_wasm` behind admin auth, with delay if users are promised one (UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM). **UPG-02** new code must read old storage: `#[contracttype]` enum keys encode variant names, struct fields are encoded by name; renames strand data; migrations versioned. **UPG-03** upgrade takes effect after the current invocation.
  - **STOR-01** keys from different modules or tuple shapes colliding (STORAGE-KEY-COLLISION). **STOR-02** user-controlled keys written to storage (SET-CONTRACT-STORAGE, UNPROTECTED-MAPPING-OPERATION). **STOR-03** big or growing data in `instance()` is loaded on every call — size and cost DoS. **STOR-04** `Vec`/`Map` in one entry that grows per user (VEC-COULD-BE-MAPPING, DOS-UNBOUNDED-OPERATION).
  - **TTL-01** persistent/instance entries archive when TTL lapses; access then fails until restored — stuck funds or DoS (TTL-ARCHIVAL). **TTL-02** data that must survive (balances, positions, admin) in `temporary()` is lost for good. **TTL-03** `extend_ttl` thresholds: instance TTL extended on hot paths; anyone can extend any entry, so "attacker keeps entry alive" is not a finding by itself.
  - **TOK-01** SEP-41 amounts are `i128`: reject `amount < 0` (negative transfer = reverse flow). **TOK-02** Stellar Asset Contract issuers can freeze (`set_authorized`) and `clawback`: a frozen user can block shared flows. **TOK-03** token address from arguments is untrusted (ARBITRARY-CONTRACT-CALL). **TOK-04** `transfer_from` with a `from` that is not the authorizing caller (UNRESTRICTED-TRANSFER-FROM). **TOK-05** SAC decimals are 7; custom tokens can differ; read `decimals()`.
  - **ARITH-01** `overflow-checks = true` must be in `[profile.release]` of the crate or workspace that builds the wasm (OVERFLOW-CHECK); otherwise release builds wrap silently. **ARITH-02** checked/wrapping/saturating ops and `as` casts (INTEGER-OVERFLOW-OR-UNDERFLOW; counter `unchecked_math`). **ARITH-03** rounding direction in fixed-point math (`soroban-fixed-point-math` `fixed_mul_floor`/`ceil`) favours the protocol (DIVIDE-BEFORE-MULTIPLY). **ARITH-04** `^` is XOR (INCORRECT-EXPONENTIATION).
  - **XC-01** called contract address from arguments or user storage (ARBITRARY-CONTRACT-CALL). **XC-02** return values from other contracts trusted without bounds (UNTRUSTED-RETURN-VALUE). **XC-03** reentrancy note (see mapping table). **XC-04** `try_invoke_contract` errors swallowed or `Result` ignored (UNUSED-RETURN-ENUM).
  - **RES-01** per-transaction CPU, memory and ledger-entry read/write limits are set by network config; loops over user-growable data hit them (DOS-UNBOUNDED-OPERATION, RESOURCE-EXHAUSTION). **RES-02** one bad element must not revert a batch (DOS-UNEXPECTED-REVERT-WITH-VECTOR). **RES-03** attacker-growable entries raise rent and fees for others.
  - **PANIC-01** `unwrap`/`expect`/`panic!`/`assert!` revert the whole invocation; a finding only when an attacker can force it on another user's critical path (UNSAFE-UNWRAP, UNSAFE-EXPECT, AVOID-PANIC-ERROR, ASSERT-VIOLATION, UNSAFE-MAP-GET).
  - **RAND-01** `env.prng()` and ledger fields are predictable or validator-influenced (INSUFFICIENTLY-RANDOM-VALUES). **TIME-01** `ledger().timestamp()` is ledger close time; staleness windows in ledgers vs seconds.
  - **BYTES-01** fixed-offset slicing of `Bytes` without length checks (MALFORMED-BYTES). **BYTES-02** custom signature schemes over app messages need domain separation + nonce.
  - **CHK-01** check-then-act across two invocations (CHECK-THEN-ACT).
  - **DEPLOY-01** `deployer().with_address(..., salt)` addresses are predictable; front-run deploy/init.
- [ ] **Step 3: `heuristics.md` — "Extended heuristics"**: one table, Scout ID → heuristic family → tier, plus the 11 Stellar IDs → family. Then "Lens B/C/D additions" (B: i128 sign, rounding, 7-decimals; C: XC-*, TOK-03; D: TTL-*, STOR-*, RES-*), "Detector modules (Soroban)" (Module A untrusted recipient: any `Address` can be a contract; Module B type casts; Module F token compatibility: SEP-41 vs SAC vs custom; Module G deployer patterns; Module O payment flow), "Question additions", "Rules".
- [ ] **Step 4: `heuristics.md` — "Recon additions"**: "Analyzer command (Step 2b)" — the Scout command from Task 5 Step 3, writing `A/analyzers/scout.json`; "Project identification (Step 1)" — read `facts.json` `sdk` (flag < 22: no `__constructor`) and `[profile.release] overflow-checks` in the workspace root `Cargo.toml`; workspace members; OpenZeppelin `stellar-contracts` usage (`#[contractimpl(contracttrait)]` parents in units = macro-generated entry points the extractor cannot list: open the trait to enumerate them); "Scope expansion (Step 3)"; "Risk-score counters (Step 3)" — explain each counter from Task 4; "Untrusted Recipient Map (Step 3c)"; "Attacker mindset (Step 4)"; "Integration checklists (Step 5)" — SAC, OpenZeppelin Stellar, Blend, Soroswap, Reflector oracle. Then "State audit additions" and "Security strengths examples".
- [ ] **Step 5: `fp-patterns.md`** — mirror `chains/cairo/fp-patterns.md` headings: FP-3 OpenZeppelin Stellar contracts standard protection; FP-7 Rust arithmetic safety (overflow-checks on → panic, not wrap); FP-8 view confusion (no view keyword: use facts `mutability`); FP-9 test/mock code (`test.rs`, `testutils`, `#[cfg(test)]`); plus Soroban-specific FP-S1 reentrancy claims (host forbids), FP-S2 replay claims against `require_auth` (host nonces), FP-S3 panic with no third-party victim (quality tier → QA), FP-S4 `mock_all_auths` in tests is not a contract bug. "Gate overrides and examples" (Gate A/B/C/D/E with one Soroban example each) and "Masking code examples".
- [ ] **Step 6: `module-triggers.md`** — two tables like `chains/cairo/module-triggers.md`. Pack modules:

| Module File | Tier | Select If... |
|---|---|---|
| `chains/soroban/modules/soroban-auth.md` | 0 | Always — every contract has `require_auth` decisions |
| `chains/soroban/modules/storage-and-ttl.md` | 0 | Always — every contract stores data with a TTL |
| `chains/soroban/modules/upgrades-and-init.md` | 2 | `update_current_contract_wasm` (counter `upgrades` > 0), `initialize`, `__constructor`, migration fns |
| `chains/soroban/modules/token-integration.md` | 2 | `token::Client`, `StellarAssetClient`, SEP-41 impls, `transfer_from`, counter `token_transfers` > 0 |
| `chains/soroban/modules/cross-contract-calls.md` | 2 | `*Client::new` on non-token contracts, `invoke_contract`, `try_invoke_contract`, `contractimport!` |
| `chains/soroban/modules/resource-limits.md` | 2 | loops over storage `Vec`/`Map`, per-user lists, batch entry points |

Second table: Soroban code evidence for each `domains/defi/triggers.md` module (oracles: Reflector `lastprice`, `SEP-40`; vaults: share math; lending: Blend-style `submit` requests; AMM: Soroswap router/pair; bridge: Allbridge/LayerZero endpoints).
- [ ] **Step 7: Six modules** — each with the header block used by `chains/cairo/modules/l1-l2-messaging.md` (`> **Trigger**`, `> **Inject into**`, `> **Priority**`, port comment) and numbered sections with a table to fill and bullets citing heuristic IDs:
  - `soroban-auth.md` (Inject into Lens A): Auth map table `| Entry point | Address args | require_auth on | Source of authority |`; middleware replay; `require_auth_for_args` coverage; `__check_auth`; `authorize_as_current_contract` sub-invocation scope.
  - `storage-and-ttl.md` (Lens D): Storage inventory `| Key | Tier | Writer | Grows per user? | TTL extended where? |`; archival paths; collisions.
  - `upgrades-and-init.md` (Lens A): upgrade gate, layout compatibility, init/constructor.
  - `token-integration.md` (Lens B + C): token table `| Token | Kind (SAC/custom) | Source of address | Decimals | Freeze/clawback exposure |`; i128 sign checks; fee-on-transfer custom tokens.
  - `cross-contract-calls.md` (Lens C): callee table `| Call site | Callee address source | Trusted? | Return value checked? | Failure handling |`.
  - `resource-limits.md` (Lens D): loops and batches over growable data; fee griefing.
- [ ] **Step 8: `recon/clustering.md`** — mirror `chains/cairo/recon/clustering.md`: "Build clusters" (one `#[contract]` type, its `#[contractimpl]` blocks, and the crate helper modules its entry points call — storage, admin, events; shared library crates join every cluster that uses them), "Findings cap" (~1500 LOC per cluster, ≤ 8 clusters, same as Solidity/Cairo), "Inputs" (`facts.json` units/parents, `risk.json`).
- [ ] **Step 9: Verify and commit**

Run: `bash tests/run.sh` — lint 0 errors (all backticked `chains/soroban/...` paths resolve), all tests pass.
Run: `grep -c '^## ' plugins/chainsec/skills/chainsec/chains/soroban/heuristics.md` and confirm every section listed above exists.

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban
git commit -m "Soroban: heuristics, FP patterns, module triggers, modules and clustering"
```

---

### Task 9: PoC guide (verified on the fixture)

**Files:** Replace stub `PK/poc/guide.md`

**Interfaces:** Consumes `pack.json` `poc.run` (Task 2). Placeholders: `<crate>` = contract crate folder relative to the audited root (`.` for one crate); `<test file>` = `chainsec_poc_<id>.rs`; `<id>` = lower-case finding ID with `-` → `_` (Rust test target names cannot contain `-`).

- [ ] **Step 1: Write the PoC test the guide will show, and run it against the fixture**

`tests/fixtures/soroban-basic/` is the target. Save as `/tmp/chainsec_poc_soroban_001.rs`:

```rust
//! PoC SOROBAN-001: withdraw debits `from` without `from.require_auth()`.
use chainsec_vault::{Vault, VaultClient};
use soroban_sdk::{testutils::Address as _, token, Address, Env};

#[test]
fn chainsec_poc_soroban_001_withdraw_without_auth() {
    let env = Env::default();
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

Run the exact `poc.run` line with `<TARGET>` = the fixture, `<root>` = `.`, `<crate>` = `.`:

```bash
T=$PWD/tests/fixtures/soroban-basic
mkdir -p $T/.audit/soroban/poc/SOROBAN-001 && cp /tmp/chainsec_poc_soroban_001.rs $T/.audit/soroban/poc/SOROBAN-001/
cd $T && mkdir -p tests && cp $T/.audit/soroban/poc/SOROBAN-001/chainsec_poc_soroban_001.rs tests/ && CARGO_TARGET_DIR=$T/.audit/soroban/target cargo test --test chainsec_poc_soroban_001 2>&1; rm -f tests/chainsec_poc_soroban_001.rs
```

Expected: `test chainsec_poc_soroban_001_withdraw_without_auth ... ok`. Then `rmdir $T/tests; rm -rf $T/.audit` (the fixture has no `tests/` of its own).

- [ ] **Step 2: Negative control** — in a scratch copy of the fixture, add `from.require_auth();` as the first line of `withdraw`, rerun: the test must FAIL with an auth error (`Error(Auth, InvalidAction)`). This proves the PoC asserts the bug, not the setup.

- [ ] **Step 3: Write `poc/guide.md`** (mirror `chains/cairo/poc/guide.md` headings):
  - "## soroban-sdk testutils workflow steps"
  - "### 1. Recon the PoC environment (MANDATORY)": `soroban-sdk` with `features = ["testutils"]` under `[dev-dependencies]` (add it in a scratch copy if missing, never in the user's tree); `[lib] crate-type` must include `"lib"` or `"rlib"` for integration tests to `use <crate_name>::...` — if it is `["cdylib"]` only, use the fallback in step 2; note the package name (dashes become underscores in `use`); run the project's own `cargo test` once.
  - "### 2. Choose the harness: native, wasm import, or ledger snapshot": native (default, link the crate); wasm fallback (`stellar contract build --out-dir <TARGET>/.audit/soroban/wasm` then `mod c { soroban_sdk::contractimport!(file = "<path>.wasm"); }` and `env.register(c::WASM, (args,))`); snapshot (`stellar snapshot create --address <C> --output json --out <file>` + `Env::from_ledger_snapshot_file`) for deployed contracts — needs an RPC/archive; stay native otherwise.
  - "### 3. Write the test": location `.audit/soroban/poc/<ID>/chainsec_poc_<id>.rs`; the verified skeleton from Step 1; every test fn name starts with `chainsec_poc_<id>`.
  - "### 4. testutils features real PoCs use": `Address::generate`, `env.register(Contract, (ctor args,))`, `register_stellar_asset_contract_v2` + `StellarAssetClient::mint`, `env.mock_all_auths()` vs `env.set_auths(&[])` vs `mock_auths(&[MockAuth{..}])`, `env.auths()`, `env.ledger().set_timestamp/with_mut`, `try_<fn>` client methods to assert errors, `env.cost_estimate()` / budget for resource DoS.
  - "### 5. Assert the HARM, not the mechanism": balances moved, admin changed, funds stuck — never "the call did not panic".
  - "### 6. Compile → run → fix": common errors (missing `testutils` feature, cdylib-only crate, `#![no_std]` crate needs `extern crate std` in tests only if using std), and `cargo test --release` when the bug depends on `[profile.release] overflow-checks`.
- [ ] **Step 4: Verify and commit** — `bash tests/run.sh` passes.

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban/poc/guide.md
git commit -m "Soroban PoC guide, verified on the soroban-basic fixture"
```

---

### Task 10: Fuzz guide (verified on the fixture)

**Files:** Replace stub `PK/fuzz/guide.md`

**Interfaces:** Consumes `pack.json` `fuzz.run`: the file is always `.audit/soroban/fuzz/tests/chainsec_fuzz.rs`, and every invariant test fn starts with `chainsec_fuzz_`.

- [ ] **Step 1: Write the harness the guide will show and run it**

Save as `$T/.audit/soroban/fuzz/tests/chainsec_fuzz.rs` (`T` = fixture path):

```rust
//! ChainSec stateful invariant fuzz: seeded random action sequences, no extra dependencies.
//! Seeds: CHAINSEC_FUZZ_SEED (default 1), runs: CHAINSEC_FUZZ_RUNS (default 64), depth 32.
use chainsec_vault::{Vault, VaultClient};
use soroban_sdk::{testutils::Address as _, token, Address, Env};

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
}

fn env_u64(key: &str, default: u64) -> u64 {
    std::env::var(key).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

#[test]
fn chainsec_fuzz_vault_invariants() {
    let seed = env_u64("CHAINSEC_FUZZ_SEED", 1);
    for run in 0..env_u64("CHAINSEC_FUZZ_RUNS", 64) {
        let mut rng = Rng(seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) ^ (run + 1));
        let env = Env::default();
        env.mock_all_auths();
        let admin = Address::generate(&env);
        let sac = env.register_stellar_asset_contract_v2(admin.clone());
        let tok = token::Client::new(&env, &sac.address());
        let vault = env.register(Vault, (admin.clone(), sac.address()));
        let v = VaultClient::new(&env, &vault);
        let users: [Address; 3] = core::array::from_fn(|_| Address::generate(&env));
        for u in users.iter() {
            token::StellarAssetClient::new(&env, &sac.address()).mint(u, &1_000);
        }
        for step in 0..32 {
            let a = &users[rng.below(3) as usize];
            let b = &users[rng.below(3) as usize];
            let amt = rng.below(400) as i128;
            match rng.below(2) {
                0 => {
                    if tok.balance(a) >= amt {
                        v.deposit(a, &amt);
                    }
                }
                _ => {
                    if v.balance(a) >= amt && amt > 0 {
                        let before = v.balance(a);
                        v.withdraw(a, b, &amt);
                        // INV-1: debiting `a` requires `a`'s authorization.
                        let authed = env.auths().iter().any(|(addr, _)| addr == a);
                        assert!(authed || v.balance(a) == before,
                            "INV-1 broken: seed {seed} run {run} step {step}: {a:?} debited without auth");
                    }
                }
            }
            // INV-2: vault token holdings equal the sum of recorded balances.
            let sum: i128 = users.iter().map(|u| v.balance(u)).sum();
            assert_eq!(tok.balance(&vault), sum, "INV-2 broken: seed {seed} run {run} step {step}");
        }
    }
}
```

Run the `fuzz.run` line (`<crate>` = `.`):

```bash
cd $T && mkdir -p tests && cp $T/.audit/soroban/fuzz/tests/chainsec_fuzz.rs tests/ && CARGO_TARGET_DIR=$T/.audit/soroban/target cargo test --test chainsec_fuzz -- --nocapture 2>&1; rm -f tests/chainsec_fuzz.rs
```

Expected (planted bug): `test chainsec_fuzz_vault_invariants ... FAILED` with
`INV-1 broken: seed 1 run 0 step 4: Contract(...) debited without auth`. Then `rmdir $T/tests; rm -rf $T/.audit`.
In a scratch copy with `from.require_auth();` added to `withdraw`, the same command PASSES (64 runs × 32 steps).

- [ ] **Step 2: Write `fuzz/guide.md`** (mirror `chains/cairo/fuzz/guide.md` headings):
  - Opening paragraph, said plainly: soroban-sdk has no Foundry-style invariant runner. ChainSec's default is a dependency-free, seeded, stateful sequence test (the harness above): reproducible (`CHAINSEC_FUZZ_SEED`, `CHAINSEC_FUZZ_RUNS`), stable toolchain, no new crates. If the project already has `proptest` in dev-dependencies, a `proptest!` with `Vec<Action>` strategies is allowed. `cargo-fuzz` (nightly, `soroban-sdk` `testutils` + `arbitrary`) is for long campaigns outside the audit loop.
  - "## Require/assert mining examples" — `panic!`/`assert!`/`require_auth`/`Error` enums in the target → candidate invariants.
  - "## Test generation patterns" — actions as `match rng.below(n)`, actors as a fixed `Address` array, preconditions skip instead of expecting panics, invariants checked after every step, auth invariants via `env.auths()` under `mock_all_auths`, conservation (`token.balance(contract) == Σ recorded`), `try_` methods for expected failures.
  - "## Iterative fix loop" — failing seed/run/step in the message → shrink by lowering depth → turn into a PoC (Task 9 layout).
  - "## soroban pipeline steps" — where files go, the `fuzz.run` line, reporting.
- [ ] **Step 3: Verify and commit** — `bash tests/run.sh` passes.

```bash
git add plugins/chainsec/skills/chainsec/chains/soroban/fuzz/guide.md
git commit -m "Soroban fuzz guide: seeded stateful invariant harness, verified on the fixture"
```

---

### Task 11: Snippet regression suite (Scout test cases)

**Files:**
- Create: `benchmarks/soroban/snippets/{README.md,import_scout.py,cases.jsonl,make_projects.py,score_snippets.py}`
- Test: `tests/test_soroban_snippets.py`

**Interfaces:**
- Consumes: `SCOUT/test-cases` at commit `53157fd`; pattern IDs (Task 6) as `class_id`.
- Produces: `cases.jsonl` (92 cases, 22 classes; `soroban-version` skipped: its cases differ only in a shared workspace pin), `manifest.json` `{project: [{case_id, class_id, expected_detect, tier, dir}]}`, score JSON `{total, per_tier, per_class, missing_projects}`.

- [ ] **Step 1: Write the failing test** — `tests/test_soroban_snippets.py`:

```python
import json
import os
import sys
import tempfile
import unittest

from helpers import REPO, run

S = os.path.join(REPO, "benchmarks", "soroban", "snippets")


class SorobanSnippetSuiteTest(unittest.TestCase):
    def test_cases_are_scrubbed(self):
        for line in open(os.path.join(S, "cases.jsonl"), encoding="utf-8"):
            case = json.loads(line)
            for name, text in case["files"].items():
                low = text.lower()
                self.assertNotIn("vulnerable", low, f"{case['case_id']}:{name}")
                self.assertNotIn("remediated", low, f"{case['case_id']}:{name}")
                self.assertNotIn("#[cfg(test)]\nmod", text, f"{case['case_id']}:{name}")

    def test_make_and_score(self):
        out = tempfile.mkdtemp()
        r = run([sys.executable, os.path.join(S, "make_projects.py"), os.path.join(S, "cases.jsonl"), out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"projects": 6, "cases": 92})
        manifest = json.load(open(os.path.join(out, "manifest.json")))
        first = manifest["snippets-1"]
        vuln = next(c for c in first if c["expected_detect"])
        clean = next(c for c in first if not c["expected_detect"])
        toml = open(os.path.join(out, "snippets-1", vuln["dir"], "Cargo.toml")).read()
        self.assertRegex(toml, r'name = "case-\d\d"')
        self.assertIn("soroban-sdk", open(os.path.join(out, "snippets-1", "Cargo.toml")).read())
        os.makedirs(os.path.join(out, "snippets-1", ".audit"))
        with open(os.path.join(out, "snippets-1", ".audit", "findings.json"), "w") as f:
            json.dump([{"id": "SOROBAN-001", "locations": [{"file": vuln["dir"] + "src/lib.rs", "line_start": 3}]},
                       {"id": "SOROBAN-002", "locations": [{"file": clean["dir"] + "Cargo.toml", "line_start": 1}]}], f)
        r = run([sys.executable, os.path.join(S, "score_snippets.py"), os.path.join(out, "manifest.json"), out])
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        self.assertEqual((res["total"]["detected"], res["total"]["flagged_clean"]), (1, 1))
        self.assertEqual(len(res["missing_projects"]), 5)


if __name__ == "__main__":
    unittest.main()
```

Run: `cd tests && python3 -m unittest test_soroban_snippets -v` → errors (files missing).

- [ ] **Step 2: Write `import_scout.py`**

```python
#!/usr/bin/env python3
"""Build cases.jsonl from CoinFabrik scout-soroban test cases (MIT).

Usage: import_scout.py SCOUT_DIR OUT_JSONL

One case per vulnerable/remediated example crate. Each case keeps Cargo.toml and src/**/*.rs with
everything that would leak the answer removed: comments, `#[cfg(test)]` modules and the package name
(which says "vulnerable" or "remediated"). `{ workspace = true }` dependencies are resolved from the
class workspace so each crate stands alone. `soroban-version` is skipped: its cases differ only in
the shared workspace pin.
"""
import json
import os
import re
import subprocess
import sys

SKIP = {"soroban-version"}
QUALITY = {"unsafe-unwrap", "unsafe-expect", "avoid-panic-error", "avoid-unsafe-block", "avoid-core-mem-forget",
           "iterators-over-indexing", "vec-could-be-mapping", "assert-violation"}
TOKENS = re.compile(r'(?<![\w])b?r(#*)".*?"\1|(?<![\w])b?"(?:\\.|[^"\\])*"'
                    r"|(?<![\w])b?'(?:\\(?:u\{[0-9a-fA-F]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'"
                    r'|//[^\n]*|/\*.*?\*/', re.S)
CFG_TEST = re.compile(r'#\[cfg\(test\)\]\s*(?:pub\s+)?mod\s+\w+\s*\{')
WS_DEP = re.compile(r'^(\s*soroban-sdk\s*=\s*\{)\s*workspace\s*=\s*true\s*(,?)', re.M)
LEAK = re.compile(r'(?i)_?(?:vulnerable|remediated)(?:_example)?_?')
SDK_PIN = re.compile(r'soroban-sdk\s*=\s*(?:"([^"]+)"|\{[^}\n]*?version\s*=\s*"([^"]+)")')


def strip_comments(src):
    out = TOKENS.sub(lambda m: m.group(0) if m.group(0)[:2] not in ("//", "/*") else "", src)
    return re.sub(r'[ \t]+\n', '\n', out)


def drop_test_mods(src):
    while True:
        m = CFG_TEST.search(src)
        if not m:
            return src
        depth, i = 0, m.end() - 1
        for i in range(m.end() - 1, len(src)):
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            if depth == 0:
                break
        src = src[:m.start()] + src[i + 1:]


def scrub(text):
    """Remove the words that reveal the expected answer from identifiers and names."""
    return LEAK.sub(lambda m: "_" if m.group(0)[:1] == "_" and m.group(0)[-1:] == "_" else "", text)


def clean_toml(text, pin):
    text = re.sub(r'(?m)^\s*#.*\n', '', text)
    text = re.sub(r'(?m)^name\s*=\s*"[^"]*"', 'name = "case"', text, count=1)
    return WS_DEP.sub(lambda m: f'{m.group(1)} version = "{pin}"{m.group(2)}', text)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    scout, out_path = argv[0], argv[1]
    commit = subprocess.run(["git", "-C", scout, "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip() or "unknown"
    base = os.path.join(scout, "test-cases")
    rows = []
    for cls in sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))):
        if cls in SKIP:
            continue
        ws = os.path.join(base, cls, "Cargo.toml")
        m = SDK_PIN.search(open(ws, encoding="utf-8").read()) if os.path.isfile(ws) else None
        pin = (m.group(1) or m.group(2)) if m else "=20.0.0"
        for case in sorted(d for d in os.listdir(os.path.join(base, cls)) if d.startswith(cls + "-")):
            for kind, vuln in (("vulnerable-example", True), ("remediated-example", False)):
                crate = os.path.join(base, cls, case, kind)
                if not os.path.isdir(crate):
                    continue
                files = {"Cargo.toml": clean_toml(open(os.path.join(crate, "Cargo.toml"), encoding="utf-8").read(), pin)}
                for dirpath, _, names in os.walk(os.path.join(crate, "src")):
                    for n in sorted(names):
                        if n.endswith(".rs"):
                            p = os.path.join(dirpath, n)
                            src = open(p, encoding="utf-8").read()
                            files[os.path.relpath(p, crate).replace(os.sep, "/")] = scrub(drop_test_mods(strip_comments(src)))
                rows.append({"case_id": f"{case}-{'vuln' if vuln else 'fixed'}", "class_id": cls.upper(),
                             "expected_detect": vuln, "tier": "quality" if cls in QUALITY else "security",
                             "source_url": f"https://github.com/CoinFabrik/scout-soroban/tree/{commit}/test-cases/{cls}/{case}/{kind}",
                             "files": files})
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print(json.dumps({"cases": len(rows), "classes": len({r["class_id"] for r in rows}), "commit": commit}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Generate `cases.jsonl` once**

Run: `python3 benchmarks/soroban/snippets/import_scout.py ~/src/scout-soroban benchmarks/soroban/snippets/cases.jsonl`
Expected: `{"cases": 92, "classes": 22, "commit": "53157fd4ddd9e388bf91138699f4e27a500aaef3"}` and a file of about 160 KB.
`source_url` values still name `vulnerable-example`/`remediated-example`; that is intended. They stay
in `cases.jsonl`, `make_projects.py` never writes them into projects, and the test checks only the
case file contents for leaks.

- [ ] **Step 4: Write `make_projects.py`**

```python
#!/usr/bin/env python3
"""Write Soroban snippet projects. Usage: make_projects.py CASES_JSONL OUT [--classes-per-project N]

Groups cases by class (N classes per project, default 4) into Cargo workspaces OUT/snippets-<k>/
with one member crate per case at contracts/case-<nn>/ (neutral names, shuffled by a fixed seed so
the order does not reveal vulnerable vs fixed). Writes OUT/manifest.json:
{project: [{case_id, class_id, expected_detect, tier, dir}]}.
"""
import argparse
import json
import os
import random

ROOT_TOML = ('[workspace]\nresolver = "2"\nmembers = ["contracts/*"]\n\n'
             '[workspace.dependencies]\nsoroban-sdk = "=20.0.0"\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("out")
    ap.add_argument("--classes-per-project", type=int, default=4)
    args = ap.parse_args(argv)
    cases = [json.loads(line) for line in open(args.cases, encoding="utf-8") if line.strip()]
    classes = sorted({c["class_id"] for c in cases})
    n = args.classes_per_project
    manifest = {}
    for k in range(0, len(classes), n):
        group = set(classes[k:k + n])
        proj = f"snippets-{k // n + 1}"
        members = [c for c in cases if c["class_id"] in group]
        random.Random(proj).shuffle(members)
        pdir = os.path.join(args.out, proj)
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "Cargo.toml"), "w", encoding="utf-8") as f:
            f.write(ROOT_TOML)
        rows = []
        for i, c in enumerate(members, 1):
            rel = f"contracts/case-{i:02d}"
            for name, text in c["files"].items():
                path = os.path.join(pdir, rel, name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if name == "Cargo.toml":
                    text = text.replace('name = "case"', f'name = "case-{i:02d}"', 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            rows.append({k2: c[k2] for k2 in ("case_id", "class_id", "expected_detect", "tier")} | {"dir": rel + "/"})
        manifest[proj] = rows
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({"projects": len(manifest), "cases": len(cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Write `score_snippets.py`**

```python
#!/usr/bin/env python3
"""Score the Soroban snippet suite. Usage: score_snippets.py MANIFEST OUT

Reads OUT/<project>/.audit/findings.json (final, report-level findings). A case is detected when
any finding has a location under its crate dir; a fixed case with a finding is flagged-clean (an
FP). Totals are reported per tier ("security", "quality") and per class. A project without
findings.json is reported as missing and its cases are not scored.
"""
import json
import os
import sys

KEYS = ("detected", "missed", "flagged_clean", "clean_ok")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    manifest_path, out = argv[0], argv[1]
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    per_class, per_tier, missing = {}, {}, []
    for proj, cases in sorted(manifest.items()):
        path = os.path.join(out, proj, ".audit", "findings.json")
        if not os.path.isfile(path):
            missing.append(proj)
            continue
        files = [loc.get("file") or "" for f in json.load(open(path, encoding="utf-8"))
                 for loc in (f.get("locations") or []) if isinstance(loc, dict)]
        for c in cases:
            flagged = any(f.startswith(c["dir"]) for f in files)
            key = ("detected" if flagged else "missed") if c["expected_detect"] else \
                  ("flagged_clean" if flagged else "clean_ok")
            for table, name in ((per_class, c["class_id"]), (per_tier, c["tier"])):
                table.setdefault(name, dict.fromkeys(KEYS, 0))[key] += 1
    total = {k: sum(r[k] for r in per_class.values()) for k in KEYS}
    print(json.dumps({"total": total, "per_tier": per_tier, "per_class": per_class,
                      "missing_projects": missing}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Write `README.md`** — like `benchmarks/cairo/snippets/README.md`: source + MIT credit + commit; "regression check, not acceptance" (patterns come from the same source; contract struct names still name the class); projects are **not meant to build** (cases pin `=20.0.0`, `20.3.2` and `=21.3.0`, which conflict in one workspace), so run audits with `CHAINSEC_NO_COMPILE=1`; the three steps (make → `chainsec-audit --quick` per project in a fresh session → score); scoring reports `security` and `quality` tiers separately and **only the security tier is a pass/fail signal**.

- [ ] **Step 7: Verify and commit**

Run: `cd tests && python3 -m unittest test_soroban_snippets -v` → 2 OK. `bash tests/run.sh` → all pass.

```bash
git add benchmarks/soroban/snippets tests/test_soroban_snippets.py
git commit -m "Soroban snippet regression suite from Scout test cases"
```

---

### Task 12: Contest benchmark registry (runs need user approval)

**Files:** Create `benchmarks/soroban/registry.yaml`

- [ ] **Step 1: Confirm each contest's repo and report URL** (public pages; read-only). Candidates found 2026-11-26: Code4rena "Blend v2" (24 Feb – 18 Mar 2025, `code4rena.com/audits/2025-02-blend-v2-audit-certora-formal-verification`), "LayerZero – Stellar endpoint" (1–14 Apr 2026, report `code4rena.com/reports/2026-04-layerzero-stellar-endpoint`), "K2" (2026-04, `code4rena.com/audits/2026-04-k2`, lending). For each, record the `code-423n4/<contest>` repo, the findings repo and whether the report lists High/Medium findings. Drop a contest whose report has no High/Medium.

- [ ] **Step 2: Write `registry.yaml`** in the Cairo registry format (`benchmarks/cairo/registry.yaml`): header comment with the acceptance rule — baseline = same agent and model with the official `stellar-dev-skill` loaded, asked for a High/Medium audit of the same commit and scope; pass = ChainSec recall ≥ baseline and FP ≤ baseline; scoring per `benchmarks/solidity/scoring.md` (exact 1, partial 0.5); commits pinned when a run starts; `status: pending` (K2 `optional`).

- [ ] **Step 3: Commit**

```bash
git add benchmarks/soroban/registry.yaml
git commit -m "Soroban contest benchmark registry"
```

- [ ] **Step 4: STOP — ask the user before running audits.** Each target is two full audits (ChainSec + baseline). Report the estimated cost and wait for approval. Results go to `benchmarks/soroban/results/<id>.json` via `tools/score_benchmark.py`.

---

### Task 13: Docs, smoke test, release notes

**Files:** Modify `README.md` (line 6 "Soroban planned" and the chains table), `INSTALL.md` (tool list near line 73), `docs/PROGRESS.md` (Sub-project 3 row and a "Soroban pack" section), `docs/smoke-tests.md`

- [ ] **Step 1: Docs** — README: "Solidity, Starknet Cairo (preview) and Stellar Soroban (preview)"; chains table row `| Soroban (Stellar) | Preview: soroban-sdk ≥ 20, benchmark in progress |`. INSTALL: "For Soroban: `cargo` (required; PoC and fuzz use soroban-sdk testutils), `stellar` CLI (optional: wasm PoC fallback, ledger snapshots), `cargo-scout-audit` (optional)". PROGRESS: Sub-project 3 status and what was built (mirror the Cairo section).

- [ ] **Step 2: Claude Code quick smoke test** — copy the fixture to a scratch folder outside the repo, run `chainsec-audit --quick` there in a fresh Claude Code session. Pass: the report has a High/Critical finding on `withdraw` missing `from.require_auth()`, and no finding claims reentrancy. Record duration and result in `docs/smoke-tests.md` (same table format as the existing entries). Repeat in OpenCode if available (`-m opencode/<free model>`).

- [ ] **Step 3: Final verification** — `bash tests/run.sh`; `CHAINSEC_SLOW_TESTS=1 python3 -m unittest discover -s tests -p 'test_extract_soroban.py'`; lint 0 errors. Use superpowers:verification-before-completion before claiming done.

- [ ] **Step 4: Commit**

```bash
git add README.md INSTALL.md docs
git commit -m "Docs and smoke test for the Soroban pack"
```

Then use superpowers:finishing-a-development-branch (merge/PR is the user's call; do not push unasked).

---

## Open decisions (defaults chosen; change before execution if needed)

1. **Benchmark baseline** — no Soroban audit skill exists to compare against (Cairo used cairo-auditor). Default: same agent + official `stellar-dev-skill`. Alternative: Scout output alone, or a plain agent with no skill.
2. **Workspaces without a root `soroban-sdk` dependency** produce several roots, and the engine stops ("one root per chain"). Default: keep the engine as is (deferred, as for Cairo). Alternative: a small `detect-chain.py` change that collapses member roots into the `[workspace]` root.
3. **Branch base** — `feat/soroban-pack` sits on `feat/cairo-pack` (unmerged). Default: rebase onto `main` after Cairo merges.
