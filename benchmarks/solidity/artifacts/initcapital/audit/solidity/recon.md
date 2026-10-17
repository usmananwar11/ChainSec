# ChainSec Recon Report

## Protocol Overview
- Name: INIT Capital (C4 2023-12 invitational)
- Type: Lending money market (isolated multi-position, ERC721 positions, modes, flashloans, multicall, hooks, rebase wrappers) — keys: lending, proxy-upgradeable, vault (share-based pools; virtual shares)
- Dependencies: OpenZeppelin 4.9.3 (+Upgradeable), API3 ServerV1, Chronicle/Pyth (Pyth out of scope), mUSD/USDY (Ondo), WNative
- Compiler: solc 0.8.19 (pragma ^0.8.19), Foundry
- Scope size: 17 files, ~2229 total LOC incl. comments (README SLoC 1545)
- Facts mode: compiler (OZ 4.9.3 + forge-std installed locally into gitignored contracts/.cache and lib/ to make `forge build` succeed)
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded (Mantle, MNT)

## File Risk Table (MANDATORY — Detection phase follows this)
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|------|------|-----------|------|-----|-----------|---------------|-------|
| 1 | contracts/core/InitCore.sol | 174.0 | DEEP | 600 | 3 | 24 | Entry point; health checks, multicall, flash, liquidate, callback |
| 2 | contracts/lending_pool/LendingPool.sol | 107.45 | DEEP | 269 | 2 | 14 | Shares/debt accounting, accrue, flash cash sync |
| 3 | contracts/core/PosManager.sol | 100.05 | DEEP | 341 | 2 | 12 | ERC721 positions, collateral balance tracking, wLp |
| 4 | contracts/hook/MoneyMarketHook.sol | 84.65 | DEEP | 273 | 6 | 3 | Hook wrapping multicall; holds position NFTs, approvals |
| 5 | contracts/core/Config.sol | 50.45 | DEEP | 149 | - | - | Mode/pool config, factors |
| 6 | contracts/core/LiqIncentiveCalculator.sol | 40.8 | STANDARD | 116 | - | - | Liquidation incentive; immaturity +0 (tests exist) |
| 7 | contracts/helper/rebase_helper/mUSDUSDYHelper.sol | 39.65 | STANDARD | 33 | - | - | wrap/unwrap rebase; balance-based, permissionless |
| 8 | contracts/oracle/InitOracle.sol | 37.0 | STANDARD | 120 | - | - | Primary/secondary fallback via try/catch |
| 9 | contracts/oracle/Api3OracleReader.sol | 35.6 | STANDARD | 92 | - | - | Staleness check, decimals scaling |
| 10 | contracts/common/Multicall.sol | 35.55 | STANDARD | 31 | - | - | delegatecall self multicall, payable |
| 11 | contracts/risk_manager/RiskManager.sol | 35.55 | STANDARD | 91 | - | - | Debt ceiling per mode |
| 12 | contracts/common/TransparentUpgradeableProxyReceiveETH.sol | 27.65 | STANDARD | 13 | - | - | receive() override |
| 13 | contracts/common/library/UncheckedIncrement.sol | 18.5 | STANDARD | 10 | - | - | |
| 14 | contracts/lending_pool/DoubleSlopeIRM.sol | 17.1 | STANDARD | 42 | - | - | rate math |
| 15 | contracts/helper/rebase_helper/BaseRebaseHelper.sol | 15.95 | STANDARD | 19 | - | - | |
| 16 | contracts/common/AccessControlManager.sol | 15.8 | SCAN | 16 | - | - | |
| 17 | contracts/common/UnderACM.sol | 15.7 | STANDARD (promoted parent) | 14 | - | - | base of most contracts |

(Exact per-file counters are in risk.json; Ext Calls / State Writers above are indicative where shown.) No immaturity adjustments applied: prior audits (Init_v01, PeckShield) exist, tests exist for all contracts, no TODO/FIXME in scope.
Codebase size category: MEDIUM (16-40)

## Fund Flows
- Supply: user transfers underlying to LendingPool, then InitCore.mintTo(pool,to) → pool.mint computes shares from `balanceOf - cash` (balance-delta pattern; core is not the custodian). Burn: shares transferred to pool then burnTo.
- Collateral: pool shares (ERC20) transferred to PosManager, then collateralize() credits `balanceOf(PosManager) - __collBalances[pool]` to the position (balance-delta). decollateralize sends shares out, then health check.
- Borrow: InitCore.borrow → debtShares in PosManager + RiskManager mode debt, pool.borrow transfers underlying to arbitrary `_to`. Repay: caller transfers underlying to pool, pool.repay verifies balance delta.
- Flash: pool underlying moved via transferFrom (pool approved core max), callback to msg.sender, syncCash verifies cash ≥ before+fee.
- Liquidation: liquidator repays debt in pool, receives collateral shares (or wLp) at incentive-adjusted oracle prices; bad debt: min(available).
- Hook: MoneyMarketHook owns position NFTs for users, builds multicall (repay, withdraw, mode change, borrow, deposit), wraps native, rebase helpers.
- InitCore.callback / transferToken: generic helpers, callable by anyone.

