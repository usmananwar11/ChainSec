# ChainSec Cairo pack: design

**Scope:** Sub-project 2. A Starknet Cairo chain pack for the existing engine. Soroban, Cairo 0
(`%lang starknet`) and several roots per chain stay out of scope.

**Approach:** port, then adapt. `chains/cairo/` mirrors `chains/solidity/`. Its security knowledge is
ported, with credit, from keep-starknet-strange `cairo-auditor` (MIT). ChainSec writes the parts the
engine needs: `pack.json`, the extractor, the PoC and fuzz guides and the Cairo FP patterns.

## 1. Engine changes

- `engine/mindsets.md` names four EVM-only modules (EIP-7702, ERC-4337, ERC-4626, EIP standards).
  They are removed from the shared table and lens lists. Pack-only modules follow their own
  `**Inject into**` header, which the engine already treats as authoritative, so no new manifest
  field is needed.
- OpenZeppelin names in `domains/defi` (`nonReentrant`, `whenNotPaused`, `balanceOf(address(this))`)
  are rewritten as generic terms ("reentrancy guard", "pause guard", "the contract's own token
  balance"). Each pack's heuristics give the concrete forms.
- Multiple roots per chain stay deferred. A Scarb workspace's root `Scarb.toml` is one root.

## 2. Pack contents (`chains/cairo/`)

- `pack.json`:
  - chain `cairo`, prefix `CAIRO`, extension `.cairo`.
  - Detection marker `Scarb.toml` containing `starknet`.
  - Scope `src/**/*.cairo`, excluding `tests/`, `target/` and `*_test.cairo`.
  - Tools: `python3` and `scarb` required, `snforge` required for PoC/fuzz, `caracal` optional.
  - Value unit STRK (18 decimals), code fence `cairo`, unit of analysis `contract_module`.
- `recon/extract.sh` + `recon/extract.py`: a Python standard-library parser over comment-stripped
  source, aware of braces and attributes. It emits `facts.json` (mode `regex`) with:
  - units: modules, plus components as kind `component` and their embedding contracts as parents;
  - entry points: `#[external(v0)]` functions, functions in `#[abi(embed_v0)]` /
    `#[abi(per_item)]` impls, constructor, and `#[l1_handler]` functions;
  - auth sites: `get_caller_address` comparisons, `assert_only_*` and `only_owner` calls;
  - storage writes: `self.<x>.write(` / `.entry(..).write(`;
  - external calls: `call_contract_syscall`, `library_call_syscall`, `replace_class_syscall`,
    `deploy_syscall`, `send_message_to_l1_syscall`, dispatcher calls;
  - value transfers: ERC20 dispatcher `transfer` / `transfer_from`;
  - counters (`external_calls`, `state_writers`, `syscalls`, `l1_handlers`, `felt_arith`) per file.

  `scarb build` runs only when `scarb` is present, and records compile status. Missing `scarb` means
  the status is unknown, not an error.
- `recon/clustering.md`: one contract module plus the components it embeds. Caps of ~1500 LOC and
  8 clusters, the same as Solidity.
- `recon/caracal-summary.py`: an optional analyzer table, like the Slither summary.
- `heuristics.md`, `fp-patterns.md` (Cairo FP-3/7/8/9 and gate examples), `module-triggers.md`,
  `modules/` (L1↔L2 messaging, upgrades and `replace_class`, account abstraction, component storage,
  felt252 arithmetic, signatures and replay), `primers/`, and `patterns/` (the cairo-auditor
  vulnerability DB, ported with IDs unchanged), with `ATTRIBUTION.md`.
- `poc/guide.md`: snforge tests with cheatcodes (`start_cheat_caller_address`,
  `start_cheat_block_timestamp`) and fork testing.
- `fuzz/guide.md`: snforge `#[fuzzer]` property tests plus hand-written call-sequence tests. It says
  plainly that snforge has no Foundry-style stateful invariant runner.

## 3. Benchmark (`benchmarks/cairo/`)

- Regression suite: cairo-auditor's snippet cases, grouped by bug class into small Scarb fixture
  projects and run with `chainsec-audit --quick`. It measures which expected classes are detected
  and counts any flags on cases expected to be clean.
- Acceptance: 2–3 public Cairo audit contests with official High/Medium lists. The baseline is
  cairo-auditor run on the same targets. Pass: ChainSec recall ≥ baseline, and ChainSec FP ≤ baseline
  FP. Scoring reuses `tools/score_benchmark.py` rules (exact 1, partial 0.5).

## 4. Errors and degraded modes

- Without `scarb`, facts still come from source and the compile status is `unknown`.
- Without Caracal, tooling is degraded and the analyzer table is skipped.
- Cairo 0 source (`%lang starknet`) is detected by the extractor. It exits 3 with a message, and the
  pipeline stops that chain as failed.

## 5. Testing

- Unit tests for the extractor on fixtures (contract, component, l1_handler, Cairo 0 rejection).
- The pack lint validates `pack.json` and the files it references (existing `tools/lint_skills.py`).
- A port-coverage test checks that every ported cairo-auditor vulnerability-DB ID exists in
  `patterns/`.
- `tests/fixtures/cairo-basic`: a Scarb project with a planted bug, an `l1_handler` that does not
  check `from_address`.
- Quick smoke tests in Claude Code (and OpenCode when available).
