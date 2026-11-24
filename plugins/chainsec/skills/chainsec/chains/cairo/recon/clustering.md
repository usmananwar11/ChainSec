# Cairo clustering: contract modules and their components

The unit of analysis for Cairo is a `#[starknet::contract]` module together with every component
it embeds through `component!`. Component storage and impls become part of the contract, so an
agent that sees only the contract misses the checks (or the bugs) that live in the component.

## Build clusters

Group scope files into clusters:

- **Contract + embedded components → same cluster.** The components of each contract are its
  `facts.json` `units[].parents`. A component used by several contracts goes into each of their
  clusters; analyze it in depth once and note the other clusters that rely on it.
- **Free functions, libraries and math modules** go with the contract that calls them most;
  otherwise they form their own cluster.
- **Interfaces** (`#[starknet::interface]`) are context only and never their own cluster.
- **Cluster size cap: ~1500 LOC.** Split larger clusters at a logical boundary.
- **Maximum 8 clusters.** If more exist, prioritise by RISK_SCORE from the recon table and note in
  the output which files got no dedicated pass.

Record the cluster plan before starting:

| Cluster | Files | LOC | Reason for grouping |
|---------|-------|-----|---------------------|

## Findings cap

- **Maximum 5 findings per cluster**, prioritised by severity.

## Inputs

Contract-to-component links come from `facts.json` `units[].parents`, and LOC from `units[].loc`.
RISK_SCORE is `files[].score` in `risk.json`; clusters holding DEEP-tier files are analyzed first.
