### PoC — SOL-002
- **Class**: local
- **File**: .audit/solidity/poc/SOL-002/SOL002.t.sol (exploit, baseline, 1-wei boundary); Sweep.t.sol (fix-efficacy sweep)
- **Command**: `cd <TARGET> && FOUNDRY_TEST=<TARGET>/.audit/solidity/poc/SOL-002 forge test --match-path '*/SOL002.t.sol' -vvv`
- **Result**: PASS (3/3)
- **Evidence**: [POC-PASS]
- **Harm asserted**: victim deposits 1,000,000 token units; attacker (no tokens) depositEth{1e6 wei} + withdraw(1e6) gains exactly 1,000,000 tokens, vault token balance goes to 0, victim's withdraw(1e6) reverts, attacker then recovers the wei via sweep().
- **Pinned (defect-mutation)**: YES — `depositEth` credits `ethBalances` instead of `balances`; exploit tests then fail with arithmetic underflow in withdraw(); baseline still passes.
- **Baseline control**: ETH-less attacker's withdraw reverts; victim withdraws in full.
- **Fix efficacy**: fix killed exploit. Sweep over ETH deposits {0,1,2,999999,1e6,1e6+1,5e6} x withdraw amounts of the same set: no token extraction (Sweep.t.sol, run against the mutated copy). The same sweep FAILS on the original source, as expected.

### Suggested Fix
```diff
     mapping(address => uint256) public balances;
+    mapping(address => uint256) public ethBalances;
...
     function depositEth() external payable {
-        balances[msg.sender] += msg.value;
+        ethBalances[msg.sender] += msg.value;
     }
```
**Fix scope**: separate ETH ledger. The finding's recommendation also adds `withdrawEth()`, which was not tested; without it ETH deposits are unwithdrawable.
**Verified**: YES — applied to a throwaway copy; project src/ unchanged.
