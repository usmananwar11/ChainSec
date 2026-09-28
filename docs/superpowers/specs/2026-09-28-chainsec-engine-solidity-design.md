# ChainSec — Engine Extraction + Solidity Reference Pack (Design)

**Date:** 2026-09-28
**Status:** Approved in brainstorming, pending written-spec review
**Scope:** Sub-project 1 of 4 (engine + Solidity pack + cross-tool adapters). Cairo and Soroban packs get their own specs.

## 1. Goal

Build ChainSec: a multi-chain smart-contract audit skill pack with one chain-agnostic methodology engine and one "pack" per chain. Sub-project 1 extracts the engine from Krait (MIT, Zealynx Security, `~/krait`) with Solidity as the reference pack, and makes it run in Claude Code, OpenCode, Codex and Antigravity.

**Success criteria**

1. All script and structure tests pass in CI (no LLM required).
2. On 5 Krait shadow-audit targets, ChainSec recall ≥ Krait v8's recorded recall and **zero new false positives**, scored with one uniform rule (§8.2).
3. `install.sh` + a `--quick` audit of the fixture repo completes in OpenCode and in Antigravity, as well as in Claude Code.

**Non-goals (this sub-project)**

- Cairo, Soroban, Solana packs.
- Porting Krait's TypeScript CLI (`src/`), MCP servers (`mcp-servers/forge`, `mcp-servers/solodit`) or checklist plugin (`checklist/`).
- Native per-tool agent definition files (`.codex/agents/*.toml` etc.). Possible later if tool restrictions per agent prove valuable.
- Rewriting Krait's heuristics or modules. They are relocated and path-fixed, not rewritten, so the benchmark comparison measures the refactor alone.

## 2. Distribution

- Repo: `https://github.com/usmananwar11/ChainSec` (public, MIT).
- The repo is a Claude Code marketplace (`.claude-plugin/marketplace.json`) with one plugin, `chainsec`. Codex reads the same manifest (`codex plugin marketplace add usmananwar11/ChainSec`).
- `install.sh` installs the skills for tools that load skills from folders: copies or symlinks `plugins/chainsec/skills/*` into `.agents/skills/` (Codex, OpenCode, Cursor, Gemini, Antigravity), `.claude/skills/`, or the global equivalents (`--global`).
- `ATTRIBUTION.md` credits Krait / Zealynx Security (MIT). Krait's own `ATTRIBUTION.md` content (pashov, etc.) is carried over verbatim.

## 3. Repository layout

```
ChainSec/
├── .claude-plugin/marketplace.json
├── README.md  LICENSE  ATTRIBUTION.md  INSTALL.md
├── install.sh
├── .github/workflows/test.yml
├── plugins/chainsec/
│   ├── .claude-plugin/plugin.json
│   └── skills/
│       ├── chainsec/                       core skill (engine, packs, prompts, scripts)
│       │   ├── SKILL.md
│       │   ├── engine/
│       │   │   ├── pipeline.md             phase order; reads/writes per phase
│       │   │   ├── phases/{preflight,recon,detect,rescan,per-unit,state,verify,review,report}.md
│       │   │   ├── mindsets.md             attacker / accountant / spec auditor / edge-case
│       │   │   ├── kill-gates.md           gates A–H, DoS exception, Impact Premise
│       │   │   ├── verdicts.md             the single status/verdict vocabulary
│       │   │   ├── finding.schema.json
│       │   │   ├── facts.schema.json
│       │   │   ├── pack.schema.json
│       │   │   └── report-template.md
│       │   ├── prompts/                    subagent templates
│       │   │   └── {lens-detector,rescan,per-unit,state-auditor,critic,reviewer,reporter}.md
│       │   ├── runtimes/                   {claude-code,opencode,codex,antigravity,generic}.md
│       │   ├── domains/defi/               chain-agnostic DeFi modules + primers
│       │   │   ├── modules/*.md
│       │   │   └── primers/*.md
│       │   ├── chains/solidity/            the Solidity pack (§5)
│       │   └── scripts/
│       │       ├── detect-chain.sh
│       │       ├── score-risk.py
│       │       ├── validate-findings.py
│       │       └── merge-findings.py
│       ├── chainsec-audit/    SKILL.md  agents/openai.yaml
│       ├── chainsec-review/   SKILL.md  agents/openai.yaml
│       ├── chainsec-poc/      SKILL.md  agents/openai.yaml
│       ├── chainsec-fuzz/     SKILL.md  agents/openai.yaml
│       └── chainsec-init/     SKILL.md  agents/openai.yaml
├── benchmarks/solidity/{registry.yaml,scoring.md,results/}
└── tests/{run.sh, fixtures/, *.test.sh, test_*.py}
```

