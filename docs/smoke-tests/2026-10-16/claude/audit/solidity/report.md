# ChainSec Security Audit Report

**Target**: Vault (smoke-test fixture)
**Date**: 2026-10-16
**Auditor**: ChainSec
**Scope**: `src/Vault.sol`, `src/Base.sol`

---

## Executive Summary

The audit covered a small custody vault (`Vault`, inheriting `Owned`) that accepts one immutable ERC20 and native ETH. Three issues were verified: an unprotected `sweep()` that lets anyone take the vault's whole native balance, a shared ETH/token ledger that lets an ETH depositor withdraw other users' tokens, and the absence of any ETH withdrawal path. Overall risk is critical: user funds in the contract can be stolen by any account.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 2 |
| Medium | 0 |
| Low | 0 |

---

## Findings

### [SOL-001] sweep() has no access control: anyone can send the vault's entire native balance to any address — CRITICAL

**File**: `src/Vault.sol:32`
**Category**: access-control
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
Discovery: Q3.7 / MODIFIER-01. sweep() is external with no guards (facts.json entry_points guards = []), while setFee and transferOwnership use onlyOwner. It transfers address(this).balance to a caller-chosen address. The in-code comment marks it a planted bug, so it is not intentional design; known-issues.md lists nothing.

**Impact**:
every user who called depositEth lose all ETH they deposited (100% of the vault's native balance in one call).

**Proof of Concept**:
```
1. Victims call depositEth() and the vault holds N wei.
2. Attacker calls sweep(attacker) from any EOA.
3. to.transfer(address(this).balance) sends N wei to the attacker.
4. Victims' balances[] entries still show N wei credited but nothing backs them.
```

**Root Cause**:
A value-moving function lacks any caller check and ignores the per-user balances ledger that depositEth maintains.

**Recommendation**:
Restrict sweep() to the owner (and ideally stop it ignoring user balances): See the fixed code in the report.

**Vulnerable Code**:
```solidity
function sweep(address payable to) external {
    to.transfer(address(this).balance);
}
```

**Fixed Code** (suggested):
```solidity
function sweep(address payable to) external onlyOwner {
    (bool ok, ) = to.call{value: address(this).balance}("");
    require(ok, "sweep failed");
}
```

---

### [SOL-002] ETH and token deposits share one balances ledger: an ETH depositor can withdraw other users' tokens — HIGH

**File**: `src/Vault.sol:27`, `src/Vault.sol:36`
**Category**: accounting
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
Discovery: Q3.2 (paired operation symmetry) and BL-03 (dual accounting). depositEth() credits balances[msg.sender] by msg.value, and withdraw() debits the same mapping but pays out `token`. The two assets are different, with no conversion or price relation, so wei credited by ETH can be redeemed one-for-one as token units.

**Impact**:
ERC20 depositors lose their deposited tokens (up to the vault's whole token balance, for a cost of the same number of wei).

**Proof of Concept**:
```
1. Victims deposit 1,000,000 token units via deposit().
2. Attacker calls depositEth{value: 1_000_000 wei}(), crediting balances[attacker] = 1,000,000.
3. Attacker calls withdraw(1_000_000): the balances debit passes, and token.transfer sends 1,000,000 token units to the attacker.
4. The attacker's 1,000,000 wei stays in the vault, so the victims' tokens are gone and the attacker can recover the wei through sweep().
```

**Root Cause**:
A single balances mapping tracks two unrelated assets, and withdraw() only pays the ERC20.

**Recommendation**:
Track ETH and tokens in separate ledgers (e.g. `mapping(address => uint256) ethBalances;`) so withdraw() only debits token credits, and add a dedicated withdrawEth() that debits ethBalances: See the fixed code in the report.

**Vulnerable Code**:
```solidity
function depositEth() external payable {
    balances[msg.sender] += msg.value;
}
...
function withdraw(uint256 amount) external {
    balances[msg.sender] -= amount;
    unchecked { totalDeposits -= amount; }
    token.transfer(msg.sender, amount);
}
```

**Fixed Code** (suggested):
```solidity
function depositEth() external payable {
    ethBalances[msg.sender] += msg.value;
}

function withdraw(uint256 amount) external {
    balances[msg.sender] -= amount;
    totalDeposits -= amount;
    require(token.transfer(msg.sender, amount), "transfer failed");
}
```

---

### [SOL-003] No way to withdraw ETH: ETH deposits are only recoverable as tokens or taken by sweep() — HIGH

**File**: `src/Vault.sol:27`, `src/Vault.sol:36`
**Category**: missing-functionality
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
Discovery: Module W / MISSING-02 (exit-path coverage). The only native-value exit is sweep(), which ignores balances[]. withdraw() pays only the ERC20. An ETH depositor therefore has no path to reclaim their ETH. If the vault holds no tokens, withdraw reverts at the transfer or pays nothing, and their credit is worthless.

**Impact**:
ETH depositors lose their deposited ETH, permanently locked or stolen by the first sweep caller (100% of each ETH deposit).

**Proof of Concept**:
```
1. Alice calls depositEth{value: 1 ether}() and balances[alice] = 1e18.
2. Alice calls withdraw(1e18). With no token balance in the vault, token.transfer cannot pay and the call reverts or pays nothing of value.
3. No other function sends ETH against balances[alice].
4. Any observer can call sweep() and take Alice's ETH.
```

**Root Cause**:
depositEth() credits a ledger entry, but no function pays ETH out against it.

**Recommendation**:
Add an ETH exit path that debits the ETH ledger and pays the caller, and remove or restrict sweep(): See the fixed code in the report.

**Vulnerable Code**:
```solidity
function depositEth() external payable {
    balances[msg.sender] += msg.value;
}
```

**Fixed Code** (suggested):
```solidity
function withdrawEth(uint256 amount) external {
    ethBalances[msg.sender] -= amount;
    (bool ok, ) = msg.sender.call{value: amount}("");
    require(ok, "eth transfer failed");
}
```

---

## Security Strengths

- **Compiler safety**: Both files use `pragma solidity ^0.8.20`, so arithmetic is checked by default; the only `unchecked` block (`Vault.withdraw`) is a weakness, not a strength.
- **Access control model**: `Owned` in `src/Base.sol` implements a simple `onlyOwner` modifier that guards `transferOwnership` and `Vault.setFee`.
- **Immutability**: `Vault.token` is `immutable`, so the custodied asset cannot be swapped after deployment.
- **Dependencies**: The vault has no external library dependencies and a minimal local `IERC20` interface, keeping the attack surface small.
- Area for improvement: Test coverage is effectively absent (`test/VaultTest.sol` only has an empty `testNothing`), and no audit is referenced.

---

## Architecture Observations

- `Vault` mixes two assets in one `balances` mapping while `totalDeposits` only tracks the ERC20; this coupling is the source of the accounting findings.
- `FEE_BPS` and `setFee` are declared but never applied (`setFee` has an empty body), and `_selfBalance` is dead code.
- `Owned` has no two-step ownership transfer and no zero-address check in `transferOwnership`.
- `deposit()` and `withdraw()` ignore the return values of `transferFrom`/`transfer`. A candidate on this was killed by the gates (it depends on an unnamed token), but it is worth hardening with `SafeERC20`.
- Low-severity item not listed above (per report policy): `withdraw()` subtracts `totalDeposits` in an `unchecked` block, which wraps when ETH credits are withdrawn.

---

## Methodology

**Audit mode**: Quick (`--quick`).

Completed phases: Recon, Detection (Pass 1), Rescan, Verification (kill gates, impact premises, exploit traces). Per-unit deep dives and State Analysis were skipped (--quick).

Facts mode: compiler. Preflight tooling mode: degraded (slither not installed; static-analysis signal table skipped). No warnings and no incomplete phases were recorded.

Methodology derived from Krait by Zealynx Security.
