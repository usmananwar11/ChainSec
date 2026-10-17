# ChainSec Recon Report

## Protocol Overview
- Name: Vault (smoke-test fixture)
- Type: Yield Vault / deposit-withdraw custody — keys: vault
- Dependencies: none (local IERC20 interface; no libraries)
- Compiler: solidity ^0.8.20
- Scope size: 2 files, 74 LOC
- Facts mode: compiler
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded

## File Risk Table (MANDATORY — Detection phase follows this)
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|------|------|-----------|------|-----|-----------|---------------|-------|
| 1 | src/Vault.sol | 85.75 | DEEP | 55 | 3 | 5 | Holds ERC20 + native balances. immaturity +10: test/VaultTest.sol only has an empty `testNothing`, no real coverage; no audit referenced |
| 2 | src/Base.sol | 29.95 | DEEP | 19 | 0 | 1 | Owned base inherited by Vault. immaturity +10: no test coverage, no audit referenced |

Codebase size category: SMALL (≤15)

## Fund Flows
- In: `deposit` (ERC20 via transferFrom; credits `balances` and `totalDeposits`), `depositEth` (payable; credits `balances` only, not `totalDeposits`).
- Out: `withdraw` (debits `balances`, `unchecked` debit of `totalDeposits`, ERC20 transfer), `sweep` (sends the whole native balance to any `to`).
- The two assets share one `balances` ledger: ETH deposits can be withdrawn as tokens and vice versa.

## Trust Boundaries
- Owner (`Owned.owner`, set to deployer, transferable): `setFee` (empty body), `transferOwnership`.
- Permissionless: `deposit`, `depositEth`, `withdraw`, `sweep`, views.
- Trusted external: `token` (immutable, unknown ERC20; return values of transfer/transferFrom are never checked).

## Attack Surface Priority
1. `sweep` — no access control, drains native balance to any address.
2. `depositEth` / `withdraw` — shared ledger across ETH and token; ETH credits redeemable as tokens.
3. `withdraw` — `unchecked` `totalDeposits` subtraction desyncs with ETH credits (ETH never added to `totalDeposits`); unchecked ERC20 return values in `deposit`/`withdraw`.
4. `FEE_BPS` / `setFee` — fee is declared but never applied.

## Novel Code (not from libraries)
All of it: Vault accounting, `sweep`, custom Owned (no two-step transfer, no zero-address check), dead `_selfBalance` assembly helper.

## Detection Primer
Loaded: domains/defi/primers (vault key has no primer; `always` module only)

## Activated Modules
| Module | Trigger Evidence |
|--------|-----------------|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/vault-share-accounting.md | Vault key: balance ledger with deposit/withdraw in src/Vault.sol |
| chains/solidity/modules/erc4626-vault-deep.md | Vault key (no share token, so low relevance) |
| domains/defi/modules/flash-loan-interaction.md | Vault key |

## Relevant Checklists
Yield vault: first-depositor/donation, rounding, accounting sync between ledgers, unchecked token return values, access control on value-moving functions.
