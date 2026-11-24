# Cairo snippet regression suite

`cases.jsonl` is `evals/cases/cairo_auditor_realworld_benchmark.jsonl` from
[keep-starknet-strange/starknet-skills](https://github.com/keep-starknet-strange/starknet-skills)
(MIT, Copyright (c) 2026 Keep Starknet Strange), copied unchanged: 42 short cases, 17 with
`expected_detect: true` and 25 clean.

This suite is a **regression check, not acceptance**: the Cairo pack's `patterns/` were ported from
the same project's vulnerability database, so recall here is optimistic. Acceptance uses full
contests (`benchmarks/cairo/registry.yaml`).

1. `python3 make_projects.py cases.jsonl OUT` writes 6 Scarb projects (one case per source file,
   fragments wrapped in a contract module) and `OUT/manifest.json`.
2. In each `OUT/<project>`, run `chainsec-audit --quick` in a fresh agent session.
3. `python3 score_snippets.py OUT/manifest.json OUT` maps every final finding to its case file and
   prints detected / missed / flagged-clean counts per class.
