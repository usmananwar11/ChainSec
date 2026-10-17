# ChainSec Recon Report

## Protocol Overview
- Name: Unnamed fixture (no README/docs); primary contract `Vault`
- Type: Yield Vault / custom balance-based vault (NOT ERC-4626 — per-user `balances` mapping, no shares) — keys: `vault`
- Dependencies: `Owned` (local abstract base, `src/Base.sol`); `IERC20` interface (inline, `src/Vault.sol`). No external protocol integrations.
- Compiler: `^0.8.20`
- Scope size: 2 files, ~74 LOC (Vault 45 LOC + Owned 16 LOC of units; counters: Vault 55, Base 19)
- Facts mode: compiler
- Analyzers: slither: SKIPPED (not available)
- Native asset price (USD, for Gate F): not recorded

## File Risk Table (MANDATORY — Detection phase follows this)
| Rank | File | RISK_SCORE | Tier | LOC | Ext Calls | State Writers | Notes |
|------|------|-----------|------|-----|-----------|---------------|-------|
| 1 | src/Vault.sol | 85.75 | DEEP | 55 | 3 | 5 | Base 75.75 + immaturity +10: no prior audit, no README/docs, contains unfinished marker (`BUG (planted for smoke tests)` comment). Handles ERC20 + native funds. |
| 2 | src/Base.sol | 29.95 | DEEP | 19 | 0 | 1 | Base 19.95 + immaturity +10: no prior audit and no dedicated test file for `Owned`. Parent promoted (inherited by Vault). |

Codebase size category: SMALL (2 files, ≤15) — all files are effectively Tier 1 (DEEP).

Immaturity judgement: neither file is referenced by any prior audit or README, and `src/Vault.sol`
carries an explicit unfinished/planted-bug marker, so both get `immaturity_bonus = +10`. Adjusted
scores do not change any tier (both already DEEP).

## Fund Flows
- **ERC20 entry**: `deposit(amount)` → `token.transferFrom(msg.sender, address(this), amount)`, then credits `balances[msg.sender]` and `totalDeposits`. Permissionless.
- **Native entry**: `depositEth()` payable → credits `balances[msg.sender] += msg.value` only. It does NOT update `totalDeposits`, and there is no accounting linking ETH to the ERC20 ledger.
- **ETH exit**: `sweep(address payable to)` → `to.transfer(address(this).balance)` — sends the ENTIRE native balance to an arbitrary `to`, with NO access control and NO connection to `balances`.
- **ERC20 exit**: `withdraw(amount)` → debits `balances[msg.sender]`, decrements `totalDeposits` under `unchecked`, then `token.transfer(msg.sender, amount)`. State is updated before the external call (CEI respected for the token path), but no return-value check and no reentrancy guard.
- No fee is ever actually applied: `FEE_BPS` is a constant that is never read; `setFee` is a no-op empty body.

## Trust Boundaries
- **Owner** (`Owned.owner`, set to deployer): can `transferOwnership`. `onlyOwner` guards `setFee` (a no-op) and `transferOwnership`. Owner has NO power over funds.
- **Permissionless (any caller)**: `deposit`, `depositEth`, `withdraw`, `sweep`, `balanceOf`.
- **Critical**: `sweep` is permissionless and moves the whole native balance to an attacker-chosen address. Anyone can drain all ETH held by the vault (including ETH credited to other users via `depositEth`).
- The vault trusts the ERC20 `token` to behave (no return-value checks); token address is immutable.

## Attack Surface Priority
1. **`sweep` — unrestricted native drain (src/Vault.sol:32).** No access control: any address can send `address(this).balance` to themselves. Highest-severity fund-theft path.
2. **ETH/ERC20 ledger desync (src/Vault.sol:27 vs :21/:36).** `depositEth` credits `balances` without touching `totalDeposits`, and `withdraw` decrements `totalDeposits` under `unchecked` while paying out ERC20. Native deposits are unwithdrawable via `withdraw` and governable only via the drainable `sweep`; `totalDeposits` does not track ETH at all.
3. **`unchecked` underflow in `withdraw` (src/Vault.sol:38-40).** `totalDeposits -= amount` is unchecked; `balances[msg.sender] -= amount` is checked (reverts) but the ordering/unchecked block is a correctness hazard.
4. **ERC20 return values ignored (src/Vault.sol:22,41).** Non-reverting/false-returning tokens would let deposits be credited without funds moving, or withdrawals silently not pay out.
5. **No reentrancy guard on `withdraw`** — state-before-call is correct today, but the token is untrusted.

## Novel Code (not from libraries)
- The entire `Vault` contract is bespoke — no OpenZeppelin/Solmate/Solady. The `balances`/`totalDeposits` ledger, the native `depositEth`/`sweep` pair, and the no-op `setFee`/unused `FEE_BPS` are all custom.
- `Owned` is a minimal hand-rolled ownership base (not from a standard library).

## Detection Primer
Loaded: domains/defi/primers/defi-lending.md is NOT relevant; no dedicated vault primer exists in the pack. Primary evidence source is the vault/economics/token-flow modules below. (No `primers/` entry applies; the pack's `vault` list pulls `../../domains/defi/modules/vault-share-accounting.md` and the chain `modules/erc4626-vault-deep.md`.)

## Activated Modules
| Module | Trigger Evidence |
|--------|-----------------|
| domains/defi/modules/access-control-state.md | Always active |
| domains/defi/modules/vault-share-accounting.md | Protocol type `vault`; custom deposit/withdraw with `balances`/`totalDeposits` accounting (src/Vault.sol:13-14,21-42). Note: share-less custom ledger, not ERC-4626. |
| chains/solidity/modules/erc4626-vault-deep.md | Protocol type `vault` (per pack `modules_by_protocol`). Not a true ERC4626 implementation; selected by type. |
| domains/defi/modules/flash-loan-interaction.md | `balanceOf(address(this))`-equivalent native balance read via `address(this).balance` in `sweep`; permissionless `deposit`/`withdraw` composable in one tx (src/Vault.sol:32-42). |
| domains/defi/modules/token-flow-tracing.md | `transferFrom` in `deposit`, `transfer` in `withdraw` (src/Vault.sol:22,41) |
| domains/defi/modules/economic-design.md | Fee constant `FEE_BPS = 30` and `setFee` present (src/Vault.sol:15,44), though never applied |

## Relevant Checklists
- **Yield Vault / ERC4626**: first-depositor/share inflation is N/A (no shares); focus on deposit/withdraw accounting correctness, donation-style desync of `totalDeposits` vs actual token balance, and rounding (none here).
- **Access control**: every state-changing external function must be gated appropriately — `sweep` is not.
- **Native-asset handling**: ETH credited via `depositEth` must be withdrawable by the correct party and not drainable by others.
- **Token integration**: ERC20 return values, fee-on-transfer tokens, non-standard tokens.
- **Arithmetic**: `unchecked { totalDeposits -= amount }` underflow/desync.
