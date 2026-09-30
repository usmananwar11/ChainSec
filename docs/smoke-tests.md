# Cross-tool smoke tests (v0.1)

Target: `tests/fixtures/solidity-basic` (planted bug: `Vault.sweep()` has no access control).
Command: `chainsec-audit --quick`, run in a scratch copy with skills installed by `install.sh`.

**Pass criteria:**
1. `.audit/solidity/findings.json` exists.
2. `validate-findings.py` accepts it (exit 0).
3. A finding points at `sweep()` in `src/Vault.sol`.
4. `.audit/report.md` exists.

| Tool | Version / model | Install | Result | Time | Notes |
|---|---|---|---|---|---|
| Claude Code | 2.1.285, default model, headless `claude -p "/chainsec-audit --quick"` | `install.sh --tool claude` (project `.claude/skills`) | **PASS** | 21m 27s | Compiler-mode facts; Pass 1 + lens A–D candidate files written by subagents; preflight `degraded` (no slither) |
| OpenCode | 1.18.32, `opencode/big-pickle` (free), `opencode run` | `install.sh --tool opencode` (project `.opencode/skills`) | **PASS** | 1h 44m | Same pipeline artifacts; phases dispatched as subagents per the transcript. The log doesn't show whether they ran in parallel |
| Antigravity | — | `install.sh --tool antigravity` (workspace `.agents/skills`) | pending (user) | — | — |
| Codex | not installed locally | — | not run | — | `runtimes/codex.md` still unverified |

## What both runs found

The two runs found the same three High+ issues:

- **SOL-002 — `sweep()` has no access control (planted bug).** Critical in Claude Code, High in OpenCode.
- **SOL-001 (Critical) — ETH and the token share one `balances` ledger.** ETH credited by `depositEth()` can be withdrawn as tokens through `withdraw()`, and `sweep()` refunds the attacker's ETH. This is a real fixture bug that wasn't planted on purpose.
- **SOL-003 — an `unchecked` decrement wraps `totalDeposits` and bricks `deposit()`.** Claude Code downgraded it to Medium (no funds lost); OpenCode kept it High as `verified-conditional`.

Neither run reported Low findings, as the report rule requires. The kill gates removed unchecked ERC20 returns, fee-on-transfer, dead `setFee`, and similar candidates.

## Issues observed

- The report's Methodology section lists "State Analysis" in `--quick` runs, where that phase is skipped.
- In the maintainer's Claude Code environment, a local hook blocked the reporter subagent from writing `report.md`; the orchestrator saved the returned text itself. The hook is not part of ChainSec.
- `preflight.json` `scope_files` counted 3 (it included `test/VaultTest.sol`), while the pack scope has 2 files. The preflight `find` ignores pack `scope.exclude`.
- The OpenCode default model (`opencode-go/qwen3.8-max`) requires an OpenCode Go subscription; the run used a free model via `-m`.
