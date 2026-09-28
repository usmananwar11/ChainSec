# External Protocol Integration Module

> Chain-specific half of `domains/defi/modules/external-protocol-integration.md`.

## 4. Silent Failure

Does the external function ever return without effect instead of reverting?
- CVX.mint() returns silently when operator != msg.sender
- Some ERC-20 transfers return false instead of reverting

## 6. Version-Specific Gotchas

- **Uniswap V3**: Negative ticks valid, `int24` sign extension, sqrtPriceX96 bounds
- **Curve**: `get_dy` vs `exchange` return semantics differ, native ETH vs WETH ID mismatch
- **Aave V3**: aToken exchange rate, health factor recalculation timing
- **Compound V3**: Comet vs legacy cToken interface differences
- **Lido/stETH**: Rebasing between blocks, wstETH vs stETH accounting
