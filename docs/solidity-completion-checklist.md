# Solidity v0.1 completion checklist

The Solidity pack is implemented. Mark it **complete** only when every release item below is checked and the evidence is recorded in this repository. Cairo and Soroban are outside this checklist.

## Release items

- [x] **Finalize the five-contest baseline.** Completed 2026-10-14. Reviewed the Frankencoin denominator correction committed in `81bad63` against the official report: 6 High + 15 Medium = **21** findings. The baseline JSON, [scoring evidence](../benchmarks/solidity/scoring.md#finalized-five-contest-baseline--2026-10-14), scorer regression test, and `docs/PROGRESS.md` agree on **11.5 / 67 = 17.16%** recall, with **zero baseline false positives**. Verified with the baseline scoring command and `python3 -m unittest discover -s tests -p 'test_score_benchmark.py' -v`.

- [x] **Make the acceptance command require all five targets.** Completed 2026-10-14. `tools/score_benchmark.py compare` now requires PoolTogether, InitCapital, GoodEntry, Arcade, and Frankencoin in both inputs, rejects duplicate targets, and checks each official total against the finalized values. Use `--target <id>` for an explicitly labeled development comparison. Regression tests cover missing targets in either input, PoolTogether alone, duplicate entries, incorrect totals (including matching incorrect totals), and recall/FP thresholds. The current results correctly fail full acceptance because four runs remain pending; the explicit PoolTogether comparison passes.

- [x] **Run the remaining four full Solidity benchmarks.** Graded 2026-10-17 against the official High/Medium lists after the outputs were frozen; results are in `benchmarks/solidity/results/`. InitCapital 3 exact / 12 missed / 0 FP; GoodEntry 4 exact / 4 FP; Arcade 0 found (no final findings) / 0 FP; Frankencoin 4 exact + 1 partial / 2 FP. Caveat: the answer-isolation protocol was not independently certified (see [execution evidence](benchmark-remaining-four.md)). Original task: Audit InitCapital, GoodEntry, Arcade, and Frankencoin in fresh agent sessions at the pinned contest commits and scopes. Record each run's ChainSec commit, runtime/model, facts mode, complete phase artifacts, validated final findings, and result under `benchmarks/solidity/results/`. Grade against the official High/Medium findings only after the audit output is final. PoolTogether already has a recorded result.

- [ ] **Pass the five-target acceptance threshold.** Run the full-acceptance comparison. The aggregate ChainSec recall must be at least the finalized Krait v8 baseline and there must be **zero new false positives**. If it fails, fix the identified detection or verification issue, then run and grade fresh audits without feeding the official answers into the auditor. Record the final comparison and any limitations in the benchmark documentation.

- [x] **Repeat the Claude Code and OpenCode quick smoke tests after the 2026-10-13 fixes.** Ran 2026-10-16; recovered and recorded 2026-10-17. Both runs pass findings validation, report `sweep()`, produce `.audit/report.md`, count two scoped files, and mark per-unit/state analysis skipped. [Run records, dispatch and timing](smoke-tests.md#post-fix-reruns--2026-10-16-recorded-2026-10-17). Claude Code is 2.1.300; OpenCode's exact version/model was not captured and is explicitly recorded as a metadata limitation.

- [ ] **Pass the Antigravity quick smoke test.** Confirm the documented workspace install path loads all six skills, run `chainsec-audit --quick` on a fresh fixture copy, check the same four artifact/finding criteria, and record the actual subagent dispatch behavior. Correct `INSTALL.md` and the runtime adapter if the documented path or invocation is wrong.

- [ ] **Pass the Codex quick smoke test.** Codex CLI is available locally now. Verify the documented plugin marketplace command and a plain-skills install, then run the fixture audit and check the same criteria. Record the actual delegation tool and whether parallel dispatch works; update `INSTALL.md`, `README.md`, and `runtimes/codex.md` to match the observed behavior.

- [x] **Exercise the other Solidity entry skills once on a fixture.** Done 2026-10-17 with Claude Code on a fresh fixture copy ([evidence](smoke-tests/2026-10-17/entry-skills/)): `chainsec-init` reported tool readiness; `chainsec-poc SOL-002` built and ran a Foundry PoC (`[POC-PASS]`, falsification sweep); `chainsec-fuzz` ran 7 invariant tests (3 violated); `chainsec-review` wrote `review.json` (1 revived finding). The first two review runs failed because step 1 let the model resolve `../chainsec` against the project folder; `chainsec-review/SKILL.md` now says to resolve it from the skill's folder, and the third run passed. Limitations: Claude Code only, no forge-std in the fixture so tests use a local Vm interface, and the review fix was verified in one run. Original task: Confirm `chainsec-init` reports tool readiness, `chainsec-review` writes a valid review, `chainsec-poc` builds and runs a Foundry proof for a verified finding, and `chainsec-fuzz` runs a generated invariant test. Record any limitations. These are advertised Solidity workflows, although the original v0.1 acceptance criteria focused on full audit benchmarks and quick audit smoke tests.

- [ ] **Close the release evidence.** Run `bash tests/run.sh` and the full-acceptance comparison on the final tree; check CI; update `docs/PROGRESS.md`, `docs/smoke-tests.md`, and README status so claims match the recorded results. Commit the benchmark results and smoke-test evidence. The final status must not rely on the current single-target `PASS`.

## Status update — 2026-10-17 (later)

- **Acceptance fails on false positives.** `compare` now prints aggregate recall 18.66% vs
  baseline 17.16% (12.5 / 67), but ChainSec has **6 false positives** (GoodEntry 4,
  Frankencoin 2) against the required zero. The item stays unchecked. Per its text, the next
  step is to fix the identified verification issue and run *fresh* audits without feeding in
  the official answers; that has not been started.
- **Codex smoke test is blocked, not failed.** `codex exec '$chainsec-audit --quick'` on a plain
  `install.sh --tool agents` install discovered the skill and passed preflight, then the account
  hit Codex's usage limit ("try again at 4:57 PM"). No delegation behavior was observed.
  Partial evidence: [`docs/smoke-tests/2026-10-17/codex/`](smoke-tests/2026-10-17/codex/).
  `INSTALL.md`/`README.md`/`runtimes/codex.md` were not changed beyond what was already recorded.
- **Antigravity is not tested.** The Antigravity IDE (1.107.0) is installed, but the audit has
  to run from its GUI agent; there is no headless command to drive from here.

## Evidence recovery — 2026-10-17

- The four remaining full audits have run, and their artifacts, scope overrides,
  launch records and normalized run metadata are now preserved under
  `benchmarks/solidity/artifacts/`. See [execution evidence](benchmark-remaining-four.md).
  All four findings files validate. The benchmark item remains unchecked because
  provenance review and official High/Medium grading into `results/` are outstanding.
- Claude Code and OpenCode post-fix smoke outputs are preserved under
  `docs/smoke-tests/2026-10-16/`; the rerun item is now checked, with OpenCode's missing
  version/model metadata explicitly documented.
- Codex installation is recorded in `INSTALL.md`; its audit reached preflight but
  has no final findings/report. Antigravity and the other entry skills remain pending.
- Full acceptance still fails with `FAIL: results: missing target arcade` because
  only PoolTogether has a scored result. No new benchmark scores were inferred from
  ungraded findings, and release closure remains pending.

## Implementation follow-up — 2026-10-17

The nine deferred final-review fixes in [PROGRESS.md](PROGRESS.md#final-review-fixes--2026-10-17)
are implemented locally. `bash tests/run.sh` passes 112 tests and structure lint.
These changes do not complete benchmark grading, runtime/entry-skill verification or
release closure. The recorded October 16 smoke runs predate these follow-up changes;
final release evidence must identify the tested tree accurately.
