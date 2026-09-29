# ChainSec

Multi-chain smart-contract security audits for AI coding agents (Claude Code, OpenCode, Codex,
Antigravity, and other tools that load Agent Skills from a folder).

One audit engine, one pack per chain. Solidity today; Cairo and Soroban planned.

## What it does

`chainsec-audit` runs a fixed pipeline against your repository:

1. **Preflight** — checks the chain's required/optional tools and stops or degrades gracefully.
2. **Fact extraction** — compiler-based facts via `forge build` (Solidity). Regex mode applies
   when `forge build` fails or there is no `foundry.toml` (e.g. Hardhat-only projects); `forge`
   is still required.
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
| Cairo | Planned |
| Soroban | Planned |

## Supported tools

| Tool | Subagent dispatch |
|---|---|
| Claude Code | Parallel |
| OpenCode | Parallel |
| Antigravity | Parallel |
| Codex | Parallel (unverified — no local Codex install during v0.1 smoke tests) |
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

## Limitations

- One root per chain (v0.1): if a repository has several roots for the same chain, the audit
  stops and asks you to run `chainsec-audit <TARGET>/<root>` once per root.

## Security

Auditing runs the target's build toolchain (`forge build`, PoC and fuzz tests), which executes
code from the audited repository. Audit untrusted repositories in a sandbox or container.

## Repository layout

```
plugins/chainsec/
  .claude-plugin/plugin.json
  skills/
    chainsec/            # core: engine, prompts, runtimes, chain packs, domain knowledge
      engine/            # pipeline, phases, kill gates, verdicts, schemas, report template
      chains/solidity/   # the Solidity pack: heuristics, modules, patterns, recon, poc, fuzz
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
reuses Krait's methodology as-is; ChainSec's own benchmark acceptance run is still pending, so no
accuracy numbers are claimed here yet. See [ATTRIBUTION.md](ATTRIBUTION.md) for the full
attribution and third-party source list.

ChainSec is licensed under the [MIT License](LICENSE).
