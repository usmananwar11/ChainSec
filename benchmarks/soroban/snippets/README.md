# Soroban snippet regression suite

`cases.jsonl` is built from the `test-cases/` directory of
[CoinFabrik scout-soroban](https://github.com/CoinFabrik/scout-soroban) (MIT, Copyright (c) 2023
CoinFabrik) at commit `53157fd4ddd9e388bf91138699f4e27a500aaef3`, by `import_scout.py`.
92 cases across 22 detector classes, 46 with `expected_detect: true` and 46 clean. Each case keeps
the crate's `Cargo.toml` and `src/**/*.rs` with comments, `#[cfg(test)]` modules and the
"vulnerable"/"remediated" names removed, so the case files do not state the answer. `source_url`
still points at the upstream crate. `soroban-version` is skipped: its cases differ only in the
shared workspace pin.

This suite is a **regression check, not acceptance**: the Soroban pack's `patterns/` were ported
from the same project's detector set, so recall here is optimistic. Contract struct names in some
cases still name the class.

The generated projects are **not meant to build**: cases pin `=20.0.0`, `20.3.2` and `=21.3.0`,
which conflict in one workspace. Run audits with `CHAINSEC_NO_COMPILE=1`.

1. `python3 make_projects.py cases.jsonl OUT` writes 6 Cargo workspace projects (4 classes per
   project, one case per `contracts/case-<nn>/` crate, shuffled with a fixed seed) and
   `OUT/manifest.json`.
2. In each `OUT/<project>`, run `chainsec-audit --quick` in a fresh agent session with
   `CHAINSEC_NO_COMPILE=1`.
3. `python3 score_snippets.py OUT/manifest.json OUT` maps every final finding to its case
   directory and prints detected / missed / flagged-clean / clean-ok counts per tier and per class.
   The `security` and `quality` tiers are reported separately, and **only the security tier is a
   pass/fail signal**. Projects without `.audit/findings.json` are listed as `missing_projects`.

To regenerate `cases.jsonl` from a checkout of scout-soroban:
`python3 import_scout.py SCOUT_DIR cases.jsonl`.
