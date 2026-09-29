# Solidity benchmark scoring

Grades per official finding: EXACT (same root cause and location) = 1, PARTIAL (related area or
same mechanism at a different location) = 0.5, missed = 0. Each reported ChainSec finding that
matches no official finding is an FP.

TP = exact + 0.5 × partial · Precision = TP/(TP+FP) · Recall = TP/official_total.
Krait's registry applied partial credit inconsistently; `baselines/krait-v8.json` re-scores its
v8 targets with this rule.

## Running a target
1. `git clone <repo> /tmp/bench/<id>` at the contest commit (registry `repo`).
2. Open a fresh agent session in that folder; run `chainsec-audit` (no flags).
3. Grade `.audit/findings.json` against the official High/Medium findings in the registry's
   `findings_repo` (report at https://code4rena.com/reports/<contest>). Record matches.
4. Write `benchmarks/solidity/results/<id>.json` (format: see baselines) — include `matches`,
   `false_positives`, ChainSec version/commit and the facts mode in `notes`.
5. `python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results`

## Known methodology deltas vs Krait
- Regex-mode `state_writers` excludes view/pure functions (Krait counted all public/external).
- `external_calls` counts only call/transfer primitives in both modes.
- On macOS Krait's extractor needed GNU `timeout`; without it Krait always ran in regex mode.
- Regex mode now detects tuple-assignment storage writes, e.g. `(a, b) = (...)`.
