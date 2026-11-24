# UNCHECKED-FEE-BOUND

> **Detector class**: `UNCHECKED_FEE_BOUND`
> **Inject into**: Lens B (Value flow)
> **Category**: Fees / value flow
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-41
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Caller-provided fee/rate parameter is forwarded to deployment or storage without range validation.
Out-of-bounds fee values can break economics, accounting, or protocol assumptions.

## Vulnerable pattern

- fee/rate/bps parameter accepted from external caller
- value passed directly to `deploy_syscall` calldata or storage write
- missing max/min bound assertion

## Secure pattern

- define protocol fee limits (`MAX_FEE_BPS`, optional `MIN_FEE_BPS`)
- validate fee bounds before writing or forwarding

## Detection

- function accepts fee-like numeric parameter
- parameter is written/forwarded (`.write`, `deploy_syscall`, external call)
- no nearby bound check on that parameter

## False-positive caveats (Gate C / FP-10 evidence)

- value already constrained by typed enum-like wrapper
- bounds guaranteed by trusted upstream invariant

## Minimum tests (PoC and regression targets)

- max allowed fee succeeds
- `max + 1` reverts with expected error
- zero-fee behavior is explicitly asserted per protocol policy
