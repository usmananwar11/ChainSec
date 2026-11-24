# STALE-SNAPSHOT-READ

> **Detector class**: `STALE_SNAPSHOT_READ`
> **Inject into**: Lens D (Edge cases/Math)
> **Category**: State updates
> **Related attack vectors** (heuristics.md, Extended heuristics): none
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Function reads from an immutable snapshot while mutating live state in the same loop, creating stale read decisions.

## Vulnerable pattern

- captures `let self_copy = @self` snapshot
- reads critical values through snapshot
- writes state with mutable `self` in same iteration

## Secure pattern

- use consistent mutable/read context for dependent operations
- re-read live state after each mutation where ordering matters

## Detection

- snapshot alias used for reads (`self_copy.*`) in loop with mutable writes (`self.*`)

## False-positive caveats (Gate C / FP-10 evidence)

- snapshot reads are intentionally independent from mutated fields

## Minimum tests (PoC and regression targets)

- sequential update/read consistency test in same transaction
- invariant checks for state-dependent loop updates
