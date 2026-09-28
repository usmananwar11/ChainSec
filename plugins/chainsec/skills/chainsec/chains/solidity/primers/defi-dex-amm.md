# ChainSec Detection Primer: DEX / AMM / Liquidity Pool

> Chain-specific half of `domains/defi/primers/defi-dex-amm.md`.

## CRITICAL — Must Check Every DEX/AMM Audit

### 1. First Depositor Share Inflation
**Check**: First mint path. Is there `_mint(address(0), MINIMUM_LIQUIDITY)` or virtual offset? If not → candidate.

### 7. LP Token Pricing via slot0/spot
If LP token value uses `slot0` sqrtPriceX96 or spot reserves → flash-loan manipulable. Must use TWAP.
**Check**: How is LP token valued? Any `slot0()` call in pricing path = manipulable.

## HIGH — Check If Relevant to Codebase

### 9. Reentrancy During LP Mint/Burn
ERC777 tokens, native ETH `.call{value}`, and ERC721/1155 callbacks give recipient execution during transfer. Can they re-enter mint/burn/swap?
**Check**: Is `nonReentrant` on ALL state-changing functions? Is CEI pattern followed for every external call?

## PROTOCOL-SPECIFIC INTEGRATION CHECKS

### Uniswap V3 Integration
- Negative ticks are valid (`int24`). Does tick math handle sign correctly?
- `tickLower < tickUpper` enforced?
- `sqrtPriceX96` bounded at min/max tick?
- All `NonfungiblePositionManager` calls have slippage + deadline?
- `pool.slot0()` used for pricing? → manipulable

### Curve/StableSwap Integration
- Killed/paused pools handled? (`pool.is_killed()`)
- Native ETH vs WETH distinction (different pool addresses/IDs)
- Tricrypto index order differs from 2pool
- `get_dy` return value properly used?

### Chainlink Oracle Integration
- Stale price check (`updatedAt + heartbeat < block.timestamp`)
- Zero/negative price rejected?
- `roundId` completeness verified?
- L2 sequencer uptime feed checked?
- BTC feed used for WBTC? (depeg risk)

## FROM MISS ANALYSIS — Patterns Krait Has Missed in Real Contests

### 21. External Call to User-Controlled Address Reverts = HoneyPot
If fee transfer uses `.call` to a user-set address (referralFeeDestination, royaltyRecipient) → user sets it to a reverting contract → all sells/transfers blocked → buyers trapped.
**Check**: For every `.call{value: ...}` where the target is user-controlled: what happens if it reverts? Is there try/catch? Can it block core operations?
