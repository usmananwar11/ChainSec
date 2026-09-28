# ERC-4626 Vault Deep Analysis Module

> Chain-specific half of `domains/defi/modules/vault-share-accounting.md`.

> **Trigger**: Protocol implements ERC-4626 or custom share-based vault
> **Inject into**: Lens B (Value/Economic) + Lens D (Edge/Math/Standards)
> **Priority**: HIGH — share-based vaults are the #1 source of accounting bugs in DeFi
> <!-- Vectors from pashov/skills (MIT) -->

## 1. Inflation Attack Vectors

- **Virtual shares/offset**: Does vault use `_decimalsOffset()` or dead shares? If not → classic inflation possible

## 2. Round-Trip Profit Extraction

- Check: `convertToAssets(convertToShares(X)) <= X` (rounding favors vault)
- Check: `convertToShares(convertToAssets(S)) <= S` (rounding favors vault)

## 5. Virtual Shares Edge Cases

If vault uses virtual shares/offset (OZ 4626 `_decimalsOffset`):
- Does `maxDeposit()` / `maxMint()` correctly account for the offset?

## 6. Paused State Compliance

- When vault is paused: do `maxDeposit()` and `maxMint()` return 0? (ERC-4626 spec requires this)
- Does `previewDeposit()` still return a value when deposits are actually blocked? (misleading)

## 7. Preview vs Actual Discrepancy

- Is `previewDeposit(assets)` == actual shares received? Always? Or can it differ due to fees, slippage, or state changes?
- Is `previewRedeem(shares)` == actual assets received? These MUST match per ERC-4626 spec
- If `preview*` and actual diverge → integrating protocols make wrong decisions
