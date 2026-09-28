# ChainSec Detection Primer: Staking / Governance / Voting

> Chain-specific half of `domains/defi/primers/defi-staking-governance.md`.

## FROM MISS ANALYSIS — Patterns Krait Has Missed in Real Contests

### 18. Gas Manipulation to Force try/catch Failure
If a core function uses `try/catch` with a `_pause()` in the catch block → attacker sends transaction with just enough gas for the outer call but not enough for the inner call → catch executes → protocol paused.
**Check**: Does any function use try/catch where the catch block has a destructive action (pause, lock, revert state)?