## Trust Boundaries
- Roles via AccessControlManager: guardian (pool config, factors status, IRM, reserve factor, risk manager, debt ceilings, max coll count), governor (config/oracle address, collateral/borrow factors, whitelisted wLps, oracle sources, treasury). Trusted.
- Permissionless: mintTo, burnTo, createPos, multicall, liquidate, liquidateWLp, flash, callback, transferToken, accrueInterest, harvest/claim (position-authorized), rebase helper wrap/unwrap, hook execute/createPos.
- Position auth: ERC721 owner/approved on PosManager; hook is owner of positions it creates and keys them by (msg.sender, posId).
- External data: API3 server price + timestamp; InitOracle primary/secondary with deviation check; ERC20 tokens (no FoT/ERC777 stated), wLp contracts (not in scope but called), ICallbackReceiver/IFlashReceiver arbitrary contracts.

## Attack Surface Priority
1. Position health bypass via multicall / isMulticallTx / uncheckedPosIds (delayed health, callback, nonReentrant interplay, posIds removed during loop, flash lock).
2. Balance-delta accounting (LendingPool.mint/repay/syncCash, PosManager.addCollateral/__collBalances) — donation, front-running of mint/collateralize, shared-balance hijack between users; MoneyMarketHook transfers to pool then core mintTo.
3. InitCore.callback arbitrary external call with core as caller (msg.sender passthrough) and payable value; approvals held by core/pools (pool approves core uint max).
4. Liquidation math (incentive, oracle prices, min of available collateral, health-after-liq check, bad-debt handling, share/rounding, repay of debt shares > position).
5. Interest accrual (accrueInterest rounding, reserve minting, totalDebt vs per-position totals, setIrm timing), debt/share rounding.
6. Oracle: InitOracle try/catch fallthrough, zero price, Api3 negative/zero price & decimals, deviation check divide by zero, unset sources.
7. MoneyMarketHook: msg.value handling for WNATIVE pools, returnNative sweeps all balance, rebase helper unwrap to arbitrary `to`, approve flows, ERC721 holder ownership, execute with posId != 0 when initPosIds missing.
8. Rebase helpers: wrap/unwrap use full balance (anyone can steal stray balance); stale approvals.
9. Config/RiskManager: mode changes, setPosMode and debt ceilings, factor validation.

## Novel Code (not from libraries)
All of contracts/core, lending_pool, hook, risk_manager, oracle, helper, Multicall (Uniswap-derived but modified: payable delegatecall with health-check wrapper), UnderACM.

## Detection Primer
Loaded: domains/defi/primers/defi-lending.md, chains/solidity/primers/proxy-upgrades.md

## Activated Modules
| Module | Trigger Evidence |
|--------|-----------------|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/lending-liquidation-deep.md | borrow/repay/liquidate/health in InitCore |
| domains/defi/modules/oracle-analysis.md | InitOracle, Api3OracleReader price reads |
| chains/solidity/modules/oracle-analysis.md | same |
| domains/defi/modules/economic-design.md | flash fees, liquidation incentive, reserve factor |
| domains/defi/modules/vault-share-accounting.md | LendingPool share-based pool with virtual shares |
| chains/solidity/modules/erc4626-vault-deep.md | share conversion mulDiv with virtual offsets |
| domains/defi/modules/flash-loan-interaction.md | InitCore.flash; balanceOf(address(this)) in LendingPool/PosManager |
| domains/defi/modules/token-flow-tracing.md | token transfers throughout |
| domains/defi/modules/multi-tx-attack.md | multicall, mint/collateralize sequences |
| domains/defi/modules/external-protocol-integration.md | API3, mUSD/USDY, WNative |
| chains/solidity/modules/eip-standard-compliance.md | ERC20 pool shares, ERC721 positions |

## Relevant Checklists
Lending: oracle manipulation/staleness, liquidation bonus and bad debt, interest rounding, self-liquidation, health check bypass, balance-delta donation, multicall reentrancy, ERC721 approvals, first-depositor (mitigated via virtual shares 1e8/1), flash fee bypass (known).
