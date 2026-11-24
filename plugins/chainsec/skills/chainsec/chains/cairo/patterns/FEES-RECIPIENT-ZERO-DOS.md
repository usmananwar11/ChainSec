# FEES-RECIPIENT-ZERO-DOS

> **Detector class**: `FEES_RECIPIENT_ZERO_DOS`
> **Inject into**: Lens B (Value flow)
> **Category**: Fees / value flow
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-42
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Fee recipient is set without non-zero guard and later used in payout paths.
If set to zero address, fee distribution can revert and block core accounting flows.

## Vulnerable pattern

- config setter writes `fees_recipient` directly
- no non-zero validation in setter path
- payout/report path depends on recipient for transfer/mint

## Secure pattern

- enforce non-zero fee recipient in config setter
- optionally require recipient contract/interface checks when protocol requires

## Detection

- `fees_recipient` written from parameter
- no non-zero check around assignment
- `fees_recipient` used in transfer/mint/report path

## False-positive caveats (Gate C / FP-10 evidence)

- protocol explicitly allows zero as burn sink and tests that behavior

## Minimum tests (PoC and regression targets)

- setting zero recipient reverts
- report/payout succeeds for valid recipient
- changing recipient preserves report flow invariants
