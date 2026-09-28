# AMM & MEV Deep Analysis Module

> Chain-specific half of `domains/defi/modules/amm-mev-deep.md`.

## 7. Hardcoded Zero Slippage

- Check: grep for `amountOutMin`, `minAmountOut`, `sqrtPriceLimitX96`. Any hardcoded to 0?
