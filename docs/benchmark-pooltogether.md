# PoolTogether benchmark — 2026-10-13

**PASS for this target:** ChainSec matched Krait v8 at 11.11% recall and zero false positives.
This is one of five planned contests, not the full acceptance run.

## Run

- Target: `code-423n4/2024-03-pooltogether`, commit
  `480d58b9e8611c13587f28811864aea138a0021a` (contest snapshot, before the later Discord export).
- ChainSec: `bfd53d0`, including the scope and report-methodology fixes. The audit used a copied
  working-tree snapshot; its skill-file hashes were checked against this commit afterward.
- Runtime: Claude Code 2.1.296, default model `claude-sonnet-5-5`.
- Full audit: six contest files, compiler facts, degraded tooling because Slither was absent.
  All phases completed; 11 subagents completed. State analysis overlapped rescan, with per-unit
  analysis after rescan; verification consumed all phase outputs.
- Elapsed: approximately 7 minutes 23 seconds. CLI-reported usage cost: $3.42
  (not a statement of subscription billing).
- A natural-language invocation was rejected because the skill requires explicit invocation.
  A fresh session using `/chainsec-audit` completed successfully.
- The auditor received local source, tests, scope, README and existing bot reports. Published
  results were retrieved separately for grading and were not supplied to the auditor.
- Audited source/tests remained unchanged. Final findings passed `validate-findings.py`.
  Verification used code traces; no executable PoC was run.

## Grade

The [official report](https://code4rena.com/reports/2024-03-pooltogether) contains one High and
eight Medium findings. Only final validated ChainSec findings receive credit.

| Measure | Krait v8 | ChainSec |
|---|---:|---:|
| Exact matches | 1 | 1 |
| Partial matches | 0 | 0 |
| False positives | 0 | 0 |
| Recall | 11.11% | 11.11% |
| Precision | 100% | 100% |

`SOL-001` exactly matches [H-01](https://github.com/code-423n4/2024-03-pooltogether-findings/issues/59):
`claimYieldFeeShares` clears the entire fee balance when minting only the requested shares.
All eight official Medium findings were missed by the final report.

## What to improve next

The per-unit pass found `PC1-1`: deposit/share-liquidation supply checks do not reserve capacity
for pending fee shares. It was rated Low and then killed at Gate H. Its mechanism overlaps
[M-05](https://github.com/code-423n4/2024-03-pooltogether-findings/issues/244) and
[M-07](https://github.com/code-423n4/2024-03-pooltogether-findings/issues/91), but it earns no credit
because it did not survive to the report.

The critic equated the documented uint96 supply cap with the distinct failure to reserve room
for accrued fees. It also conflated low precision per dollar with huge nominal supply. Gate H
already requires matching entry point, root cause and impact; the run did not enforce that
distinction here. A focused follow-up should test that distinction and severity assessment
before changing the general detection prompts. This benchmark has not been rerun or tuned
against the answer key.

The other six Medium findings have no corresponding final finding. This single run does not
establish whether each was missed during detection or filtered before a candidate was written.
Model and tooling differences from Krait are not controlled, so this comparison measures the
recorded outputs rather than isolating the effect of the ChainSec port.

## Artifacts

- [Scored result and per-finding grades](../benchmarks/solidity/results/pooltogether.json)
- [Audit report](../benchmarks/solidity/artifacts/pooltogether/audit/report.md)
- [Phase artifacts](../benchmarks/solidity/artifacts/pooltogether/audit/solidity/)
- [Run metadata and skill hashes](../benchmarks/solidity/artifacts/pooltogether/run.json)

Reproduce the comparison:

```sh
python3 tools/score_benchmark.py compare benchmarks/solidity/baselines/krait-v8.json benchmarks/solidity/results
```

The comparator uses only shared target IDs. Its current PASS covers PoolTogether alone;
InitCapital, GoodEntry, Arcade and Frankencoin remain pending.
