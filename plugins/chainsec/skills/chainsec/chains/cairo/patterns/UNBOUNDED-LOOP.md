# UNBOUNDED-LOOP

> **Detector class**: `UNBOUNDED_LOOP`
> **Inject into**: Lens D (Edge cases/Math)
> **Category**: DoS
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-80
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

View/mutation functions iterate over unbounded state size and become unusable as data grows.

## Vulnerable pattern

- loop upper bound tied to global counter/state length
- no pagination/limit parameter
- linear scan over full dataset for filtered queries

## Secure pattern

- support pagination (`start`, `limit`) and bounded iteration
- expose index mappings for targeted retrieval

## Detection

- function loops from `1..next_id` or `0..len` and reads storage each iteration
- returns aggregate list without caller-supplied bound

## False-positive caveats (Gate C / FP-10 evidence)

- internal/admin-only maintenance function not exposed to user paths

## Minimum tests (PoC and regression targets)

- pagination correctness tests
- large-state query gas/time budget tests
