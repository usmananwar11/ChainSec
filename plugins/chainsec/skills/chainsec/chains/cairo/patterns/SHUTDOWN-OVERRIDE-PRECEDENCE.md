# SHUTDOWN-OVERRIDE-PRECEDENCE

> **Detector class**: `SHUTDOWN_OVERRIDE_PRECEDENCE`
> **Inject into**: Lens A (Access/State)
> **Category**: Emergency controls
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-123, AV-124
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Contract computes both an inferred shutdown mode and an explicit fixed override.
If inferred mode is checked first with early return, admin override can be shadowed.

## Vulnerable pattern

- inferred mode is evaluated first
- function returns inferred mode before reading fixed/admin override
- fixed override becomes ineffective during certain states

## Secure pattern

- check explicit fixed/admin override first
- return inferred mode only when fixed override is not active

## Detection

- function combines inferred mode + fixed override mode
- inferred path has early return before fixed override check
- both compare against same sentinel (`NONE`, `0`, etc.)

## False-positive caveats (Gate C / FP-10 evidence)

- no admin override exists by design
- inferred mode is intentionally authoritative and documented

## Minimum tests (PoC and regression targets)

- both inferred + fixed active returns fixed override
- fixed-only and inferred-only behaviors are independently tested
