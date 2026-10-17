# Methodology / limitations
- Skill: frozen local ChainSec snapshot (.claude/skills), full pipeline, no --quick. Chain: solidity, scope = 17 contest-README files.
- Phases run: preflight, extract, score, recon (orchestrator), detect (Pass1 + lenses A-D + consensus merge + Pass 3 sweep, orchestrator), rescan, per-unit (7 clusters), state, verify (critic, trace-only), validate (exit 0, no repair needed), report. incomplete_phases: none.
- Facts mode: compiler. First forge build failed (deps missing); installed OZ 4.9.3 (npm) into gitignored contracts/.cache and forge-std v1.9.7 into lib/, then re-ran extractor. No audited source/tests/skill files modified.
- Slither missing: degraded mode, no analyzer pre-scan.
- Executable PoCs: NONE run. Critic was trace-only; verdicts are [CODE-TRACE], not [POC-PASS].
- Deviations: per-unit and state subagents were dispatched concurrently; cluster 6 JSON had a string depth_evidence coerced to a list; recon risk-table ext-call/state-writer columns are indicative (risk.json is authoritative).
- Borderline kills worth a second look (chainsec-review): DD-2 (LiqIncentiveCalculator div-by-zero at health==0), RS-1 (PosManager collBalances overwrite), DD-5 (repay pause blocks liquidation), PC6-1 (API3 zero price).
