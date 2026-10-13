# ChainSec — Progress

_Last updated: 2026-10-13_

ChainSec is a set of smart-contract audit skills: one audit engine shared by every chain, plus a "pack" for each chain. It runs in Claude Code, OpenCode, Codex and Antigravity. The engine and the Solidity pack are derived from [Krait](https://github.com/zealynx/krait) by Zealynx Security (MIT).

- Repo: https://github.com/usmananwar11/ChainSec (branch `main`)
- Design spec: [`docs/superpowers/specs/2026-09-28-chainsec-engine-solidity-design.md`](superpowers/specs/2026-09-28-chainsec-engine-solidity-design.md)
- Implementation plan: [`docs/superpowers/plans/2026-09-28-chainsec-engine-solidity.md`](superpowers/plans/2026-09-28-chainsec-engine-solidity.md)
- Smoke-test log: [`docs/smoke-tests.md`](smoke-tests.md)

## At a glance

| Area | Status |
|---|---|
| Sub-project 1: engine + Solidity pack + support for other tools (v0.1) | Built, reviewed and merged to `main` |
| Automated tests | 100 tests passing; structure lint clean; CI on GitHub Actions (with Foundry) |
| Smoke test, Claude Code | Passed |
| Smoke test, OpenCode | Passed |
| Smoke test, Antigravity | Pending (run by the user) |
| Smoke test, Codex | Not run (not installed locally) |
| Benchmark against Krait (5 contests) | Pending (needs the user's go-ahead) |
| Sub-project 2: Cairo pack | Planned |
| Sub-project 3: Soroban pack | Planned |

---

## Done

### Sub-project 1 — the engine, the Solidity pack and support for other tools (v0.1)

Built in 15 tasks. Each task was done by an implementer subagent and then checked by a reviewer for spec compliance and code quality. A final review of the whole branch came next, followed by two rounds of fixes. The branch was then merged to `main` at `0b416cd`.

**Packaging and support for other tools**
- The repo is a Claude Code plugin marketplace (`chainsec@chainsec`). Codex can read the same manifest.
- There is one core skill (`chainsec`) and five entry skills: `chainsec-audit`, `chainsec-review`, `chainsec-poc`, `chainsec-fuzz` and `chainsec-init`. Each entry skill ships a Codex `agents/openai.yaml` that turns off automatic invocation.
- `install.sh` copies or symlinks the skills into `.agents/skills`, `.claude/skills` or `.opencode/skills`, or into the matching global folders. It refuses to delete anything outside its own skill folders.
- Runtime adapters for Claude Code, OpenCode, Codex and Antigravity, plus a generic one-step-at-a-time fallback for tools without subagents.
- Every path is relative to its skill folder, so the skills don't depend on Claude-only environment variables. The lint enforces this.

**Engine** (`plugins/chainsec/skills/chainsec/engine/`)
- `pipeline.md` runs the audit end to end. It covers chain detection, per-chain phases, resuming and invalidation, validation and repair, merging across chains, dispatch, failure handling and the final message.
- 9 phase files: preflight, recon, detect, rescan, per-unit, state, verify, review and report. Phases pass JSON to each other.
- Supporting files:
  - `kill-gates.md`: Gates A–H, the DoS exception, the Impact Premise and the detection pre-filter.
  - `mindsets.md`: 4 lenses × 4 mindsets.
  - `verdicts.md`: one vocabulary for finding statuses, plus a mapping from Krait's old terms.
  - `report-template.md`.
  - `fuzz.md`.
  - `poc/`: the method for writing proof-of-concept exploits.
- JSON schemas for findings, code facts and pack manifests.

**Scripts** (Python 3 standard library only)
- `detect-chain.py`: works out which chain packs apply to a repo, and where.
- `score-risk.py`: ranks files by risk using each pack's weights.
- `validate-findings.py`: enforces in code that every verified Medium-or-higher finding has a file and line, a harm statement and an exploit trace. It also catches duplicate IDs and can automatically downgrade findings that fail.
- `merge-findings.py`: merges findings across chains, removes duplicates, ranks them and tags findings that cross chain boundaries.

**Subagents**
- 8 prompt templates: pass1-detector, lens-detector, rescan, per-unit, state-auditor, critic, reviewer and reporter.

**DeFi domain layer** (`domains/defi/`)
- 17 chain-agnostic modules and primers, plus domain heuristics and module triggers. Future Cairo and Soroban packs reuse these.

**Solidity pack** (`chains/solidity/`)
- `pack.json` (tools, scope, risk weights, module mapping, PoC and fuzz settings).
- A facts extractor that reads the compiler AST through `forge build --ast` and falls back to regex when that isn't possible.
- 18 Solidity-specific modules and primers, the heuristics, false-positive patterns, module triggers and clustering rules.
- A Slither summary script.
- A Foundry PoC guide with references, a Foundry fuzz guide and 14 pattern files.

**Benchmark tooling** (`benchmarks/solidity/`)
- A registry of 50 contests taken from Krait.
- A single scoring rule: exact match = 1, partial = 0.5.
- Krait's v8 results re-scored under that rule. Aggregate recall is **17.42%**, with **0** false positives.
- `tools/score_benchmark.py` runs the PASS/FAIL comparison.

**Proof that nothing was lost from Krait**
- A test checks that all **91** Krait heuristic and false-positive IDs are still present.
- The reviewers also checked every port line by line against the Krait source.

### Decisions made during the build (user-approved)

| Decision | Why |
|---|---|
| Work on a feature branch, then merge to `main` | Keeps `main` clean |
| Regex mode detects tuple-assignment storage writes, e.g. `(a, b) = (...)` | Common in AMM code; these writes were silently missed before |
| The Slither summary was ported from bash + `jq` to Python | ChainSec scripts don't depend on `jq` |
| The PoC guide runs `forge` directly | ChainSec doesn't ship Krait's forge MCP server |
| Detection runs Pass 1 once, unrestricted, then the 4 lenses in parallel | The same structure as Krait, which keeps recall up and the consensus count honest |
| Second-opinion findings are capped at `verified-conditional` | Krait's own rule: a second opinion flags a finding for a human; it never verifies it |
| v0.1 audits one root per chain | Multiple roots of the same chain would collide; the audit stops and asks for a path instead |
| Merged to `main` before the benchmark | So people can try it sooner; the benchmark runs on `main` |

### Smoke tests

The test project is `tests/fixtures/solidity-basic`, which contains a planted bug: anyone can call `sweep()`. Each run was `chainsec-audit --quick`.

| Tool | Result | Time | Notes |
|---|---|---|---|
| Claude Code 2.1.285 | **PASS** | 21 min | Found the planted bug, plus a real bug in the fixture we hadn't planted (ETH and the token share one balance ledger) |
| OpenCode 1.18.32 (free model `opencode/big-pickle`) | **PASS** | 1 h 44 min | Same three findings as Claude Code |

---

## Planned

### Finish v0.1

1. **Antigravity smoke test (user).** The test folder is ready at `~/chainsec-smoke-ag`. Run `/chainsec-audit --quick` and report:
   - whether the skills were found;
   - whether subagents ran in parallel;
   - the contents of `.audit/`.

   This also checks whether Antigravity reads skills from `.agents/skills`, a path still marked unverified in INSTALL.md.
2. **Benchmark (Task 17).** Run 5 full audits against the Code4rena contests Krait was scored on: PoolTogether, InitCapital, GoodEntry, Arcade and Frankencoin. Grade each against the official findings, then run `tools/score_benchmark.py compare`.
   - **Pass bar:** aggregate recall of at least 17.42% and zero false positives.
   - **Cost:** probably 1–3 hours of agent time per contest. It's worth starting with PoolTogether (648 lines).
3. **Small fixes the smoke tests turned up:**
   - In `--quick` runs, the report's Methodology section still lists "State Analysis".
   - Preflight's `scope_files` count includes `test/`, because it ignores the pack's `scope.exclude`.
4. **Minor items from the final review**, deferred and fine to leave for now:
   - a stale top-level report is left behind when no chain produces findings;
   - the runtime detection row is ambiguous in Claude Code sessions without an Agent tool;
   - the rescan prompt says "exactly one line" but then allows `REINFORCED:` lines after it;
   - PoC test files are named inconsistently;
   - an older `preflight.json` has no `quick` key, and nothing says how to treat it;
   - stale analyzer output is left behind when recon re-runs;
   - re-running rescan or per-unit appends duplicate warnings;
   - `install.sh` only refuses an exact match between destination and source, not a destination inside the source;
   - `--downgrade` can still rewrite a finding that also has schema errors.
5. **Unverified paths:** the Codex runtime and the Codex plugin install command. Codex isn't installed locally.

### Design questions to settle before the second pack

- `engine/mindsets.md`'s module-to-lens table names four EVM-only modules (EIP-7702, ERC-4337, ERC-4626, EIP standards). Move them into a section supplied by the pack.
- A few OpenZeppelin-origin names (`nonReentrant`, `whenNotPaused`, `balanceOf(address(this))`) are still in the DeFi domain files. Decide whether they count as generic vocabulary or move to the pack.
- Support several roots per chain, e.g. `.audit/<chain>/<root>/`, for monorepos.

### Sub-project 2 — Cairo pack (next)

Write its own spec, then plan, then build, reusing the engine and the DeFi domain layer.
- **Tools:** Caracal (static analysis) and snforge (tests and fuzzing).
- **Facts extractor:** reads Sierra or the AST into `facts.json`.
- **What to cover:**
  - felt252 vs u256 overflow semantics;
  - `#[l1_handler]` functions must check `from_address`;
  - access control on `replace_class_syscall`;
  - account abstraction (`__validate__` / `__execute__`);
  - storage-slot collisions between components.
- **Reuse, with credit:** Trail of Bits' Cairo scanner, and starknet-skills' `cairo-auditor`.
- **Benchmark:** `benchmarks/cairo/` built from known Cairo audit reports.

### Sub-project 3 — Soroban pack (for the Stellar work)

- **Tools:** CoinFabrik Scout, the `stellar` CLI and the soroban-sdk test utilities. The facts extractor uses `syn`.
- **What to cover:**
  - missing or wrong-address `require_auth`;
  - the scope of `require_auth_for_args`;
  - auth trees across sub-invocations;
  - instance vs persistent vs temporary storage, and TTL extension and archival;
  - instance storage bloat;
  - `overflow-checks` in the release profile;
  - `panic!` vs `Result` errors;
  - auth on `update_current_contract_wasm`;
  - SAC tokens use 7 decimals.
- **Benchmark:** `benchmarks/soroban/`.

### Later (optional)

- Generate each tool's native agent files from one source, e.g. `.codex/agents/*.toml`, if per-agent tool limits prove worth having.
- Split into one plugin per chain if the packs get large.
- A Solana pack.
