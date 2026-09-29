# Fix and report — Foundry specifics

Supplements `engine/poc/fix-and-report.md`. Moved verbatim from Krait's `fix-and-report.md`.

## Example minimal diff

```diff
- uint256 shares = amount * totalShares / totalAssets;
+ uint256 shares = totalShares == 0
+     ? amount
+     : amount * totalShares / totalAssets;
```

## Report block values

- **File**: test/Victim_exp.sol
- **Command**: forge test --match-contract ExploitTest -vvv
