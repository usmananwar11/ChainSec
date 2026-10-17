# ChainSec Recon Report

## Protocol Overview
- Name: GoodEntry (C4 2023-08)
- Type: DEX/AMM (Uniswap V3 single-tick TokenisableRange), Lending (Aave v2 fork "ROE", out of scope, used as integration), Yield Vault (GeVault) — keys: dex-amm, lending, vault
- Dependencies: Uniswap V3 NonfungiblePositionManager/Factory/Pool, Uniswap V2-style router (V3Proxy adapter over V3 SwapRouter/Quoter), Aave v2 LendingPool (ROE) with PMTransfer extension, Chainlink feeds via Aave oracle, OpenZeppelin (vendored)
- Compiler: solidity 0.8.19 (RangeManager ^0.8.0)
- Scope size: 38 files in README scope (10 implementation contracts + 28 interfaces), ~2.5k SLOC; contracts/lib, openzeppelin-solidity, tests out of scope
- Facts mode: regex — structural facts are pattern-matched, not compiler-verified (lower confidence). (No foundry project/deps; compiler mode not forced.)
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded

## File Risk Table (MANDATORY — Detection phase follows this)
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|------|------|-----------|------|-----|-----------|---------------|-------|
| 1 | contracts/helper/V3Proxy.sol | 159.8 | DEEP | 196 | 9 | 11 | swap adapter, ETH handling; `to` arg ignored; held approvals/balances; immaturity +10: no test file |
| 2 | contracts/GeVault.sol | 135.25 | DEEP | 465 | 5 | 11 | share vault over TRs deposited in ROE; fees, rebalance, oracle check; |
| 3 | contracts/TokenisableRange.sol | 124.1 | DEEP | 382 | 12 | 5 | tokenised UniV3 position, fee compounding, LP accounting |
| 4 | contracts/PositionManager/OptionsPositionManager.sol | 91.6 | DEEP | 552 | 1 | 7 | flashloan receiver, liquidation, swaps |
| 5 | contracts/RangeManager.sol | 70.75 | DEEP | 215 | 3 | 5 | range creation, PMTransfer-based asset movement |
| 6 | contracts/PositionManager/PositionManager.sol | 45.4 | STANDARD | 148 | 1 | 2 | base of OPM: cleanup, PMWithdraw, removeDust |
| 7 | contracts/RoeRouter.sol | 31.35 | STANDARD | 87 | 0 | 3 | whitelist registry |
| 8 | contracts/helper/FixedOracle.sol | 21.3 | STANDARD | 46 | 0 | 1 | hardcoded oracle |
| 9 | contracts/helper/LPOracle.sol | 20.25 | SCAN | 105 | 0 | 0 | UniV2 LP fair-price oracle |
| 10 | contracts/helper/OracleConvert.sol | 19.05 | SCAN | 81 | 0 | 0 | composite chainlink |
| 11+ | interfaces/* (28 files) | 15–44 | STANDARD/SCAN | — | — | — | interfaces only; skim for signature mismatches |

Codebase size category: MEDIUM (38 files)

## Fund Flows
- Users deposit token0/token1 (or ETH→WETH) into GeVault; fee to treasury; shares minted by oracle-valued TVL. GeVault splits assets into TR positions (UniV3 NFTs owned by TR), TR tokens deposited into the ROE lending pool as collateral (aTokens held by vault). Withdraw burns shares, pulls all TRs out of ROE and Uniswap, pays user in a single chosen token valued by oracle, redeploys remainder.
- TR deposit/withdraw: Uniswap increaseLiquidity/decreaseLiquidity; fees accumulate in fee0/fee1 and compound when >1%.
- OPM: buyOptions flashloans TR tokens from ROE with mode 2 (open variable debt for msg.sender), withdraws underlying, optionally swaps, deposits underlying to ROE for user. Liquidation: flashloan debt TR, liquidationCall, redeposit to TR, flash repay. close/sellOptions/withdrawOptions/swapTokens use PMTransfer to pull user aTokens.
- RangeManager: moves user aTokens via PMTransfer, withdraws, redeposits to TR / lending pool.
- V3Proxy: Uniswap-V2-router-like wrapper used by OPM swaps.

## Trust Boundaries
- Owner: GeVault (setEnabled, treasury, push/shift/modifyTick, fee, tvlCap), RangeManager (generateRange, initRange), RoeRouter (add/deprecate pool, treasury), V3Proxy emergencyWithdraw.
- PositionManager/OPM are granted PMTransfer by lending pool: effectively they can move any user's aTokens; all external entry points taking `user` param (close, liquidate) must be checked for permission.
- Permissionless: GeVault.deposit/withdraw/rebalance, TR.deposit/withdraw/claimFee, OPM.buyOptions/liquidate/close/sellOptions/withdrawOptions/swapTokens/removeDust, V3Proxy swaps, RangeManager transfer*/remove*, executeOperation (guarded only by msg.sender==lendingPool; initiator not checked; poolId user-supplied).
- External data trusted: Aave oracle prices (no staleness), Uniswap slot0 spot (compared to oracle with 1% band).

