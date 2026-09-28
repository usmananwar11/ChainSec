# External Protocol Integration Module

> **Trigger**: Protocol integrates with Uniswap, Aave, Compound, Curve, Chainlink, Convex, Lido, or any external DeFi protocol
> **Inject into**: Lens C (External/Cross-contract)
> **Priority**: HIGH — composability bugs are the hardest to catch and the most impactful

## 1. Integration Inventory

| External Protocol | Version | Functions Called | Our Functions That Call It | Data Dependency |
|-------------------|---------|-----------------|---------------------------|----------------|
| {name} | {v2/v3/etc} | {specific functions} | {our callers} | {what we read/write} |

## 2. Permissionless Function Check (CRITICAL)

For EACH external function the contract calls:
- Can ANYONE call this function on behalf of our contract's address?
- Examples that catch people: Convex `getReward(address,bool)`, Aave `claimRewards`, Compound `claimComp`
- If YES → our contract cannot assume it's the only caller → front-running risk

## 3. Shutdown/Deprecation

For each external dependency:
- What happens if the external pool/market/vault is shut down?
- Does our function revert (users bricked), silently fail, or handle it?
- Is there a governance function to update/migrate the dependency?
- Has the external protocol EVER shut down a pool/market? (Aave v1→v2, Compound v2→v3 migrations)

## 4. Silent Failure

Does the external function ever return without effect instead of reverting?
- Chain-specific checks: see the pack's modules/external-protocol-integration.md.
- Curve `exchange` with killed pool → different behavior per version

If our contract uses a CALCULATED expected amount instead of checking ACTUAL balance change → wrong accounting.

## 5. Return Value vs Balance Delta

| External Call | Expected Return | Actual Check Method | Correct? |
|---------------|----------------|--------------------|---------|
| `swap()` | `amountOut` return value | ??? | Should check `balanceOf` delta |
| `getReward()` | `earned()` pre-call | ??? | Should check balance delta — front-run risk |
| `withdraw()` | `amount` param | ??? | Should check actual received |

## 6. Version-Specific Gotchas

Chain-specific checks: see the pack's modules/external-protocol-integration.md.
