# Token Flow Tracing Module

> **Trigger**: Any `transfer`, `transferFrom`, `safeTransfer`, `mint`, `burn`, `balanceOf(this)`
> **Inject into**: Lens B (Value/Economic), Lens C (External/Cross-contract)
> **Priority**: HIGH — token handling bugs are the most common source of fund loss

## 1. Token Entry Points

Where can tokens enter the contract?

| Entry Point | Function | Token Type | Tracked By | Bypass Possible? |
|-------------|----------|------------|-----------|-----------------|
| Standard deposit | `deposit()` | ERC-20 | `balances[user]` | N/A |
| Direct transfer | `transfer()` to contract | Any | ??? | YES if no hook |
| Side-effect | External call returns tokens | Various | ??? | Depends |

Chain-specific checks: see the pack's modules/token-flow-tracing.md.

**Key**: If a token can enter via a path that BYPASSES the tracking state variable → accounting mismatch.

## 2. Token State Tracking

For each entry point:
- What state variable tracks the balance?
- Is `balanceOf(address(this))` used directly? → **Donation attack vector**
- Can tracked balance desynchronize from actual balance?

**Red flags**:
- Exchange rate using `balanceOf(this)` directly
- No skim/sync function
- Accounting updated BEFORE transfer completes

## 3. Token Exit Points

| Exit Point | Function | Recipient | Balance Check | CEI Order? |
|------------|----------|-----------|---------------|-----------|
| Fee distribution | `distributeFees()` | treasury | ??? | ??? |
| Liquidation | `liquidate()` | liquidator | ??? | ??? |
| Emergency | `emergencyWithdraw()` | owner/user | ??? | ??? |

Chain-specific checks: see the pack's modules/token-flow-tracing.md.

For each: state updated BEFORE or AFTER transfer? → CEI violation = reentrancy risk.

## 4. Self-Transfer Accounting

For each transfer function: can sender == recipient?
If YES: does a self-transfer update accounting (fees credited, rewards claimed, share ratios changed) without net token movement? → **Finding**.

## 5. Multi-Token Separation

For protocols handling multiple token types:
- Are different types handled by separate code paths?
- Can one type's path be triggered with another? (e.g., calling ERC-721 function with ERC-20 address)
- Native vs wrapped (ETH/WETH) — consistent handling?
- Base vs receipt tokens — can you redeem receipt tokens for more base than deposited?
