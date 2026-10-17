# ChainSec Recon Report

## Protocol Overview
- Name: Arcade.xyz governance (Council Framework based)
- Type: Governance/DAO with voting vaults, token, NFT multiplier, treasury, airdrop — keys: governance, nft-gamefi, staking
- Dependencies: OpenZeppelin (ERC20/ERC1155/AccessControl/Ownable/MerkleProof), Council (CoreVoting, GSCVault, Authorizable, Timelock — out of scope, in contracts/external/council)
- Compiler: solidity 0.8.18
- Scope size: 12 files, ~2,900 file LOC (README: 979 SLOC)
- Facts mode: regex — structural facts are pattern-matched, not compiler-verified (lower confidence). `solc` is not installed and no compiler run was done. The Foundry build was not attempted.
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded

## File Risk Table (MANDATORY — Detection phase follows this)
Codebase size category: SMALL (≤15), so all files DEEP. Immaturity: all files appear in Omniscia2023 audit scope (assumed) and have tests; no TODO/FIXME found; no immaturity bonus applied.
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|---|---|---|---|---|---|---|---|
| 1 | contracts/NFTBoostVault.sol | 128.3 | DEEP | 706 | 4 | 12 | voting power, delegation history, NFT boost, withdraw locks |
| 2 | contracts/ArcadeTreasury.sol | 111.9 | DEEP | 398 | 3 | 12 | spend/approve, GSC allowance, batchCalls, ETH |
| 3 | contracts/ARCDVestingVault.sol | 93.2 | DEEP | 384 | 5 | 6 | grants, vesting, revoke, delegation |
| 4 | contracts/token/ArcadeTokenDistributor.sol | 92.0 | DEEP | 180 | 6 | 7 | one-shot distribution |
| 5 | contracts/nft/ReputationBadge.sol | 61.1 | DEEP | 222 | 1 | 4 | merkle-claim ERC1155, fees |
| 6 | contracts/token/ArcadeAirdrop.sol | 42.0 | DEEP | 80 | 1 | 2 | merkle airdrop + vault deposit (ArcadeMerkleRewards) |
| 7 | contracts/BaseVotingVault.sol | 37.05 | DEEP | 201 | 0 | 3 | base of vaults, manager/timelock, delegation helpers |
| 8 | contracts/token/ArcadeToken.sol | 31.55 | DEEP | 171 | 0 | 2 | mint cap/rate |
| 9 | contracts/nft/BadgeDescriptor.sol | 22.1 | DEEP | 62 | 0 | 1 | tokenURI |
| 10 | contracts/ImmutableVestingVault.sol | 17.15 | DEEP | 43 | 0 | 0 | revokeGrant disabled |
| 11 | contracts/ArcadeGSCVault.sol | 17.0 | DEEP | 40 | 0 | 0 | wrapper of Council GSCVault |
| 12 | contracts/ArcadeGSCCoreVoting.sol | 16.65 | DEEP | 33 | 0 | 0 | wrapper of Council CoreVoting |

Supporting (not scored, scope-expansion by inheritance/use): contracts/libraries/{HashedStorageReentrancyBlock, NFTBoostVaultStorage, ARCDVestingVaultStorage, ArcadeMerkleRewards}.sol; contracts/external/council/* (out of scope, but integration is reviewable).

## Fund Flows
- ArcadeToken minted to Distributor, which sends to Airdrop, vesting vaults, treasury, etc.
- Users deposit ERC20 into NFTBoostVault (optionally with ERC1155 badge). Withdraw is gated by `locked`/timelock. Airdrop claims can deposit straight into the vault (ArcadeMerkleRewards.votingVault).
- ARCDVestingVault: manager adds grants (tokens in), user claims vested, manager revokes (returns unvested).
- Treasury: governance spends/approves ERC20/ETH with spend thresholds. GSC has a bounded allowance per period.
- ReputationBadge: users mint with mint price in ETH, manager withdraws fees.

## Trust Boundaries
- Vault `manager` (setMultiplier, grants, revoke) and `timelock` (change manager/timelock, unlock withdrawals).
- Treasury roles: ADMIN, CORE_VOTING, GSC_CORE_VOTING, SPENDER-type; batchCalls arbitrary calls.
- Token minter, Airdrop owner/authorized, Distributor owner, Badge manager/merkle roots.
- Permissionless: `updateVotingPower`, `claim`/airdrop claims, deposit/withdraw, delegate, badge claim.

## Attack Surface Priority
1. NFTBoostVault: voting-power accounting (history, delegation, multiplier updates, ERC1155 handling, addNftAndDelegate/addTokens/withdraw paths, unlocked withdraw).
2. ARCDVestingVault: grant creation/revoke/claim, delegation and voting-power consistency, cliff/unlock semantics, withdraw balances.
3. ArcadeTreasury: threshold checks, GSC allowance windows, approve/spend, ETH and batchCalls auth.
4. ReputationBadge, ArcadeAirdrop and ArcadeMerkleRewards: merkle proof/leaf construction, claim expirations, delegate-and-deposit path.
5. ArcadeToken minting limits, Distributor one-time set.
6. Custom storage reentrancy block (HashedStorageReentrancyBlock) and storage pointer layout (NFTBoostVaultStorage/ARCDVestingVaultStorage).

## Novel Code (not from libraries)
Everything in `contracts/` outside external/, plus custom `Storage.Pointer` style storage and HashedStorageReentrancyBlock.

## Detection Primer
Loaded: domains/defi/primers/defi-staking-governance.md, domains/defi/primers/gamefi-nft.md

## Activated Modules
| Module | Trigger Evidence |
|---|---|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/governance-voting.md | CoreVoting, delegation and voting power in vaults |
| domains/defi/modules/economic-design.md | Vesting, mint caps, mint price, spend thresholds |
| domains/defi/modules/token-flow-tracing.md | ERC20 transfers in vaults, treasury, airdrop, distributor |
| domains/defi/modules/flash-loan-interaction.md | Deposit/withdraw with voting power in same-block flows |
| domains/defi/modules/multi-tx-attack.md | Deposit/delegate/withdraw/claim sequences |
| chains/solidity/modules/eip-standard-compliance.md | ERC20/ERC1155/ERC20Permit implementations |

## Relevant Checklists
Governance/DAO: flash loan voting, snapshot manipulation, delegation accounting, timelock bypass. NFT/ERC1155: callback reentrancy, approval scope. Staking: dust and rounding, withdraw gating.
