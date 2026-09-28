# Solidity clustering: inheritance clusters

The unit of analysis for Solidity is an inheritance cluster. Rules ported from Krait per-contract analysis (Step 1 and the findings cap).

## Build contract clusters

Group scope files into clusters:

- **Same inheritance chain → same cluster.** A base and its derived contracts belong together: a "missing" check often lives in the parent, and an agent that only sees the child reports a false positive. Use `facts.json`'s inheritance tree when it exists; otherwise read the `contract X is Y, Z` declarations directly.
- **Standalone contracts** → their own cluster.
- **Cluster size cap: ~1500 LOC.** Split larger clusters at a logical boundary.
- **Maximum 8 clusters.** If more exist, prioritise by RISK_SCORE from the recon table and note in the output which files got no dedicated pass — silently dropping coverage reads as "we covered everything" when you didn't.

Record the cluster plan before starting:

| Cluster | Files | LOC | Reason for grouping |
|---------|-------|-----|---------------------|

## Findings cap

- **Maximum 5 findings per cluster** — prioritise by severity. This is a depth pass, not a volume pass.

## Inputs

The parents of each contract come from `facts.json` `units[].parents` (the inheritance tree), and LOC comes from `units[].loc`; sum `loc` over a cluster's units to apply the ~1500 LOC cap. RISK_SCORE is `files[].score` in `risk.json`, and clusters holding DEEP-tier files are analyzed first.