### 3.1 Skills

| Skill | Invocation (Claude Code) | Purpose |
|---|---|---|
| `chainsec` | not user-facing; loaded by entry skills | Core: engine, packs, prompts, scripts |
| `chainsec-audit` | `/chainsec:chainsec-audit [path] [--quick] [--chain X] [--fresh]` | Full pipeline |
| `chainsec-review` | `/chainsec:chainsec-review` | Second opinion on killed findings |
| `chainsec-poc` | `/chainsec:chainsec-poc <finding-id>` | PoC via the pack's harness |
| `chainsec-fuzz` | `/chainsec:chainsec-fuzz` | Invariant fuzzing via the pack's fuzz harness |
| `chainsec-init` | `/chainsec:chainsec-init` | Preflight in report mode: are the pack's tools installed? |

- All skill names carry the `chainsec-` prefix, because non-Claude tools put every skill in one flat folder and generic names (`audit`, `review`, `init`) would collide. Each `name` matches its folder (agentskills.io rule).
- `chainsec-audit`, `chainsec-poc` and `chainsec-fuzz` set `disable-model-invocation: true` (honored by Claude Code and Cursor). Every entry skill ships `agents/openai.yaml` with `allow_implicit_invocation: false` for Codex. OpenCode and Antigravity have no equivalent; the skill descriptions say "Run only when the user explicitly asks for a ChainSec audit."
- The core skill's description says it is a library loaded by the `chainsec-*` skills and should not be invoked directly.

### 3.2 Path resolution

- Shared instructions use paths **relative to the skill's own folder**. Entry skills reach the core as `../chainsec/...`. All four target tools resolve relative paths against the skill directory.
- `${CLAUDE_SKILL_DIR}` appears only in `runtimes/claude-code.md` as an optional hint.
- Scripts find their own location with `$(cd "$(dirname "$0")" && pwd)` and never depend on environment variables.
- Each entry skill's first step checks that `../chainsec/engine/pipeline.md` exists; if not, it stops and points the user to `INSTALL.md` (installing entry skills without the core is the one failure this layout introduces).

## 4. Engine

### 4.1 Pipeline

Per detected chain `C`, all state goes under `.audit/C/`:

| # | Phase | Reads | Writes |
|---|---|---|---|
| 0 | detect chains | repo | `.audit/chains.json` |
| 1 | preflight | `pack.json` | `preflight.json` (tools present/missing, `mode: full\|degraded`) |
| 2 | recon (extract) | source | `facts.json` via pack extractor |
| 3 | recon (score) | `facts.json`, `pack.json` | `risk.json` via `score-risk.py` |
| 4 | recon (LLM) | README/docs, facts, risk | `recon.md` (architecture, fund flows, trust boundaries, activated modules + evidence), `known-issues.md` |
| 5 | detect | recon outputs, heuristics, modules | `candidates/detect.json` |
| 6 | rescan | detect candidates as exclusion list | `candidates/rescan.json` (skipped if pass 1 found nothing above Info) |
| 7 | per-unit | units from pack clustering | `candidates/per-unit.json` |
| 8 | state | facts, recon | `candidates/state.json` |
| 9 | verify (critic) | all candidates | `verdicts.json` |
| 10 | validate | `verdicts.json` | pass / reject list (`validate-findings.py`) |
| 11 | report | verdicts | `report.md`, `findings.json` |

After all chains: `merge-findings.py` writes `.audit/report.md` and `.audit/findings.json`, with a separate "Boundary" section for cross-chain (e.g. bridge) findings.

- `--quick` skips phases 7 and 8.
- **Resume:** a phase is skipped when its output exists (and, for JSON outputs, validates against its schema); `--fresh` deletes `.audit/C/` first.
- `chainsec-review` reads `verdicts.json` and writes `review.json` (revived findings chained through `preconditions` / `postconditions`).

### 4.2 Methodology carried from Krait unchanged in substance

- 4 lenses (A access/state/governance, B value flow/economic, C external/cross-contract, D edge/math/standards) × 4 mindsets; consensus levels strong (3+) / moderate (2) / single (1).
- Question categories Q1–Q9, pass structure, anti-anchoring, Pass 3 sweep, detector pre-filter.
- State auditor: coupled-state pairs, mutation matrix, masking code.
- Kill gates A–H with the DoS exception, and the Impact Premise ("harm, not mechanism"). Gate thresholds stay in USD (Gate F: < $1 per tx; max_loss × iterations < $100). Packs convert via `value_unit`.
- Evidence tiers, root-cause consolidation, trust-assumption downgrade in the reporter.
- The 6-field methodology audit trail.

