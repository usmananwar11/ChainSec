# Methodology notes
- Full pipeline run (no --quick), chain solidity, root ".", scope = README paths (38 files via pack.json).
- Phases 1-11 all completed; incomplete_phases = []. Validation passed first try (no repair/downgrade).
- Facts mode: regex (extractor did not use compiler; no foundry project/deps; compiler mode not forced). Preflight mode: degraded (slither missing).
- Recon, consensus merge, Pass 3 sweep, cluster building were done by the orchestrator; detect Pass1, lenses A-D, rescan, 6 per-unit clusters, state, critic, reporter by subagents.
- Executable PoCs: NONE run. All verdicts are [CODE-TRACE] by the critic. Critic killed e.g. DA-1 (executeOperation initiator) by FP-1; V3Proxy finding downgraded to Medium.
- Limitations: interfaces had no dedicated per-unit cluster; clusters.json 'excluded' entries are summarized; Aave pool/OZ/lib out of scope; automated-findings gist not accessed.
