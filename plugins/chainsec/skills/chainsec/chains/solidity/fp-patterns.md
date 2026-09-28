# Solidity false-positive patterns and gate overrides

## FP patterns

### FP-3: OpenZeppelin / Solmate Standard Protection
The finding reports a vulnerability in code that inherits from battle-tested libraries:
- ERC20 with built-in overflow protection (Solidity 0.8+)
- ERC4626 with virtual offset against share inflation
- ReentrancyGuard with nonReentrant modifier
- Ownable2Step with two-phase ownership transfer

**Check**: Verify the exact version of the library. Check if the contract overrides any protective virtual functions.

### FP-7: Solidity 0.8+ Arithmetic Safety
The finding claims overflow/underflow but:
- Solidity 0.8+ has built-in checked arithmetic
- The overflow would revert, not silently wrap
- This is a DoS (revert) not a value extraction → Lower severity

**Check**: Is the code in an `unchecked` block? If not, overflow reverts.

**IMPORTANT EXCEPTION**: Explicit type casts like `uint128(someUint256)` do NOT revert in Solidity 0.8+. They silently truncate. Do NOT dismiss type-cast overflow findings with this FP pattern. These are real bugs that corrupt state silently.

### FP-8: Read-Only / View Function Confusion
The finding claims state manipulation via a view function:
- View functions cannot modify state
- staticcall prevents state changes
- The "vulnerability" only affects off-chain reads

**Check**: Is the function actually view/pure? Does it matter if the value is temporarily wrong?

## Gate overrides and examples

(ported in a later task)

## Masking code examples

(ported in a later task)
