# ChainSec Recon Report

## Protocol Overview
- Name: Frankencoin (ZCHF) — C4 2023-04 contest snapshot
- Type: Stablecoin (oracle-free, CDP with auction liquidation) + governance/pool shares (FPS bonding curve) + bridge — keys: governance, bridge (stablecoin/lending-like CDP; also vault-like share issuance in Equity)
- Dependencies: none external (no OZ imports; custom ERC20/ERC20PermitLight/Ownable, clone factory copied from optionality)
- Compiler: Solc 0.8.26 (pragma ^0.8.0 / >=0.8.0 <0.9.0); forge build needed FOUNDRY_VIA_IR=true (stack-too-deep otherwise)
- Scope size: 10 files, ~1949 total raw lines / ~950 SLOC (per README scope)
- Facts mode: compiler (forge with viaIR via env var)
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded (no native asset handling; ZCHF ~ 1 CHF)

## File Risk Table (MANDATORY — Detection phase follows this)
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|------|------|-----------|------|-----|-----------|---------------|-------|
| 1 | contracts/MintingHub.sol | 141.75 | DEEP | 315 | 13 | 9 | auctions, bids, challenges, split; all hub fund custody. immaturity +10 (TODO) |
| 2 | contracts/Position.sol | 112.55 | DEEP | 391 | 4 | 12 | collateral, mint/repay, clones |
| 3 | contracts/Frankencoin.sol | 74.25 | DEEP | 305 | 0 | 11 | minters, reserve accounting, notifyLoss mints |
| 4 | contracts/Equity.sol | 61.85 | DEEP | 317 | 1 | 4 | voting anchors, cubic bonding curve, redeem |
| 5 | contracts/StablecoinBridge.sol | 59.25 | DEEP | 85 | 2 | 5 | XCHF<->ZCHF 1:1 |
| 6 | contracts/ERC20.sol | 43.05 | DEEP | 241 | 0 | 4 | custom ERC20, infinite allowance, ERC677 |
| 7 | contracts/PositionFactory.sol | 31.35 | DEEP | 47 | 0 | 2 | clone via assembly |
| 8 | contracts/ERC20PermitLight.sol | 25.6 | DEEP | 72 | 0 | 1 | permit |
| 9 | contracts/Ownable.sol | 21.6 | DEEP | 52 | 0 | 1 | setOwner |
| 10 | contracts/MathUtil.sol | 17.1 | DEEP | 42 | 0 | 0 | cubic root, mulD18 |

Codebase size category: SMALL (≤15)

## Fund Flows
- Collateral: user -> Position (openPosition/clone/adjust); Position -> owner (withdraw) or -> bidder (notifyChallengeSucceeded); challenger collateral -> MintingHub (launchChallenge) -> bidder (bid averts) or back to challenger (end).
- ZCHF: minted via Position.mintInternal -> Frankencoin.mint splits owner / reserve (Equity) as fees+reserve. Bids held by MintingHub; returned on outbid; paid to challenger/owner/burned on end. notifyLoss mints/transfers from reserve to cover shortfall.
- FPS: ZCHF.transferAndCall -> Equity.onTokenTransfer mints shares on cubic curve; redeem burns shares and transfers ZCHF out after 90*7200 blocks holding.
- Bridge: XCHF in -> ZCHF mint; ZCHF burn -> XCHF out.

## Trust Boundaries
- Minters (approved after application period w/o veto by 3% FPS holders) have unlimited mint/burn/allowance power over ZCHF (allowanceInternal returns INFINITY for minters and positions of minters).
- Position owner: onlyOwner on adjust/mint/repay/withdraw. Hub-only: notify*, reduceLimitForClone, initializeClone.
- Permissionless: launchChallenge, bid, splitChallenge, end, returnPostponedCollateral, Equity.onTokenTransfer/redeem, suggestMinter, openPosition (any collateral token), clonePosition, bridge mint/burn, ZCHF.burn.
- Collateral tokens are arbitrary, untrusted ERC20 (hub trusts collateral.transfer/transferFrom semantics, no SafeERC20).

## Attack Surface Priority
1. MintingHub bid/end/split accounting (bid refunds, splitChallenge bid proration, challenge deletion/reuse, challenger-controlled recipient, end() on partially-consumed collateral).
2. Position accounting: price set at clone, limit reduction, challengedAmount, adjust ordering, notifyChallengeSucceeded rounding/repayment vs reserve.
3. Frankencoin reserve accounting: minterReserveE6 vs real reserve, burnFrom/burnWithReserve/notifyLoss, mint fee/reserve split.
4. Equity: voting anchor arithmetic, restructureCapTable (loop uses addressesToWipe[0]), bonding curve rounding/first-share edge cases, delegate cycle recursion in canVoteFor.
5. StablecoinBridge: decimals/limit, fee-on-transfer, ERC677 paths.
6. Custom ERC20: allowance, ERC677 transferAndCall, permit.

## Novel Code (not from libraries)
Everything: auction mechanism, reserve accounting, voting anchors, cubic-root bonding curve, clone factory, custom ERC20.

## Detection Primer
Loaded: domains/defi/primers/defi-staking-governance.md, domains/defi/primers/bridge-crosschain.md

## Activated Modules
| Module | Trigger Evidence |
|--------|-----------------|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/governance-voting.md | Equity vote-weight, checkQualified, veto of minters/positions |
| domains/defi/modules/economic-design.md | Bonding curve, reserve/fee economics |
| domains/defi/modules/lending-liquidation-deep.md | Position collateral/liquidation auction in MintingHub |
| domains/defi/modules/vault-share-accounting.md | Equity share issuance/redemption (share-price math) |
| domains/defi/modules/flash-loan-interaction.md | FPS mint/redeem and vote-weight, bids funded with ZCHF |

## Relevant Checklists
Stablecoin: undercollateralized minting, reserve insolvency / notifyLoss mint inflation, auction gaming. Governance: flash-loan/ vote-anchor manipulation, delegate loops. Share curve: path independence, rounding, first depositor. ERC20 compliance: custom allowance/ERC677.

## Maturity
| Contract | Prior Audit? | Test File? | TODO/FIXME? | Maturity |
|---|---|---|---|---|
| all | Blockbite (pre-contest) | hardhat + forge tests | MintingHub TODO | MintingHub +10 immaturity |
