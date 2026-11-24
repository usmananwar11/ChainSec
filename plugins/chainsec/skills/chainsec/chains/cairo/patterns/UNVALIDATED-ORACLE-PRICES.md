# UNVALIDATED-ORACLE-PRICES

> **Detector class**: `UNVALIDATED_ORACLE_PRICES`
> **Inject into**: Lens B (Value flow)
> **Category**: Oracles
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-46
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Description

Oracle price updates bypass signature/median/deviation validations and accept raw input values.

## Vulnerable pattern

- validated path disabled/commented with TODO markers
- test-only fast path writes primary prices directly from compacted arrays

## Secure pattern

- route all updates through validation pipeline
- fail closed when validation modules are disabled/unavailable

## Detection

- `set_prices` uses direct `set_primary_price_` writes from compacted arrays
- commented `set_prices_`/`validate_prices_` path indicators

## False-positive caveats (Gate C / FP-10 evidence)

- dedicated test contract/module not deployed to production

## Minimum tests (PoC and regression targets)

- invalid signer/price deviation cases revert
- median/signature path coverage tests
- validator-disabled/unavailable path must fail closed (price update reverts)