Solidity-specific content currently inside these files (e.g. SafeERC20 examples in Gate A, FP-3 OZ/Solmate, FP-7 Solidity 0.8 arithmetic, FP-8 view/staticcall) moves to `chains/solidity/fp-patterns.md` or `heuristics.md`. The engine files reference "the pack's fp-patterns" instead.

### 4.3 Verdict vocabulary (`verdicts.md`)

`status ∈ {candidate, verified, verified-conditional, downgraded, killed}`. This replaces Krait's three inconsistent sets (TP/LT/DOWNGRADE/FP/IE; VERIFIED/VERIFIED-CONDITIONAL/DOWNGRADE/KILLED; TRUE POSITIVE/LIKELY TRUE). The mapping from Krait's names is documented in `verdicts.md`.

### 4.4 `finding.schema.json`

JSON Schema (draft 2020-12). Fields:

- `id`, `chain`, `title`, `severity ∈ {Critical, High, Medium, Low, Info}`, `category`, `status`
- `locations[]`: `{file, line_start, line_end}`
- `discovery`: `{phase, lens, mindset, consensus}`
- `description`, `root_cause`, `recommendation`
- `harm`: `{who, loses_what, magnitude}` (the Impact Premise)
- `exploit_trace[]`: ordered steps
- `preconditions[]`, `postconditions[]`: each `{text, type ∈ STATE|ACCESS|TIMING|EXTERNAL|BALANCE}`
- `verdict`: `{gate, reason, evidence_tag, method}`
- `audit_trail`: `{step_execution, rules_applied, depth_evidence, missing_precondition, postconditions_created, who_benefits}`

Candidate files are JSON arrays of findings with `status: candidate`.

### 4.5 `validate-findings.py`

Python 3 standard library only (no jsonschema dependency). It implements the required-field checks itself, plus these hard rules for findings with `status ∈ {verified, verified-conditional}` and severity Medium or higher:

1. At least one location with `file` and `line_start`.
2. Non-empty `harm.who` and `harm.loses_what`.
3. Non-empty `exploit_trace`.

Exit code 0 = pass, 1 = rejects (a JSON list of `{id, rule}` goes to stdout). The critic gets one repair pass. Findings still invalid after it are set to `downgraded`, severity Low, with the rejection reason in `verdict.reason`.

### 4.6 `facts.schema.json`

Written by each pack's extractor:

```json
{
  "chain": "solidity",
  "mode": "compiler | regex",
  "units":          [{"name", "file", "loc", "parents": []}],
  "entry_points":   [{"unit", "name", "file", "line", "visibility", "mutability", "guards": []}],
  "auth_sites":     [{"unit", "file", "line", "kind"}],
  "storage_writes": [{"unit", "function", "file", "line", "target"}],
  "external_calls": [{"unit", "function", "file", "line", "kind"}],
  "value_transfers":[{"unit", "function", "file", "line", "asset"}],
  "counters": {"<file>": {"<pack-defined counter>": 0}}
}
```

`mode: regex` means lower confidence. The report states which mode ran.

### 4.7 `score-risk.py`

`score(file) = Σ counters[file][k] × risk_weights[k] + loc × loc_weight + novelty_bonus (file not under novelty_allowlist) + value_bonus (file has value_transfers)`. Weights and bonuses come from `pack.json`. Tiers follow Krait: top 5 files DEEP, next 10 STANDARD, the rest SCAN. If the codebase has ≤ 15 files, all are DEEP. Parents of DEEP units are promoted to at least STANDARD. The Solidity pack's weights reproduce Krait's formula exactly (ext_calls×5, state_writers×4, payable×4, assembly×6, unchecked×3, LOC×0.05, novel +15, value +10). Krait's "immaturity +10" is a judgment call, so it stays with the LLM recon step.

### 4.8 `detect-chain.sh`

For each `chains/*/pack.json`, it applies `detect.files` (paths or globs that must exist) and `detect.contains` (strings that must appear in those files). It prints `{"chains":[{"chain","root"}]}`, one entry per match root, so monorepos with several chains are supported. Requires `jq`.

### 4.9 `merge-findings.py`

Merges the per-chain `findings.json` files. It dedupes on (file, overlapping lines, root_cause), preferring the more severe entry, ranks by severity then consensus, and tags findings whose locations span more than one chain as `boundary`.