## Attack Surface Priority
1. TokenisableRange share accounting (deposit/withdraw/claimFee, fee0/fee1 vs liquidity, sqrt-price from oracle, rounding, first/last depositor, totalSupply==0 closure).
2. GeVault deposit/withdraw valuation: oracle vs spot, fee calculation, TVL cap, inflation / withdrawals draining due to balance not only TR (idle balances), token-specific payouts, withdraw uses `getAdjustedBaseFee` after reserves, ETH receive/deposit path.
3. OPM flashloan callback and liquidation: initiator, poolId/user spoofing, `to` of swaps, closeDebt with user != msg.sender, fee calc, PMTransfer abuse via user param.
4. V3Proxy: `to` ignored (recipient is msg.sender), swapTokensForExactTokens refund, ETH refund paths, leftover balances.
5. RangeManager rounding/permissions; GeVault ticks array manipulation (shiftTick/modifyTick correctness).

## Novel Code (not from libraries)
All contracts in contracts/ (non-lib): TokenisableRange math, GeVault, OPM, PositionManager, V3Proxy, RangeManager.

## Detection Primer
Loaded: domains/defi/primers/defi-dex-amm.md, domains/defi/primers/defi-lending.md

## Activated Modules
| Module | Trigger Evidence |
|--------|-----------------|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/amm-mev-deep.md | Uniswap V3 positions, swaps in OPM/V3Proxy |
| domains/defi/modules/economic-design.md | fee logic in GeVault, TR claimFee, OPM liquidation fee |
| domains/defi/modules/flash-loan-interaction.md | Aave flashLoan in OPM, spot slot0 reads, deposit/withdraw |
| domains/defi/modules/lending-liquidation-deep.md | liquidationCall, repay, borrow-via-flashloan mode 2 |
| domains/defi/modules/oracle-analysis.md / chains/solidity/modules/oracle-analysis.md | Chainlink/AaveOracle in TR, GeVault, LPOracle, OracleConvert |
| domains/defi/modules/vault-share-accounting.md | GeVault and TR share minting |
| chains/solidity/modules/erc4626-vault-deep.md | custom share vault |
| domains/defi/modules/token-flow-tracing.md | transfers throughout |
| domains/defi/modules/external-protocol-integration.md | Uniswap V3, Aave |
| domains/defi/modules/multi-tx-attack.md | deposit/withdraw/rebalance sequenceable |
| chains/solidity/modules/eip-standard-compliance.md | GeVault and TR are ERC20 |

## Relevant Checklists
DEX/AMM, Lending, Yield Vault (share inflation, rounding direction, donation), Oracle (staleness acknowledged as known issue).
