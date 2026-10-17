# ChainSec Security Audit Report

**Target**: INIT Capital (C4 2023-12 invitational lending money market)
**Date**: 2026-10-16
**Auditor**: ChainSec
**Scope**: 17 Solidity files under `contracts/`: core (InitCore, PosManager, Config, LiqIncentiveCalculator), lending_pool (LendingPool, DoubleSlopeIRM), hook (MoneyMarketHook), oracle (InitOracle, Api3OracleReader), risk_manager (RiskManager), helper/rebase_helper (mUSDUSDYHelper, BaseRebaseHelper), common (AccessControlManager, UnderACM, Multicall, TransparentUpgradeableProxyReceiveETH, UncheckedIncrement)

---

## Executive Summary

The audit covered the INIT Capital core, lending pool, hook, oracle, risk-manager and helper contracts. Three verified findings remain after the kill gates: one High (any position owner can unwrap LP and harvest rewards from other positions' collateralized wLp NFTs) and two Medium (a same-timestamp debt-update underflow that can block liquidations, and stranded repay overpayments in MoneyMarketHook). All findings are reasoned from code traces only; no executable PoCs were run, so the two Medium findings are conditional and the High should be confirmed with a PoC before remediation sign-off.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 2 |
| Low | 0 |

---

## Findings

### [SOL-001] removeCollateralWLpTo skips tokenId membership check on partial or zero removal, so any position owner can unwrap LP and harvest rewards of other positions' wLp NFTs — HIGH

**File**: `contracts/core/PosManager.sol:249`
**Category**: access-control
**Evidence**: REASONED (code trace only, no executable PoC run) [CODE-TRACE]
**Status**: verified

**Affected locations** (3):

| File | Line | Function |
|------|------|----------|
| `contracts/core/PosManager.sol` | 249-268 | `removeCollateralWLpTo` |
| `contracts/core/InitCore.sol` | 264-279 | `decollateralizeWLp` |
| `contracts/core/InitCore.sol` | 317-353 | `liquidateWLp` |

**Description**:
Discovery: Q4 edge-case (param _amt=0 / partial boundary), MODIFIER-01 sibling diff. Confirms and deepens DP1-1. getCollWLpAmt and harvestTo check ids[_wLp].contains(_tokenId), but removeCollateralWLpTo only reaches ids.remove(_tokenId) when newWLpAmt == 0. For _amt < balanceOfLp(_tokenId) (including _amt == 0) the caller-supplied tokenId is never tied to _posId, while PosManager is the ERC721 owner of every collateralized wLp NFT, so _harvest and unwrap (both onlyOwner(id) in the wLp) succeed for a foreign NFT. liquidateWLp reaches the same path with a foreign _tokenId: getCollWLpAmt returns 0 for a non-member, wLpAmtToBurn = 0, and removeCollateralWLpTo(_posId, _wLp, foreignId, 0, liquidator) harvests the victim NFT's rewards into pendingRewards[_posId]. Full removal is blocked by the NOT_CONTAIN check, so the drain is capped at balanceOfLp - 1 per NFT.

State-analysis view (STATE-1): the NFT's LP balance falls and rewards are booked to pendingRewards[_posId] of the acting position, while the owning position still lists the tokenId and its collateral valuation (read live from balanceOfLp) shrinks without that position having acted. The attacker then calls claimPendingRewards to take the harvested rewards.

**Impact**:
Who: owners of positions with collateralized wLp NFTs. Loses: LP tokens backing the NFT (all but 1 unit), accrued wLp rewards, and the victim position becomes undercollateralized. Magnitude: up to balanceOfLp(tokenId) - 1 per NFT.

**Preconditions (caveat)**: a whitelisted wLp NFT is collateralized by another position

**Proof of Concept** (code trace, not executed):
```
1. Victim collateralizes wLp NFT N (balanceOfLp = 1000) in position V.
2. Attacker owns any position A and calls decollateralizeWLp(A, wLp, N, 999, attacker).
3. removeCollateralWLpTo: newWLpAmt = 1 != 0, membership check skipped; _harvest credits N's rewards to A; unwrap(N, 999, attacker) runs as PosManager (owner).
4. ensurePositionHealth(A) checks only A, which is unchanged, and passes.
5. Attacker calls claimPendingRewards(A, rewardTokens, attacker) to take N's rewards; the victim position V still lists N but its valuation collapses.
```

**Root Cause**:
Position-to-token membership is enforced only on the newWLpAmt == 0 branch; the partial path trusts the caller-supplied (_wLp, _tokenId) pair and acts on the NFT-global balance.

**Recommendation**:
In PosManager.removeCollateralWLpTo, assert membership before any partial/zero removal, independent of the remaining amount:

_require(posCollInfo.ids[_wLp].contains(_tokenId), Errors.NOT_CONTAIN);
uint newWLpAmt = IBaseWrapLp(_wLp).balanceOfLp(_tokenId) - _amt;
if (newWLpAmt == 0) {
    posCollInfo.ids[_wLp].remove(_tokenId);
    ...
}

This also closes the liquidateWLp path (non-member tokenId with _amt == 0), mirroring the contains() checks already present in harvestTo and getCollWLpAmt.

**Vulnerable Code**:
```solidity
uint newWLpAmt = IBaseWrapLp(_wLp).balanceOfLp(_tokenId) - _amt;
if (newWLpAmt == 0) {
    _require(posCollInfo.ids[_wLp].remove(_tokenId), Errors.NOT_CONTAIN);
    ...
}
_harvest(_posId, _wLp, _tokenId);
IBaseWrapLp(_wLp).unwrap(_tokenId, _amt, _receiver);
```

**Fixed Code** (suggested):
```solidity
uint newWLpAmt = IBaseWrapLp(_wLp).balanceOfLp(_tokenId) - _amt;
if (newWLpAmt == 0) {
    posCollInfo.ids[_wLp].remove(_tokenId);
    ...
}
_harvest(_posId, _wLp, _tokenId);
IBaseWrapLp(_wLp).unwrap(_tokenId, _amt, _receiver);
// preceded at the top of the function by:
_require(posCollInfo.ids[_wLp].contains(_tokenId), Errors.NOT_CONTAIN);
```

---

### [SOL-002] updatePosDebtShares snapshots lastDebtAmt with the pre-operation debt ratio, so a second debt update on the same position and pool in one timestamp underflows — MEDIUM

**File**: `contracts/core/PosManager.sol:170`
**Category**: rounding-dos
**Evidence**: REASONED (code trace only, no executable PoC run) [CODE-TRACE]
**Status**: verified-conditional

**Affected locations** (4):

| File | Line | Function |
|------|------|----------|
| `contracts/core/PosManager.sol` | 170-187 | `updatePosDebtShares` |
| `contracts/core/InitCore.sol` | 141-146 | `borrow` |
| `contracts/core/InitCore.sol` | 544-547 | `_repay` |
| `contracts/lending_pool/LendingPool.sol` | 125-145 | `repay` |

**Description**:
Discovery: Q2 accountant (trace concrete values through rounding). Confirms DP1-3. Traced: totalDebt=1,000,000, totalDebtShares=900,000, position holds all shares. repay(1 share): updatePosDebtShares sets lastDebtAmt = ceil(899,999*1e6/9e5) = 999,999 using the pre-repay ratio; LendingPool.repay then charges ceil(1e6/9e5)=2, leaving totalDebt 999,998 / shares 899,999. A second update at the same timestamp reads debtAmtCurrent = 999,998, so debtAmtCurrent - lastDebtAmt underflows (checked arithmetic) and the borrow/repay/liquidate reverts. Borrow behaves the same because shares round up after the snapshot. A borrower can front-run a liquidation in the same block with a dust repay or borrow. Small debts of low-decimal tokens keep the blockage for several seconds because per-second interest rounds to 0.

**Impact**:
Who: liquidators and borrowers. Loses: liquidations or same-block repay/borrow on the position revert. Magnitude: liveness, per block.

**Preconditions (caveat)**: two debt updates on same position/pool in one timestamp and non-integral debt ratio

**Proof of Concept** (code trace, not executed):
```
1. Position P has debt in pool X with non-integral totalDebt/totalDebtShares.
2. Borrower sends a dust repay (or borrow) in block N before the liquidator's tx.
3. The liquidator's _repay calls updatePosDebtShares with no accrued interest in the same timestamp and underflows.
```

**Root Cause**:
The interest snapshot uses a ratio that the pool's round-up arithmetic immediately lowers, breaking the documented invariant debtAmtCurrent >= lastDebtAmt.

**Recommendation**:
Snapshot lastDebtAmt after the pool has applied its round-up (e.g. call LendingPool.repay/borrow first, then compute newDebtAmt from debtShareToAmtStored for the post-operation shares), or compute the interest delta with a saturating form: `extraInfo.totalInterest += debtAmtCurrent > extraInfo.lastDebtAmt ? (debtAmtCurrent - extraInfo.lastDebtAmt).toUint128() : 0;`. The first option preserves the invariant debtAmtCurrent >= lastDebtAmt.

**Vulnerable Code**:
```solidity
extraInfo.totalInterest += (debtAmtCurrent - extraInfo.lastDebtAmt).toUint128();
...
extraInfo.lastDebtAmt = newDebtAmt.toUint128();
```

**Fixed Code** (suggested):
```solidity
uint debtAmtCurrent = ILendingPool(_pool).debtShareToAmtCurrent(oldShares);
extraInfo.totalInterest += debtAmtCurrent > extraInfo.lastDebtAmt
    ? (debtAmtCurrent - extraInfo.lastDebtAmt).toUint128() : 0;
```

---

### [SOL-003] MoneyMarketHook pulls repay tokens for the requested shares but core repays only min(shares, position debt); excess is stranded in the hook and stealable for WNATIVE — MEDIUM

**File**: `contracts/hook/MoneyMarketHook.sol:145`
**Category**: token-flow
**Evidence**: REASONED (code trace only, no executable PoC run) [CODE-TRACE]
**Status**: verified-conditional

**Affected locations** (3):

| File | Line | Function |
|------|------|----------|
| `contracts/hook/MoneyMarketHook.sol` | 145-159 | `_handleRepay` |
| `contracts/hook/MoneyMarketHook.sol` | 75-80 | `execute` |
| `contracts/core/InitCore.sol` | 533-548 | `_repay` |

**Description**:
Discovery: Q2 value-in vs value-out cross-contract check (hook vs core). The hook computes repayAmt = debtShareToAmtCurrent(_params[i].shares) and pulls that from the user, but InitCore._repay clamps sharesToRepay to the position's actual debt shares and transfers only that amount from the hook. If the position's debt shares dropped between signing and execution (partial liquidation front-run, or the user overshooting to close a debt), the difference stays in the hook. No refund exists. For WNATIVE, returnNative=true unwraps the hook's whole WNATIVE balance and sends the whole ETH balance to the next caller; other tokens are stuck permanently.

**Impact**:
Who: user repaying through the hook. Loses: the overpaid amount (stuck, or taken by whoever next calls execute with returnNative for WNATIVE). Magnitude: difference between requested and actual repaid debt.

**Preconditions (caveat)**: requested repay shares exceed position debt shares at execution

**Proof of Concept** (code trace, not executed):
```
1. User calls hook.execute with repay shares = full debt of a WNATIVE pool position.
2. A liquidator's tx lands first and reduces the position's debt shares.
3. Hook pulls WNATIVE for the full requested shares; core repays only the remaining shares; excess WNATIVE stays in the hook.
4. Attacker calls execute with posId = 0, a valid mode and returnNative = true; the hook unwraps its WNATIVE balance and pays all ETH to the attacker.
```

**Root Cause**:
The hook sizes the pull from caller-supplied shares instead of min(shares, position debt shares) and never refunds leftovers.

**Recommendation**:
In MoneyMarketHook._handleRepay, clamp the requested shares to the position's current debt shares before pulling funds:

uint debtShares = IPosManager(POS_MANAGER).getPosDebtShares(_initPosId, _params[i].pool);
uint shares = _params[i].shares < debtShares ? _params[i].shares : debtShares;
uint repayAmt = ILendingPool(_params[i].pool).debtShareToAmtCurrent(shares);

Also refund any leftover underlying (balance delta) to msg.sender at the end of execute(), and avoid sweeping the hook's entire WNATIVE/ETH balance to an unrelated caller.

**Vulnerable Code**:
```solidity
uint repayAmt = ILendingPool(_params[i].pool).debtShareToAmtCurrent(_params[i].shares);
_ensureApprove(uToken, repayAmt);
IERC20(uToken).safeTransferFrom(msg.sender, address(this), repayAmt);
```

**Fixed Code** (suggested):
```solidity
uint shares = _params[i].shares < debtShares ? _params[i].shares : debtShares;
uint repayAmt = ILendingPool(_params[i].pool).debtShareToAmtCurrent(shares);
_ensureApprove(uToken, repayAmt);
IERC20(uToken).safeTransferFrom(msg.sender, address(this), repayAmt);
```

---

## Security Strengths

- **Access control model**: Config.sol gates parameter setters with `onlyGuardian` and `onlyGovernor` modifiers backed by AccessControlManager (UnderACM base), applied to setPoolConfig, setModeStatus, setMaxHealthAfterLiq_e18 and setWhitelistedWLps.
- **Reentrancy protection**: InitCore.sol applies `nonReentrant` on 14 sites across its state-mutating entry points.
- **Battle-tested dependencies**: Built on OpenZeppelin 4.9.3 (including the Upgradeable variants) with solc 0.8.19, so arithmetic is checked by default.
- **Upgrade safety**: Contracts are deployed behind transparent proxies (TransparentUpgradeableProxyReceiveETH.sol only overrides `receive()`), with admin separated from the user call path.
- **Area for improvement**: LendingPool.sol has no reentrancy guard of its own and relies on InitCore as the only caller for balance-delta accounting; the wLp membership checks in PosManager are inconsistent across functions (see SOL-001).

---

## Architecture Observations

- PosManager and LendingPool use balance-delta accounting (`balanceOf - cash`, `balanceOf(PosManager) - __collBalances[pool]`), which makes ordering of transfers and core calls security-critical; the hook pre-transfers funds before the multicall.
- Membership checks on wLp NFT ids are applied in `harvestTo` and `getCollWLpAmt` but only conditionally in `removeCollateralWLpTo`; a sibling-function diff of every function touching `ids[_wLp]` is worthwhile.
- Debt interest accounting caches `lastDebtAmt` per position and pool; its invariant (`debtAmtCurrent >= lastDebtAmt`) depends on the pool's round-up rules and warrants fuzz/invariant testing.
- MoneyMarketHook holds user position NFTs and approvals and sweeps its full WNATIVE/ETH balance on `returnNative`; a lower-severity candidate (DA-3, downgraded to Low and not reported here) concerns the same sweep behavior.
- The hook, PosManager and InitCore interplay through multicall and health-check deferral is the main complexity hotspot.

---

## Methodology

**Audit mode**: Full pipeline (`quick` = false).

Completed phases: Recon (architecture, fund flows, trust boundaries), Detection (Pass 1, four lenses and final sweep), Rescan, Per-unit deep dives (7 clusters), State Analysis, Verification (kill gates, harm statements, concrete exploit traces). No phases are listed as incomplete.

Tooling and mode notes:
- Facts mode: `compiler`. Preflight tooling mode: `degraded` (slither not installed; no static-analysis pre-scan).
- Methodology limitations: verification was trace-only (code-trace critic); no executable PoCs were run, so every finding carries the REASONED evidence tier. Run `chainsec-poc` on SOL-001 to upgrade it.
- Preflight warnings:
  - slither not installed: degraded mode, no static-analysis pre-scan.
  - facts mode is compiler: initial forge build failed (missing OZ 4.9.3 + forge-std), so OZ 4.9.3 (npm) and forge-std v1.9.7 were installed into gitignored contracts/.cache and lib/ and the extractor was re-run.
  - per-unit: cluster 6 output had depth_evidence as a string; coerced to a list mechanically before merge.
  - per-unit/state phases ran concurrently (state reads only detect.json); no executable PoCs were run (critic is trace-only).
  - AccessControlManager/UnderACM/UncheckedIncrement/Proxy files covered by one small cluster (7); UnderACM repeated in clusters as parent context.
- Verification outcome: 21 candidates after merging, 3 reported (SOL-001 merges DD-1 and STATE-1); 16 killed by gates; 2 Low findings (DA-3 downgraded, DC-4) excluded as Low. No second-opinion review (`A/review.json`) was present.

Methodology derived from Krait by Zealynx Security.

```
───────────────────────────────────────────────────
📋 3 findings saved to .audit/findings.json
───────────────────────────────────────────────────
```

### Next Steps

1. **Review killed findings**: 16 candidates were killed; run `chainsec-review` for a second opinion on gate-killed items.
2. **Prove a finding**: run `chainsec-poc SOL-001` to turn the `[CODE-TRACE]` into an executed `[POC-PASS]` or `[POC-FAIL]`.
3. **Fuzz invariants**: run `chainsec-fuzz` to test `debtAmtCurrent >= lastDebtAmt` and wLp membership invariants.
