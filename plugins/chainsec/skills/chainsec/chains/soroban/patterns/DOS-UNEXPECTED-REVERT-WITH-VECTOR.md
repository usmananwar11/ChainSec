# DOS-UNEXPECTED-REVERT-WITH-VECTOR

> **Detector class**: Scout `dos-unexpected-revert-with-vector`
> **Inject into**: Lens D
> **Category**: DoS
> **Tier**: security
> **Related heuristics** (heuristics.md): RES-02, STOR-04
> **Module**: [modules/resource-limits.md](../modules/resource-limits.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/17-dos-unexpected-revert-with-vector.md, vulnerabilities/17 and test-cases; see ATTRIBUTION.md -->

## Description

An entry point anyone can call that appends to a stored `Vec`/`Map` lets an attacker grow it until later reads, iterations or ledger-entry size limits make a shared function revert, locking out every user.

## Vulnerable pattern

```rust
state.candidates.push_back(candidate.clone());   // callable by anyone
```

## Secure pattern

```rust
state.admin.require_auth();   // or caller.require_auth() + per-key storage:
env.storage().instance().set(&DataKey::Candidate(candidate), &c);
```

## Detection

- `push_back`/`push_front`/`insert` on a stored collection in an entry point with weak or no `guards`.
- Another entry point reads or loops over the same collection.

## False-positive caveats (Gate C / FP-10 evidence)

- Admin-only or fee-gated growth with a hard cap is fine.
- Scout notes owner checks inside a helper trigger false positives: read the helper.
- Needs a path where the bloat blocks someone else; self-harm only is not a finding.

## Minimum tests (PoC and regression targets)

- Loop the append in a test until a dependent function exceeds the budget or entry size and assert it fails.
- Show cost to the attacker (fee/rent) versus the impact on others.
