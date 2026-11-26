# ChainSec

Multi-chain smart-contract security audits for AI coding agents (Claude Code, OpenCode, Codex,
Antigravity, and other tools that load Agent Skills from a folder).

One audit engine, one pack per chain. Solidity, Starknet Cairo (preview) and Stellar Soroban (preview) today.

## What it does

`chainsec-audit` runs a fixed pipeline against your repository:

1. **Preflight** — checks the chain's required/optional tools and stops or degrades gracefully.
2. **Fact extraction** — compiler-based facts via `forge build` (Solidity). Regex mode applies
   when `forge build` fails or there is no `foundry.toml` (e.g. Hardhat-only projects); `forge`
   is still required. Soroban: a source parser builds the facts, and a time-limited
   `cargo check` records whether the project compiles.
3. **Deterministic risk scoring** — ranks files by risk from the extracted facts.
4. **Recon** — protocol summary, actors, invariants, known issues.
5. **Detection** — an unrestricted Pass 1 sweep, then four parallel lenses (A access/state, B
   value/economic, C external, D edge/math), a consensus merge, and a Pass 3 "what's missing"
   sweep.
6. **Rescan** — a further pass over the merged candidates.
7. **Per-unit deep dives** — one focused pass per cluster of units (skipped with `--quick`).
8. **State-inconsistency analysis** — cross-function/cross-transaction state bugs (skipped with
   `--quick`).
9. **Verification** — kill gates A–H plus the Impact Premise, applied to every candidate.
10. **Code-enforced validation** — `scripts/validate-findings.py` checks the verdicts against the
    finding schema before anything is reported.
11. **Report** — a markdown report and a `findings.json` per chain, merged across chains.

## Supported chains