## 5. Solidity pack (`chains/solidity/`)

```
pack.json
recon/extract.sh           (from Krait ast-extract.sh; emits facts.json)
recon/slither-summary.sh   (optional tool adapter; from Krait)
recon/clustering.md        (inheritance-cluster strategy)
heuristics.md              (Krait heuristics-core + heuristics-extended, Solidity parts)
modules/*.md               (eip-standard-compliance, eip7702-delegation, account-abstraction-erc4337,
                            plus the Solidity-specific halves of oracle / token-flow / external-integration / erc4626)
primers/*.md               (proxy-upgrades, wallet-safe-aa)
fp-patterns.md             (Solidity FP patterns + gate overrides)
poc/                       (krait-poc SKILL + Foundry references)
fuzz/                      (Krait fuzzer, Foundry invariant tests)
patterns/*.yaml            (Krait patterns/solidity/*.yaml + schema.yaml)
```

`pack.json` (validated against `pack.schema.json`):

```json
{
  "chain": "solidity",
  "detect": {"files": ["foundry.toml", "hardhat.config.*", "**/*.sol"], "contains": []},
  "scope": {"include": ["src/**/*.sol", "contracts/**/*.sol"],
            "exclude": ["**/test/**", "**/mock*/**", "script/**", "lib/**", "out/**", "node_modules/**"]},
  "tools": {"required": ["forge", "jq"], "optional": ["slither"]},
  "extractor": "recon/extract.sh",
  "risk_weights": {"external_calls": 5, "state_writers": 4, "payable": 4, "assembly_blocks": 6, "unchecked_blocks": 3},
  "loc_weight": 0.05,
  "novelty_bonus": 15,
  "value_bonus": 10,
  "novelty_allowlist": ["lib/openzeppelin-contracts/**", "lib/solmate/**", "node_modules/@openzeppelin/**"],
  "unit_of_analysis": "inheritance_cluster",
  "clustering": "recon/clustering.md",
  "value_unit": {"name": "wei", "decimals": 18},
  "code_fence": "solidity",
  "modules_by_protocol": {
    "lending": ["../../domains/defi/modules/lending-liquidation-deep.md", "modules/oracle-chainlink.md"]
  },
  "poc":  {"framework": "foundry", "run": "forge test --match-test", "guide": "poc/SKILL.md"},
  "fuzz": {"framework": "foundry-invariant", "guide": "fuzz/SKILL.md"}
}
```

`modules_by_protocol` paths are relative to the pack folder. The full map is built during the port from Krait's recon module-trigger table.

### 5.1 Krait → ChainSec file mapping

- **→ engine:** rescan, state-auditor, reviewer, and the engine parts of recon / detector / per-contract / critic / reporter / preflight.
- **→ `domains/defi/`:** access-control-state, economic-design, multi-tx-attack, lending-liquidation-deep, amm-mev-deep, governance-voting, flash-loan-interaction, cross-chain-bridge (generic half), and primers defi-dex-amm, defi-lending, defi-staking-governance, gamefi-nft, bridge (generic parts). Mixed modules are split: the concept stays in the domain file, and Solidity specifics move to a pack module the domain file points to.
- **→ Solidity pack:** everything classified PACK in the analysis, plus the Solidity halves of the mixed files.
- **krait-poc references:** assertion-protocol, batch-triage, falsification-gate and fix-and-report → `engine/poc/` (generic PoC discipline). The Foundry-specific references → `chains/solidity/poc/`.

### 5.2 Krait defects fixed during the port

- Hardcoded `~/.claude/skills/krait/...` paths → relative paths.
- Broken references: `krait-recon/ast-extract.sh`, `recon/SKILL.md`, and the non-existent `/krait-recon`, `/krait-detect`, … commands.
- Three conflicting verdict vocabularies → one (§4.3).
- `ast-extract.sh`: the header says "Compiler-Verified" in regex mode, and regex mode counts view functions as state writers. Both are fixed, and the fixes are listed in the benchmark notes because they can shift risk tiers.
- Final JSON dropped harm, evidence and the audit trail → the full finding schema is kept end to end.

## 6. Cross-tool runtime adapters

The orchestrator works out which tool it is running in from **which subagent tool it has available** (more reliable than environment variables, which only Claude Code exposes to skills), then follows `runtimes/<tool>.md`:

