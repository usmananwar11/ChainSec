---
name: chainsec-poc
description: Build and run an executable proof-of-concept for a ChainSec finding using the chain pack's PoC framework, asserting real harm and running the falsification gate. Run only when the user asks for a PoC.
disable-model-invocation: true
argument-hint: "<finding-id> [path]"
---

# ChainSec PoC

1. Resolve CORE as in chainsec-audit.
2. Find the finding: search `TARGET/.audit/*/findings.json`, then `TARGET/.audit/*/verdicts.json`,
   for the given id. Not found → list available ids and stop. The folder name is the chain.
3. Read `../chainsec/engine/poc/workflow.md`, then the pack guide named by `pack.json` `poc.guide`
   in `../chainsec/chains/<chain>/`. Follow the workflow; supporting references are in
   `../chainsec/engine/poc/` and the pack's `poc/references/`.
4. Write artifacts to `TARGET/.audit/<chain>/poc/<id>/` and update the finding's
   `verdict.evidence_tag` in `TARGET/.audit/<chain>/findings.json`.