| Chain | Status |
|---|---|
| Solidity | Supported |
| Cairo (Starknet) | Preview: Cairo 1+, benchmark in progress |
| Soroban (Stellar) | Preview: soroban-sdk ≥ 20; smoke test and contest benchmark pending ([details](#soroban-pack-preview)) |

## Supported tools

| Tool | Subagent dispatch |
|---|---|
| Claude Code | Parallel |
| OpenCode | Parallel |
| Antigravity | Parallel |
| Codex | Parallel |
| Others (Cursor, Gemini CLI, generic) | Sequential, in-conversation |

## Quick start

In Claude Code:

```
/plugin marketplace add usmananwar11/ChainSec
/plugin install chainsec@chainsec
/chainsec:chainsec-audit
```

For every other tool, and for details on each runtime, see [INSTALL.md](INSTALL.md).

## Commands

| Skill | Purpose |
|---|---|
| `chainsec-audit` | Run a full audit (recon, detection, state analysis, verification, report). |
| `chainsec-review` | Second opinion on findings the audit killed. |
| `chainsec-poc` | Build and run an executable proof-of-concept for a finding. |
| `chainsec-fuzz` | Extract invariants and generate/run invariant fuzz tests. |
| `chainsec-init` | Check whether a project is ready for a ChainSec audit. |

## Output

Audit output lives under `.audit/` in the target repository:

```
.audit/
  chains.json           # detected chains
  report.md             # combined report (all chains)
  findings.json         # merged findings (all chains)
  <chain>/
    preflight.json
    facts.json
    risk.json
    recon.md
    known-issues.md
    candidates/          # per-phase intermediate findings
    verdicts.json        # post-verification, post-validation findings
    report.md
    findings.json
    review.json          # written by chainsec-review
    fuzz/                 # written by chainsec-fuzz
```

## Benchmark vs Krait (Solidity)

ChainSec and Krait v8 were scored on the same five Code4rena contests, graded against the
official High/Medium findings (exact = 1, partial = 0.5). ChainSec found more of the official
bugs: **12.5 / 67 (18.66%) recall vs Krait's 11.5 / 67 (17.16%)**, with 12 exact matches against
Krait's 10.

| Target | Official H/M | Krait recall | ChainSec recall | Krait FP | ChainSec FP |
|---|---:|---:|---:|---:|---:|
| PoolTogether | 9 | 11.11% | 11.11% | 0 | 0 |
| InitCapital | 15 | 3.33% | **20.00%** | 0 | 0 |
| GoodEntry | 14 | 35.71% | 28.57% | 0 | 4 |
| Arcade | 8 | 31.25% | 0.00% | 0 | 0 |
| Frankencoin | 21 | 11.90% | **21.43%** | 0 | 2 |
| **Total** | **67** | **17.16%** | **18.66%** | **0** | **6** |

The gain comes from InitCapital and Frankencoin. Grades come from agent review against
the official reports and are borderline in places. See
[benchmarks/solidity/scoring.md](benchmarks/solidity/scoring.md) for the method and the
per-finding reasons. To reproduce the comparison:

```
python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results
```

## Soroban pack (preview)

The Soroban pack (`chains/soroban/`) audits Stellar smart contracts written with `soroban-sdk`.

- **Detection:** a project is Soroban when a `Cargo.toml` names `soroban-sdk`. A workspace whose
  root `Cargo.toml` names it counts as one root.
- **Facts:** entry points, `require_auth` guards (followed through helper functions), storage
  writes by tier, cross-contract calls, upgrades and token transfers. A
  `unguarded_mutators` counter flags state-changing entry points with no auth check.
- **Knowledge:** 34 vulnerability patterns, 23 from CoinFabrik Scout and 11 from Stellar's
  security guide. It also has Soroban heuristics, false-positive rules (for example, the host
  blocks reentrancy into a contract already on the call stack), six modules and a primer for
  EVM auditors.
- **PoC and fuzz:** tests use `soroban-sdk` testutils through `poc/run-test.sh`. The runner never
  leaves changes in your project: it restores `Cargo.lock` byte for byte, removes the files it
  added and builds in `.audit/soroban/target`. The test templates also turn off snapshot
  writes. Fuzzing uses seeded
  stateful invariant tests, because `soroban-sdk` has no Foundry-style invariant runner.
- **Optional:** Scout (`cargo-scout-audit`) adds a static-analysis signal table during recon.
- **Status:** these checks are done:
  - unit tests;
  - a fixture with a planted missing-`require_auth` bug, which both the PoC and the fuzz
    harness detect;
  - a 92-case regression suite built from Scout's test cases.

  Still pending: the Claude Code smoke test, the contest benchmark (Code4rena Blend v2 and K2,
  see `benchmarks/soroban/registry.yaml`) and a first real Scout run, which confirms its
  output format.

## Limitations

- One root per chain (v0.1): if a repository has several roots for the same chain, the audit
  stops and asks you to run `chainsec-audit <TARGET>/<root>` once per root. For Soroban this
  happens when only the member crates, not the workspace root, name `soroban-sdk`.
- Soroban facts come from a source parser, not the compiler. A `view` label or a non-empty guard
  is a hint to check in the code, never proof (see "Extractor limits" in
  `chains/soroban/heuristics.md`).

## Security

Auditing runs the target's build toolchain (`forge build`, `cargo check` for Soroban, PoC and
fuzz tests), which executes
code from the audited repository. Audit untrusted repositories in a sandbox or container.

## Repository layout

```
plugins/chainsec/
  .claude-plugin/plugin.json
  skills/
    chainsec/            # core: engine, prompts, runtimes, chain packs, domain knowledge
      engine/            # pipeline, phases, kill gates, verdicts, schemas, report template
      chains/solidity/   # the Solidity pack: heuristics, modules, patterns, recon, poc, fuzz
      chains/soroban/    # the Soroban (Stellar) pack, same layout plus poc/run-test.sh
      domains/defi/      # chain-agnostic DeFi domain knowledge
      prompts/           # subagent prompt templates
      runtimes/          # per-tool subagent dispatch instructions
    chainsec-audit/
    chainsec-review/
    chainsec-poc/
    chainsec-fuzz/
    chainsec-init/
tools/lint_skills.py
tests/
install.sh
```

## Development

```
bash tests/run.sh
```

runs the skill lint and the full test suite.

## Attribution and license

ChainSec's engine and Solidity pack are derived from **Krait** by Zealynx Security (MIT). v0.1
reuses Krait's methodology as-is. See [Benchmark vs Krait](#benchmark-vs-krait-solidity) for how
the two compare on the same contests. See [ATTRIBUTION.md](ATTRIBUTION.md) for the full
attribution and third-party source list.

The Soroban pack ports material from two sources: CoinFabrik's
[Scout for Soroban](https://github.com/CoinFabrik/scout-soroban) (MIT) and Stellar's
[stellar-dev-skill](https://github.com/stellar/stellar-dev-skill) (Apache-2.0, modified by
ChainSec). The credits and license texts are in
[plugins/chainsec/skills/chainsec/chains/soroban/ATTRIBUTION.md](plugins/chainsec/skills/chainsec/chains/soroban/ATTRIBUTION.md).

ChainSec is licensed under the [MIT License](LICENSE).
