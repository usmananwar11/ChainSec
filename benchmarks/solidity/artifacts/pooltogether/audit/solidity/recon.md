# ChainSec Recon Report

## Protocol Overview
- Name: PoolTogether V5 PrizeVault (C4 2024-03-pooltogether)
- Type: Yield Vault / ERC4626 (prize-linked savings) — keys: `vault`
- Dependencies: OpenZeppelin (ERC20, ERC20Permit, SafeERC20, Math, SafeCast), owner-manager-contracts Ownable, PrizePool, TwabController, ILiquidationSource (LiquidationPair), underlying ERC4626 yieldVault, Claimer
- Compiler: ^0.8.24
- Scope size: 6 files, 1419 total LOC (PrizeVault 962)
- Facts mode: compiler
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded

## File Risk Table (MANDATORY)
| Rank | File | RISK_SCORE | Tier | LOC | Notes |
|---|---|---|---|---|---|
| 1 | src/PrizeVault.sol | 152.1 | DEEP | 962 | All funds; ERC4626, dust strategy, yield fee, liquidation source. Not in prior audit (new contract) |
| 2 | src/PrizeVaultFactory.sol | 40.95 | DEEP | 139 | CREATE2 deploy, transferFrom donation of yield buffer |
| 3 | src/TwabERC20.sol | 35.2 | DEEP | 104 | balances in TwabController; _mint/_burn/_transfer overrides |
| 4 | src/abstract/Claimable.sol | 25.7 | DEEP | 134 | claimPrize with user hooks, gas-limited |
| 5 | src/abstract/HookManager.sol | 20.65 | DEEP | 33 | per-user hooks |
| 6 | src/interfaces/IVaultHooks.sol | 17.35 | DEEP | 47 | interface |

Codebase size category: SMALL (≤15)

## Fund Flows
- Deposit: user -> vault (safeTransferFrom) -> vault sweeps whole asset balance ("latent dust") into yieldVault via previewDeposit + mint(shares) ; mints TWAB shares 1:1 to receiver. Post-check totalAssets>=totalDebt.
- Withdraw/redeem: burn shares; _withdraw uses latent balance then yieldVault.redeem(previewWithdraw(...)); transfers assets to receiver. Shares->assets 1:1 unless vault is undercollateralised (totalAssets<totalDebt) then proportional.
- Yield: totalAssets - totalDebt(supply + yieldFeeBalance) - yieldBuffer is liquidatable. LiquidationPair calls transferTokensOut (assets via _withdraw or shares via _mint) then verifyTokensIn contributes prize tokens to PrizePool.
- Yield fee: accrued as yieldFeeBalance (virtual shares), claimed by yieldFeeRecipient via claimYieldFeeShares -> _mint.
- Prize claim: Claimer -> claimPrize -> user hook beforeClaimPrize (recipient) -> prizePool.claimPrize -> afterClaimPrize.
- Factory: deployVault pulls YIELD_BUFFER of asset from msg.sender and donates it to the vault.

## Trust Boundaries
- Owner: setClaimer, setLiquidationPair, setYieldFeePercentage (<=90%), setYieldFeeRecipient. Trusted.
- liquidationPair: only caller of transferTokensOut/verifyTokensIn.
- claimer: only caller of claimPrize.
- yieldFeeRecipient: claimYieldFeeShares.
- Permissionless: deposit, mint, withdraw, redeem, depositWithPermit, sponsor, setHooks, view functions, anyone can donate assets.
- External trust: yieldVault (assumed non-malicious, no fees), asset (no fee-on-transfer), TwabController, PrizePool.
- Untrusted recipient: user-supplied hook implementation (beforeClaimPrize returns arbitrary recipient; afterClaimPrize), 150k gas limit.

## Attack Surface Priority
1. Yield fee accounting (claimYieldFeeShares, transferTokensOut yieldFee calc, _totalDebt incl. yieldFeeBalance).
2. Deposit/withdraw rounding & dust (latent balance sweep, yieldBuffer, LossyDeposit check, previewWithdraw vs redeem).
3. Undercollateralised conversion paths (convertToShares/Assets, previewWithdraw vs withdraw consistency, maxRedeem).
4. Liquidation source (transferTokensOut for shares vs assets, limits, availableYield).
5. Claimable hooks (gas griefing, returned bytes, reentrancy), permit flow, sponsor.
6. Factory (CREATE2 salt, unchecked transferFrom, donation, front-running).
7. TwabERC20 overrides (uint96 downcasts, transfer to self, delegation).

## Novel Code (not from libraries)
Entire PrizeVault: custom non-standard ERC4626, dust strategy, yield fee math, liquidation source, Claimable, HookManager, factory.

## Detection Primer
Loaded: domains/defi/primers (vault module set: none beyond modules below)

## Activated Modules
| Module | Trigger Evidence |
|---|---|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/vault-share-accounting.md | ERC4626 vault in PrizeVault.sol |
| chains/solidity/modules/erc4626-vault-deep.md | ERC4626 vault |
| domains/defi/modules/flash-loan-interaction.md | vault share/asset accounting |

## Relevant Checklists
ERC4626 share inflation/donation, rounding direction (withdraw should round shares up, redeem assets down), fee accounting, max* functions compliance, reentrancy through hooks/ERC777, uint96 limits, permit front-running.
