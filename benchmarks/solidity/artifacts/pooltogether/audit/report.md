# ChainSec Security Audit Report

**Target**: PoolTogether V5 PrizeVault (C4 2024-03-pooltogether)
**Date**: 2026-10-13
**Auditor**: ChainSec
**Scope**: src/PrizeVault.sol, src/PrizeVaultFactory.sol, src/TwabERC20.sol, src/abstract/Claimable.sol, src/abstract/HookManager.sol, src/interfaces/IVaultHooks.sol (6 files, 1419 LOC)

---

## Executive Summary

ChainSec audited the PrizeVault ERC4626 prize-savings vault, its factory, the TWAB-backed share token and the claim/hook modules. One verified High-severity accounting bug was found: `claimYieldFeeShares` clears the whole yield fee balance on a partial claim, so the unclaimed fee entitlement is lost to the liquidation path. Other candidates were killed by the verification gates. Overall risk is moderate, concentrated in the yield-fee accounting.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 0 |
| Low | 0 |

---

## Findings

### [SOL-001] claimYieldFeeShares subtracts the full cached yieldFeeBalance instead of the claimed shares — HIGH

**File**: `src/PrizeVault.sol:611`
**Category**: accounting
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
`yieldFeeBalance` is a debt counter read by `_totalDebt`, `totalYieldBalance`, `availableYieldBalance`, `liquidatableBalanceOf` and `transferTokensOut`. Its only decrementing writer, `claimYieldFeeShares`, mints `_shares` but subtracts the cached full balance. After a partial claim the unclaimed fee entitlement leaves `totalDebt`, so the backing assets become available yield and can be liquidated to the prize pool. The fee recipient permanently loses the remainder.

**Impact**:
The yield fee recipient loses the unclaimed fee shares after any partial claim (`yieldFeeBalance - _shares`, e.g. 900 of 1000 fee shares). The backing assets go to the prize pool and liquidation pair takers. Precondition: `yieldFeeBalance > 0` and the recipient claims fewer shares than the balance.

**Proof of Concept**:
```
1. Liquidations accrue yieldFeeBalance = 1000.
2. yieldFeeRecipient calls claimYieldFeeShares(100): 100 shares minted, yieldFeeBalance set to 0.
3. totalDebt drops by 900 relative to the correct value; 900 assets of backing are now counted as available yield.
4. liquidationPair liquidates that yield; the recipient can never claim the remaining 900.
```
No executed PoC was run (a PoC is recommended).

**Root Cause**:
`yieldFeeBalance -= _yieldFeeBalance` (cached full balance) is used instead of `-= _shares`.

**Recommendation**:
Replace the subtraction with `yieldFeeBalance -= _shares;`. Totals then stay consistent because `totalSupply` rises by `_shares` while `yieldFeeBalance` falls by the same amount, so `_totalDebt` is unchanged by a claim.

**Vulnerable Code**:
```solidity
yieldFeeBalance -= _yieldFeeBalance;

_mint(msg.sender, _shares);
```

**Fixed Code** (suggested):
```solidity
yieldFeeBalance -= _shares;

_mint(msg.sender, _shares);
```

---

## Security Strengths

- **Access control model**: Privileged paths use explicit guards: `onlyOwner` on the four setters, `onlyLiquidationPair` on `transferTokensOut`/`verifyTokensIn`, `onlyYieldFeeRecipient` on `claimYieldFeeShares`, `onlyClaimer` on `claimPrize`.
- **Battle-tested dependencies**: OpenZeppelin ERC20, ERC20Permit, SafeERC20, Math and SafeCast are used, with the owner-manager-contracts `Ownable`.
- **Arithmetic safety**: Solidity ^0.8.24 checked math, with only four `unchecked` blocks in PrizeVault.sol; share supply is bounded through SafeCast to the TwabController uint96 limit.
- **Input validation**: `claimYieldFeeShares` rejects zero shares and shares above the fee balance; the yield fee percentage is capped (<= 90%) and the claimer, liquidation pair and yield vault are address-validated.
- **Area for improvement**: `_setYieldFeeRecipient` accepts `address(0)` (unlike the sibling setters); the finding was killed as an owner-recoverable misconfiguration, but a zero-address check would be consistent.

---

## Architecture Observations

- PrizeVault.sol (962 LOC) holds nearly all logic: a custom non-standard ERC4626 with dust sweeping, a yield buffer, a virtual yield-fee share counter, and the liquidation-source interface. It is the main complexity hotspot, and `yieldFeeBalance` is coupled to `totalSupply` in `_totalDebt`, so every writer of either needs invariant tests.
- Only two code paths write `yieldFeeBalance` (`transferTokensOut` increments, `claimYieldFeeShares` decrements). A fuzz/invariant test on "claim leaves `totalDebt` unchanged" would have caught SOL-001.
- Edge cases killed by the gates but worth testing: `convertToShares`/`maxRedeem` division by zero when `totalAssets() == 0` with debt outstanding (requires total yield-vault loss), and `claimYieldFeeShares` reverting near the uint96 supply cap (listed as a known limitation).

---

## Methodology

**Audit mode**: Full pipeline (`quick` = false).

Completed phases: Recon, Detection, Rescan, Per-unit deep dives, State Analysis, Verification. No phases are incomplete.

Mode notes: facts mode `compiler`; preflight tooling mode `degraded` because slither was unavailable (the static-analysis signal table was skipped during recon; python3 and forge were present). Warnings: rescan reinforced DA-1 (the claimYieldFeeShares finding). Verification was by code trace; no PoC was executed.

Methodology derived from Krait by Zealynx Security.
