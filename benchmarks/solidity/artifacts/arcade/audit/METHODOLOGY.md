# Audit run notes (ChainSec, blind benchmark run)

- Chain: solidity, root `.`, 12 in-scope files (contract README / scope.txt paths), 1 chain.
- Phases run, all complete: preflight, extract, score, recon, detect (Pass 1, lenses A-D, consensus merge, Pass 3 sweep done by the orchestrator), rescan, per-unit (6 clusters), state, verify (critic), validate (passed first try, no repair needed), report.
- Incomplete phases: none.
- Facts mode: regex. `solc` is not installed, so no compiler-mode facts. A forge build was not attempted. Structural facts are lower confidence.
- Preflight mode: degraded. `slither` is missing. `forge 1.7.1` and `python3` were OK.
- Executable PoCs: NONE were run. The audit pipeline's critic does not build PoCs (Method D is out of scope), and chainsec-poc was not invoked. All verdicts are code-trace based and nothing was verified by execution.
- Known issues: taken from `slither/FullReport.md`. The linked gist is not fetchable offline, and `audits/Omniscia2023.pdf` was not parsed.
- Result: 0 reportable findings. The reporter excludes Low severity by rule. DC-1 (shared per-block treasury expenditure counter) was downgraded Medium -> Low and omitted. 7 candidates were killed. See `.audit/solidity/verdicts.json` for every candidate and verdict, including the Low ones.
- Observation on recall: the detection phases produced few candidates (5 raw candidates before dedup), so the clean result likely reflects limited detection depth in this run and is not strong evidence of absence. Lens B returned nothing. Several lens/per-unit "safe" conclusions were not independently executed.
- Source, tests and skill files were not modified. Pass 3 was done by reading the in-scope contracts directly.
