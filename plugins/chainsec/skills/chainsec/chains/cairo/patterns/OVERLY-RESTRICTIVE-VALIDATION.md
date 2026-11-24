# OVERLY-RESTRICTIVE-VALIDATION

> **Detector class**: `OVERLY_RESTRICTIVE_VALIDATION`
> **Inject into**: Lens D (Edge cases/Math)
> **Category**: Edge cases / validation
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-57
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Validation rejects safe/common user flows due to overly strict inequalities or constraints.

## Vulnerable pattern

- uses strict `>` where `>=` is expected by product semantics
- blocks legitimate configurations (for example zero-cliff schedules)

## Secure pattern

- encode constraints that match protocol/business rules exactly
- add compatibility tests for boundary values

## Detection

- strict inequality on time/range boundaries in creation helpers
- user-impacting branch with no security rationale

## False-positive caveats (Gate C / FP-10 evidence)

- strict inequality is intentional and explicitly documented as product rule

## Minimum tests (PoC and regression targets)

- boundary tests for equal-value configurations
- tests proving rejected configurations are unsafe if intentionally disallowed
