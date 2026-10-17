# Remaining four Solidity benchmarks — 2026-10-16

## Method

These full audits use ChainSec commit `7598d8f3d52e4a9b2f01e8edee046369a6f408c5`
and Claude Code 2.1.300 (`claude-sonnet-5-5`), with a fresh session and checkout for
each target. No quick flag was used. Official High/Medium findings are retrieved
for grading only after each audit's final output is frozen. Only final validated
findings receive credit; candidates killed or downgraded below Medium receive none.

The imported registry specifies repository URLs but no commit hashes. The snapshots
below pin the latest contest-era commits, before later Discord exports. Exact paths
are retained in each artifact directory's `scope.txt`. The only skill customization
is the copied Solidity pack's `scope.include` list and disabling fallback scope;
`scoped-pack.json` records it. All other skill files use the pinned ChainSec tree.

| Target | Contest commit | Scoped files |
|---|---|---:|
| InitCapital | `a53e401529451b208095b3af11862984d0b32177` | 17 |
| GoodEntry | `71c0c0eca8af957202ccdbf5ce2f2a514ffe2e24` | 38 |
| Arcade | `f8ac4e7c4fdea559b73d9dd5606f618d4e6c73cd` | 12 |
| Frankencoin | `1022cb106919fba963a89205d3b90bf62543f68f` | 10 |

Scope details:

- InitCapital's README lists 17 files, including `Multicall.sol` and
  `TransparentUpgradeableProxyReceiveETH.sol`; its older `scope.txt` lists only 15.
  This run uses the README's complete list.
- GoodEntry's README scope table lists 38 files, including 28 interfaces, despite
  a separate summary claiming 14 contracts. Its interface links incorrectly point
  under `contracts/interfaces`; the actual files are under `interfaces`.
- Arcade's README and `scope.txt` agree on 12 files.
- Frankencoin's source table lists 10 implementation files; interfaces and tests
  are available as context but excluded from the scored scope.

Auditors receive local source, tests, README, and pre-contest known-issue material.
Their instructions prohibit official reports, findings repositories, other benchmark
workspaces, and web search. Automatic memory is disabled. Dependency setup is allowed;
compiler fallback is recorded. The benchmark does not control model/tooling differences
from Krait and does not establish absence of bugs.

## Recovered execution evidence — recorded 2026-10-17

The four audit outputs are now preserved in the repository. **Grading remains pending**;
these are execution records, not scored benchmark results or acceptance evidence.

| Target | Facts | Observed elapsed | Evidence |
|---|---|---|---|
| InitCapital | compiler | 29m 9s | [Run](../benchmarks/solidity/artifacts/initcapital/run.json), [report](../benchmarks/solidity/artifacts/initcapital/audit/report.md) |
| GoodEntry | regex | 32m 24s | [Run](../benchmarks/solidity/artifacts/goodentry/run.json), [report](../benchmarks/solidity/artifacts/goodentry/audit/report.md) |
| Arcade | regex | 18m 1s | [Run](../benchmarks/solidity/artifacts/arcade/run.json), [report](../benchmarks/solidity/artifacts/arcade/audit/report.md) |
| Frankencoin | compiler | 31m 23s | [Run](../benchmarks/solidity/artifacts/frankencoin/run.json), [report](../benchmarks/solidity/artifacts/frankencoin/audit/report.md) |

All four per-chain findings files passed validation again on October 17. Their
preflights say `quick: false` and list no incomplete phases. Run records contain
runtime/model from transcript initialization, dispatch summaries, tool readiness,
validation, scope overrides, and SHA-256 hashes of preserved audit artifacts. Full
transcripts remain local at the recorded paths, with their hashes preserved.
Elapsed time is launch to the last timestamped transcript event, including post-report
wakeups, rather than summed API durations. No executable PoCs were run.

The recovered launch records mixed October 14 setup timestamps with October 16 process
launch epochs. `launch-record.json` preserves the originals; `run.json` uses the actual
launch epoch and transcript runtime (2.1.300), correcting this draft's earlier 2.1.296.
Installed skill sources match the current pinned tree except for the documented scope
pack override (generated Python bytecode excluded). This recovery did not independently
verify source integrity or every phase's completeness, and does not certify the draft's
answer-isolation protocol. Review those provenance details during grading. No official
answers were retrieved during this recovery.

