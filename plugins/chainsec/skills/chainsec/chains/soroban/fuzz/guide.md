# Soroban fuzz guide (soroban-sdk testutils, seeded sequences)

Pack half of `engine/fuzz.md` for Soroban. Verified on `tests/fixtures/soroban-basic` with cargo 1.99 /
soroban-sdk 26.1.1.

**Limitation:** soroban-sdk has no Foundry-style invariant runner. ChainSec's default is a
dependency-free, seeded, stateful sequence test (the harness below): it builds a fresh `Env` per run,
applies random sequences of contract calls, and checks the invariants after every step. It is
reproducible (`CHAINSEC_FUZZ_SEED`, `CHAINSEC_FUZZ_RUNS`), runs on the stable toolchain and adds no
crates. If the project already has `proptest` in `[dev-dependencies]`, a `proptest!` over a
`Vec<Action>` strategy is allowed instead. `cargo-fuzz` (nightly, `soroban-sdk` `testutils` +
`arbitrary`) is for long campaigns outside the audit loop.

Placeholders (`<CORE>`, `<crate>`, `<TARGET>`, `<root>`) are defined in `chains/soroban/poc/guide.md`.
The helper `chains/soroban/poc/run-test.sh` is the same one the PoC flow uses; it exits 2 and refuses to
run on a stale `Cargo.lock` backup, see that guide.

## Require/assert mining examples

Mine `panic!`, `assert!`, `require_auth()` / `require_auth_for_args`, and `contracterror` enums
(`panic_with_error!`, `Err(Error::X)`) as candidate invariants, plus implied rules:

- every function that debits an address's balance requires that address's authorization;
- tokens held by the contract equal the sum of recorded balances (conservation);
- only the admin changes the admin or upgrades the wasm;
- a recorded balance never goes negative.

Each becomes one assertion in the harness, or its own `chainsec_fuzz_<topic>` test function.

## Test generation patterns

Tests live in `.audit/soroban/fuzz/tests/chainsec_fuzz.rs` (one file, any number of test functions, each
named `chainsec_fuzz_<topic>`). The pack's `fuzz.run` calls `run-test.sh`, which copies the file into the
crate's `tests/`, runs `cargo test --test chainsec_fuzz -- --nocapture`, and restores the crate. Dev
dependencies: see `chains/soroban/poc/guide.md` step 1.

Patterns:

- Actions are `match rng.below(n)`; actors are a fixed `Address` array; amounts come from `rng.below(..)`.
- Preconditions skip instead of expecting a panic (`if v.balance(a) >= amt { .. }`). Use `try_<fn>` clients
  when a failure is the expected outcome.
- Check every invariant after every step, and put the seed, run and step in the message.
- Auth invariants: under `mock_all_auths`, `env.auths()` lists the authorizations the last call required;
  assert the debited address appears in it.
- Conservation: `token.balance(contract) == sum of recorded balances`.
- Create the `Env` with `Env::new_with_config(EnvTestConfig { capture_snapshot_at_drop: false })` so no
  `test_snapshots/` files are written into the audited crate (see the PoC guide step 3).

Verified harness (planted bug: `withdraw` debits `from` without `from.require_auth()`):

<!-- chainsec:verified-fuzz-harness -->

```rust
//! ChainSec stateful invariant fuzz: seeded random action sequences, no extra dependencies.
//! Seeds: CHAINSEC_FUZZ_SEED (default 1), runs: CHAINSEC_FUZZ_RUNS (default 64), depth 32.
use chainsec_vault::{Vault, VaultClient};
use soroban_sdk::{
    testutils::{Address as _, EnvTestConfig},
    token, Address, Env,
};

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
        // No test_snapshots/ files are written into the audited crate.
        let env = Env::new_with_config(EnvTestConfig { capture_snapshot_at_drop: false });
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

Run on the unmodified fixture copy it FAILS with `INV-1 broken: seed 1 run 0 step <n>: Contract(..) debited
without auth`. With `from.require_auth();` added as the first line of `withdraw` (scratch copy) it prints
`test chainsec_fuzz_vault_invariants ... ok` (64 runs x 32 steps).

## Iterative fix loop

1. Run `fuzz.run`. A failing test prints `INV-<n> broken: seed S run R step T`.
2. Decide: **real violation** (the contract breaks the invariant: keep seed/run/step as the
   counterexample), **wrong invariant** (fix the property), or **harness bug** (fix setup or the
   precondition skips).
3. Reproduce with the same seed (`CHAINSEC_FUZZ_SEED=S CHAINSEC_FUZZ_RUNS=R+1`; set them in the
   environment before the `fuzz.run` command). Shrink by lowering the step depth (`for step in 0..T+1`)
   until the shortest failing sequence remains.
4. Turn a real violation into a PoC with the layout in `chains/soroban/poc/guide.md`.
5. Re-run with a new seed and `CHAINSEC_FUZZ_RUNS=256` for confidence once fixed.

## soroban pipeline steps

- Phase 0, recon: `testutils` dev-dependency present (scratch copy if not); note the crate name for
  `use <crate_name>::...`; `<crate>` and `<CORE>` as in the PoC guide.
- Phase 2, generation: write `.audit/soroban/fuzz/tests/chainsec_fuzz.rs`, one assertion (or test) per
  mined invariant, every test function named `chainsec_fuzz_<topic>`.
- Phase 3, run and fix: run the pack's `fuzz.run` line (the `run-test.sh` helper), then the loop above, at
  most 3 rounds per test.
- Phase 4, report: list each invariant as held / violated (with seed, run, step) / not testable (and
  why), and state the no-invariant-runner limitation above.
