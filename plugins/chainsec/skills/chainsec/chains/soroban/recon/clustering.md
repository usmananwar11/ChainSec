# Soroban clustering: contract crates and their helper modules

The unit of analysis for Soroban is a `#[contract]` type together with its `#[contractimpl]` blocks
and the crate modules those entry points call. Auth, storage, admin and event helpers usually live in
sibling modules or library crates; an agent that sees only the contract file misses the checks (or
the bugs) behind them.

## Build clusters

Group scope files into clusters:

- **One `#[contract]` type → one cluster**, with all its `#[contractimpl]` blocks (including
  `contracttrait` impls) and the crate helper modules its entry points call: storage accessors, admin
  and role checks, events, math. The contract's traits are its `facts.json` `units[].parents`.
- **Shared library crates** (workspace members without `#[contract]`, path dependencies) **join every
  cluster that uses them.** Analyze the library in depth once and note the other clusters that rely on it.
- **Free functions and math modules** go with the contract that calls them most; otherwise they form
  their own cluster.
- **OpenZeppelin `stellar-contracts` trait default methods are macro-generated and invisible in
  facts**: open the trait source for each parent and include the methods in the cluster notes.
- **Interfaces** (`#[contractclient]`, `contractimport!` stubs) are context only and never their own cluster.
- **Cluster size cap: ~1500 LOC.** Split larger clusters at a logical boundary.
- **Maximum 8 clusters.** If more exist, prioritise by RISK_SCORE from the recon table and note in
  the output which files got no dedicated pass.

Record the cluster plan before starting:

| Cluster | Files | LOC | Reason for grouping |
|---------|-------|-----|---------------------|

## Findings cap

- **Maximum 5 findings per cluster**, prioritised by severity.

## Inputs

Contract-to-trait links come from `facts.json` `units[].parents`, and LOC from `units[].loc`.
RISK_SCORE is `files[].score` in `risk.json`; clusters holding DEEP-tier files are analyzed first.
