# SYSCALL-SELECTOR-FALLBACK-ASSUMPTION

> **Detector class**: `SYSCALL_SELECTOR_FALLBACK_ASSUMPTION`
> **Inject into**: Lens C (External/Integration)
> **Category**: External calls
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-23, AV-39, AV-77
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Code retries `call_contract_syscall` with alternate selector casing when first call errors.
This assumes recoverable fallback behavior that can hide real compatibility bugs.

## Vulnerable pattern

- `call_contract_syscall(..., SELECTOR_A, ...)`
- branch on `result.is_err()`
- retry with `SELECTOR_B` for same logical function

## Secure pattern

- use canonical selector only
- fail fast on syscall errors with explicit error surface

## Detection

- one syscall followed by `is_err` branch
- second syscall in error branch with different selector
- both selectors target same operation semantics

## False-positive caveats (Gate C / FP-10 evidence)

- offchain simulation-only helper code
- test-only compatibility adapters with explicit scope

## Minimum tests (PoC and regression targets)

- failing syscall path reverts deterministically (no fallback retry)
- successful canonical selector path returns expected result
