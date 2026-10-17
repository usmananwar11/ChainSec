# Solidity benchmark scoring

Grades per official finding: EXACT (same root cause and location) = 1, PARTIAL (related area or
same mechanism at a different location) = 0.5, missed = 0. Each reported ChainSec finding that
matches no official finding is an FP.

TP = exact + 0.5 × partial · Precision = TP/(TP+FP) · Recall = TP/official_total.
Krait's registry applied partial credit inconsistently; `baselines/krait-v8.json` re-scores its
v8 targets with this rule.

The Frankencoin denominator was corrected on 2026-10-13: the
[official report](https://code4rena.com/reports/2023-04-frankencoin) lists 6 High and 15 Medium
findings (21 total), while the imported registry lists 20. Krait's recorded match and FP counts
are unchanged. The corrected five-target baseline is 17.16% (11.5 / 67), replacing the historical
17.42% (11.5 / 66). The registry remains an unchanged historical import.

### Finalized five-contest baseline — 2026-10-14

Reviewed the correction committed in `81bad63` against the official report's
High Risk Findings (6) and Medium Risk Findings (15), covering H-01–H-06 and
M-01–M-15. The accepted Frankencoin denominator is **21**.

| Target | Official H/M total | Exact | Partial | Weighted TP | FP |
|---|---:|---:|---:|---:|---:|
| PoolTogether | 9 | 1 | 0 | 1 | 0 |
| InitCapital | 15 | 0 | 1 | 0.5 | 0 |
| GoodEntry | 14 | 5 | 0 | 5 | 0 |
| Arcade | 8 | 2 | 1 | 2.5 | 0 |
| Frankencoin | 21 | 2 | 1 | 2.5 | 0 |
| **Total** | **67** | **10** | **3** | **11.5** | **0** |

The acceptance target is **11.5 / 67** recall (**17.16%** displayed), with
**zero false positives**. Use the unrounded fraction for comparisons.
Reproduce the score with
`python3 tools/score_benchmark.py score benchmarks/solidity/baselines/krait-v8.json`.
The regression test in `tests/test_score_benchmark.py` checks all five entries,
their counts, and the aggregate score. This finalizes the baseline; full ChainSec
acceptance still requires the remaining contest runs and a comparison across all five.

### ChainSec full-run results — 2026-10-17

| Target | Official | Exact | Partial | Weighted TP | FP |
|---|---:|---:|---:|---:|---:|
| PoolTogether | 9 | 1 | 0 | 1 | 0 |
| InitCapital | 15 | 3 | 0 | 3 | 0 |
| GoodEntry | 14 | 4 | 0 | 4 | 4 |
| Arcade | 8 | 0 | 0 | 0 | 0 |
| Frankencoin | 21 | 4 | 1 | 4.5 | 2 |
| **Total** | **67** | **12** | **1** | **12.5** | **6** |

Recall 18.66% vs baseline 17.16%, but 6 false positives vs 0: full acceptance **FAILS**.
Grades were produced by delegated agent review of each final findings file against the
official report and are borderline in places (e.g. Frankencoin M-12 PARTIAL, GoodEntry M-07,
InitCapital M-07); see each result's `reason` fields. Isolation of the audits from official
answers was not independently certified.

## Running a target
1. `git clone <repo> /tmp/bench/<id>` at the contest commit (registry `repo`).
2. Open a fresh agent session in that folder; run `chainsec-audit` (no flags).
3. Grade `.audit/findings.json` against the official High/Medium findings in the registry's
   `findings_repo` (report at https://code4rena.com/reports/<contest>). Record matches.
4. Write `benchmarks/solidity/results/<id>.json` (format: see baselines) — include `matches`,
   `false_positives`, ChainSec version/commit and the facts mode in `notes`.
5. For a development comparison, run
   `python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results --target <id>`.

## Full acceptance

```sh
python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results
```

The default comparison requires all five targets in both the baseline and results.
Each required ID must appear exactly once, including across result files and within
JSON lists, and its official total must match the finalized table above. Missing or
duplicate targets and incorrect totals produce `FAIL` with exit code 1 before scoring.
Other target IDs are excluded from this five-target comparison.
Acceptance requires aggregate recall at least equal to the baseline and no increase
in false positives. The finalized baseline has zero false positives.

`--target <id>` checks only the named target under the same uniqueness and official-total
rules and labels the output as a development comparison, not full acceptance.
With only the recorded PoolTogether result, full acceptance fails; the explicit
PoolTogether development comparison passes.

## Known methodology deltas vs Krait
- Regex-mode `state_writers` excludes view/pure functions (Krait counted all public/external).
- `external_calls` counts only call/transfer primitives in both modes.
- On macOS Krait's extractor needed GNU `timeout`; without it Krait always ran in regex mode.
- Regex mode now detects tuple-assignment storage writes, e.g. `(a, b) = (...)`.
