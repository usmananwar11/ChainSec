---
name: chainsec-fuzz
description: Extract protocol invariants and generate/run invariant fuzz tests with the chain pack's fuzz framework. Run only when the user asks for ChainSec fuzzing.
disable-model-invocation: true
argument-hint: "[path] [--chain <name>]"
---

# ChainSec fuzz

1. Resolve CORE as in chainsec-audit.
2. Detect chains with `python3 ../chainsec/scripts/detect-chain.py TARGET` (or use `--chain`).
3. For each chain: read `../chainsec/engine/fuzz.md`, then the pack guide named by `pack.json`
   `fuzz.guide`. If `TARGET/.audit/<chain>/recon.md` exists, use it; otherwise do only the
   invariant-extraction steps from code.
4. Outputs: `TARGET/.audit/<chain>/fuzz/invariants.md`, `.../fuzz/tests/`, `.../fuzz/report.md`.
