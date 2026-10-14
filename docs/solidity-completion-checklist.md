# Solidity v0.1 completion checklist

The Solidity pack is implemented. Mark it **complete** only when every release item below is checked and the evidence is recorded in this repository. Cairo and Soroban are outside this checklist.

## Release items

- [ ] **Finalize the five-contest baseline.** Review and commit the pending Frankencoin denominator correction (20 to 21 official High/Medium findings), or document a different verified count. Make `benchmarks/solidity/baselines/krait-v8.json`, `benchmarks/solidity/scoring.md`, the scorer test, and `docs/PROGRESS.md` agree on the resulting aggregate target. The current working-tree calculation is 11.5 / 67 = **17.16%** recall, with zero baseline false positives.

- [ ] **Make the acceptance command require all five targets.** `tools/score_benchmark.py compare` currently prints `PASS` for PoolTogether alone because it compares only shared IDs. Add a full-acceptance mode (or change the command) that fails when any of PoolTogether, InitCapital, GoodEntry, Arcade, or Frankencoin is missing, duplicated, or has an inconsistent official total. Keep an explicit way to compare one target during development. Cover the missing-target case with a test.

- [ ] **Run the remaining four full Solidity benchmarks.** Audit InitCapital, GoodEntry, Arcade, and Frankencoin in fresh agent sessions at the pinned contest commits and scopes. Record each run's ChainSec commit, runtime/model, facts mode, complete phase artifacts, validated final findings, and result under `benchmarks/solidity/results/`. Grade against the official High/Medium findings only after the audit output is final. PoolTogether already has a recorded result.

- [ ] **Pass the five-target acceptance threshold.** Run the full-acceptance comparison. The aggregate ChainSec recall must be at least the finalized Krait v8 baseline and there must be **zero new false positives**. If it fails, fix the identified detection or verification issue, then run and grade fresh audits without feeding the official answers into the auditor. Record the final comparison and any limitations in the benchmark documentation.

- [ ] **Repeat the Claude Code and OpenCode quick smoke tests after the 2026-10-13 fixes.** The earlier passes predate the scope-count and quick-report changes. On a fresh copy of `tests/fixtures/solidity-basic`, each run must produce a valid `.audit/solidity/findings.json`, report the unrestricted `sweep()` issue, and write `.audit/report.md`. Confirm preflight counts the two scoped source files and the quick report says per-unit and state analysis were skipped. Record versions, dispatch behavior, result, and elapsed time in `docs/smoke-tests.md`.

- [ ] **Pass the Antigravity quick smoke test.** Confirm the documented workspace install path loads all six skills, run `chainsec-audit --quick` on a fresh fixture copy, check the same four artifact/finding criteria, and record the actual subagent dispatch behavior. Correct `INSTALL.md` and the runtime adapter if the documented path or invocation is wrong.

- [ ] **Pass the Codex quick smoke test.** Codex CLI is available locally now. Verify the documented plugin marketplace command and a plain-skills install, then run the fixture audit and check the same criteria. Record the actual delegation tool and whether parallel dispatch works; update `INSTALL.md`, `README.md`, and `runtimes/codex.md` to match the observed behavior.

- [ ] **Exercise the other Solidity entry skills once on a fixture.** Confirm `chainsec-init` reports tool readiness, `chainsec-review` writes a valid review, `chainsec-poc` builds and runs a Foundry proof for a verified finding, and `chainsec-fuzz` runs a generated invariant test. Record any limitations. These are advertised Solidity workflows, although the original v0.1 acceptance criteria focused on full audit benchmarks and quick audit smoke tests.

- [ ] **Close the release evidence.** Run `bash tests/run.sh` and the full-acceptance comparison on the final tree; check CI; update `docs/PROGRESS.md`, `docs/smoke-tests.md`, and README status so claims match the recorded results. Commit the benchmark results and smoke-test evidence. The final status must not rely on the current single-target `PASS`.
