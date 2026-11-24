# ChainSec Cairo pack: implementation plan

Spec: `docs/superpowers/specs/2026-11-24-chainsec-cairo-pack-design.md`. Branch: `feat/cairo-pack`.
After each task, `bash tests/run.sh` passes (lint + unit tests).

| # | Task | Output | Verify |
|---|---|---|---|
| 1 | Engine generalization | EVM-only modules removed from `mindsets.md` (pack modules follow their `Inject into` header); OZ names in `domains/defi` made generic | lint + port-coverage tests pass |
| 2 | Pack manifest + detection | `chains/cairo/pack.json`; required files stubbed | `detect-chain.py` finds a Starknet Scarb project; ignores plain Cairo |
| 3 | Facts extractor | `recon/extract.sh`, `recon/extract.py`, `tests/test_extract_cairo.py` | output validates against `facts.schema.json`; component/l1_handler/Cairo 0 cases |
| 4 | Clustering + Caracal summary | `recon/clustering.md`, `recon/caracal-summary.py` + test | test on a sample Caracal output |
| 5 | Port cairo-auditor content | `patterns/*.md` (vuln DB), `ATTRIBUTION.md`, `tests/test_port_coverage.py` additions | every vuln-DB ID present |
| 6 | Heuristics, FP patterns, modules, triggers, primers | `heuristics.md`, `fp-patterns.md`, `module-triggers.md`, `modules/`, `primers/` | lint resolves every referenced path |
| 7 | PoC guide | `poc/guide.md` | example test compiles with `snforge` on the fixture |
| 8 | Fuzz guide | `fuzz/guide.md` | example fuzz test runs with `snforge` on the fixture |
| 9 | Fixture | `tests/fixtures/cairo-basic` (planted unchecked `from_address`) | `scarb build` passes; extractor facts include the l1_handler |
| 10 | Snippet regression suite | `benchmarks/cairo/snippets/` projects + registry | each project builds |
| 11 | Contest benchmark | `benchmarks/cairo/registry.yaml`, baseline + ChainSec results | needs user approval (cost: full audits) |
| 12 | Docs, smoke test, release | README, INSTALL, PROGRESS updates; Claude Code quick smoke test | fixture audit reports the planted bug |