| Tool | Detected by (tool available) | Dispatch |
|---|---|---|
| Claude Code | `Agent` (or `Task`) | 4 lenses in parallel; per-unit agents in parallel (max 8) |
| OpenCode | `task` (V1) or `subagent` (V2) | multiple calls in one message |
| Codex | Codex's subagent spawn tool | explicit subagent spawning (the skill asks for it, which Codex requires) |
| Antigravity | `invoke_subagent` | concurrent subagents |
| other / none | fallback | `generic.md`: run lenses/units **sequentially in this context**, writing the same files |

The exact tool names are verified per tool during implementation step 5 and recorded in each runtime file.

- Every subagent gets a filled-in template from `prompts/`: chain, lens or unit, the paths of its inputs, and **one output file it alone writes**. Parallel runs never write the same file.
- Krait never actually spawned subagents (its "parallel lenses" ran in sequence in one context). The sequential fallback therefore reproduces Krait's behavior, and parallel dispatch is an addition.
- Superpowers' reported OpenCode V2 rename (`task` → `subagent`) is unverified; `runtimes/opencode.md` covers both names.

## 7. Error handling

| Failure | Behavior |
|---|---|
| Core skill missing next to entry skill | Stop; point to INSTALL.md |
| Required tool missing | Preflight stops the run with the install command |
| Optional tool missing | Continue in `degraded` mode; the report says so |
| Extractor fails / no compiler | Fall back to `mode: regex`; the report says so |
| Validator rejects findings | One critic repair pass, then downgrade to Low with the reason |
| Subagent fails or returns invalid JSON | Re-run that unit once sequentially; then mark the phase `incomplete` in the report |
| Interrupted run | Resume from the first phase without valid output; `--fresh` restarts |

## 8. Testing and benchmarks

### 8.1 Automated (`tests/run.sh`, run in GitHub Actions)

- `detect-chain.sh`: Solidity-only fixture, mixed fixture (with a stub second pack), no-contracts fixture.
- `validate-findings.py`: one valid finding, and one fixture per rejection rule.
- `score-risk.py`: hand-computed expected scores and tiers, including the ≤ 15-file rule and parent promotion.
- `merge-findings.py`: dedup, ranking, boundary tagging.
- `extract.sh`: small Foundry fixture repo, expected `facts.json` in regex mode (and compiler mode when `forge` is present).
- Structure lint:
  - every relative path in any `.md` under `skills/` resolves;
  - each skill `name` matches its folder, is ≤ 64 characters of lowercase letters and hyphens, and has a description ≤ 1024 characters;
  - every pack validates against `pack.schema.json` and has the required files;
  - every entry skill has `agents/openai.yaml`.

Dependencies: bash, jq, python3 (standard library). `forge` is optional in CI.

### 8.2 Benchmark (manual, LLM-driven)

- `benchmarks/solidity/registry.yaml` is Krait's registry plus `chain: solidity` and `pack` fields.
- **One scoring rule:** EXACT = 1, PARTIAL = 0.5, FP = 0. Precision = TP/(TP+FP), Recall = TP/total_official. Krait's recorded v8 results for the chosen targets are re-scored with this rule (Krait applied partial credit inconsistently).
- **Acceptance:** 5 targets, a mix of sizes (small/medium) and protocol types, chosen from `methodology: v8` entries. Pass = ChainSec recall ≥ Krait recall on the aggregate **and** zero FPs that Krait did not also report. Results go in `benchmarks/solidity/results/`.

### 8.3 Cross-tool smoke tests

In Claude Code, OpenCode and Antigravity: `install.sh` (or plugin install), then `chainsec-audit --quick` on the fixture repo. The run passes if `.audit/solidity/findings.json` is produced and validates.

## 9. Build order within this sub-project

1. Repo scaffold, manifests, LICENSE/ATTRIBUTION, CI, structure lint.
2. Schemas + scripts (detect-chain, score-risk, validate, merge) with tests.
3. Solidity extractor port + fixture tests.
4. Engine phase files + prompts + verdicts, with Solidity specifics moved into the pack.
5. Entry skills + runtime adapters + install.sh.
6. Smoke tests in Claude Code, OpenCode, Antigravity.
7. Benchmark on 5 targets; fix regressions.

## 10. Later sub-projects (for context only)

2. Cairo pack (Caracal, snforge; felt252 semantics, L1 handlers, `replace_class_syscall`, account abstraction, component storage collisions). Reuse Trail of Bits and starknet-skills content with credit.
3. Soroban pack (require_auth scope and auth trees, storage type/TTL/archival, overflow-checks profile, panic vs Result, `update_current_contract_wasm` auth, SAC 7 decimals; Scout, stellar CLI, soroban-sdk testutils).
4. Optional: generated native agent files per tool; per-chain plugins if packs grow large.
