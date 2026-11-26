# INSUFFICIENTLY-RANDOM-VALUES

> **Detector class**: Scout `insufficiently-random-values`
> **Inject into**: Lens B
> **Category**: Randomness
> **Tier**: security
> **Related heuristics** (heuristics.md): RAND-01, TIME-01
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/5-insufficiently-random-values.md and vulnerabilities/5-insufficiently-random-values.md; see ATTRIBUTION.md -->

## Description

`ledger().timestamp()` is set by the validator set and `ledger().sequence()` is public and predictable, so values derived from them (`% max`) can be predicted or nudged. Soroban's `env.prng()` is the sanctioned source, but it is also deterministic within a transaction and only suits low-stakes use.

## Vulnerable pattern

```rust
let pick = e.ledger().timestamp() % max_val;
```

## Secure pattern

```rust
let pick = e.prng().u64_in_range(0..max_val);
```

## Detection

- Grep `ledger().timestamp()` and `ledger().sequence()` feeding `%`, hashing, or a winner selection.

## False-positive caveats (Gate C / FP-10 evidence)

- Timestamp or sequence used for time windows, not randomness, is not a finding.
- `env.prng()` for a high-value lottery is still weak: a caller can simulate and only submit winning transactions; call it out as a design limit rather than a fix.
- Commit-reveal designs that mix ledger data with user commitments are a different, bounded risk.

## Minimum tests (PoC and regression targets)

- Simulate the call at known ledger values and show the attacker computes the outcome before submitting.
- Regression: outcome no longer a pure function of public ledger fields.
