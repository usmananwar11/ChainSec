# ChainSec Security Audit Report

**Target**: GoodEntry (Code4rena 2023-08): GeVault, TokenisableRange, RangeManager, OptionsPositionManager/PositionManager, V3Proxy and helpers
**Date**: 2026-10-16
**Auditor**: ChainSec
**Scope**: 38 files listed in the README scope: 10 implementation contracts under `contracts/` (GeVault, TokenisableRange, RangeManager, RoeRouter, PositionManager/PositionManager, PositionManager/OptionsPositionManager, helper/V3Proxy, helper/LPOracle, helper/FixedOracle, helper/OracleConvert) and 28 interface files under `interfaces/`. The Aave v2 fork lending pool, vendored OpenZeppelin, `contracts/lib` and tests are out of scope.

---

## Executive Summary

GoodEntry's vault (GeVault), tokenised Uniswap V3 ranges and options position manager were audited. Eight findings survived verification: two High and six Medium, none Critical. The main risks are an accounting flaw that lets a disabled GeVault burn shares for zero payout, a permissionless `close()` in the options position manager that spends a third party's collateral through PMTransfer, and several swap/withdraw paths settled at manipulable Uniswap spot prices without an oracle bound. Most findings are conditional on an owner action or an attacker-movable pool price. All findings are held on critic code traces; no executable PoC was run.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 2 |
| Medium | 6 |
| Low | 0 |

---

## Findings

### [SOL-001] GeVault withdraw burns shares for 0 once funds are parked idle: with isEnabled=false every withdrawal after the first pays nothing — HIGH

**File**: `contracts/GeVault.sol:214`, `contracts/GeVault.sol:392`, `contracts/GeVault.sol:202`
**Category**: accounting / value-flow
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if owner sets isEnabled=false while depositors remain.

**Description**:
Discovery: Q2 (accountant, trace every wei) / TVL-01. withdraw() prices shares from getTVL(), which only sums aToken balances of the ticks (getTickBalance). withdraw() and rebalance() both call removeFromAllTicks() and only redeploy `if (isEnabled)`. When the owner has set isEnabled=false (the documented way to wind the pool down: 'otherwise just let assets sit here until totally withdrawn'), the first withdraw or any public rebalance() moves every position into idle token0/token1 balances of the vault. From then on getTVL()==0, so valueX8 and amount are 0 for every later withdrawer, yet _burn(msg.sender, liquidity) still executes and no check requires amount>0. The idle tokens stay in the vault and are not attributable to any share.

**Impact**:
Every vault depositor who withdraws after the first withdrawal/rebalance while the pool is disabled lose their whole share value (shares burned, 0 paid). Magnitude: up to the entire vault TVL minus the first withdrawer's share.

**Proof of Concept** (code trace, not executed):
```
1. Owner calls setEnabled(false) to wind the vault down; ticks still hold all assets as aTokens.
2. User A calls withdraw(): TVL is still correct, A is paid, removeFromAllTicks() moves every other depositor's assets to idle balances and deployAssets() is skipped.
3. User B calls withdraw(all): getTVL() sums only aToken balances and returns 0, so amount = 0; the fee transfer and payout transfer move 0, _burn destroys B's shares.
4. Alternatively anyone calls rebalance() right after setEnabled(false) to park everything idle, making every following withdrawal pay 0.
```

**Root Cause**:
Share valuation (getTVL) ignores the vault's own idle token0/token1 balances, while the disabled path deliberately parks all assets idle; withdraw has no amount>0 check.

**Recommendation**:
Value idle vault balances in getTVL() and refuse zero-payout burns. In getTVL() add the vault's own balances of token0/token1 (priced via the oracle) to the aToken sum, and in withdraw() add `require(amount > 0, "GEV: zero amount");` before `_burn`. Alternatively, in withdraw()/rebalance() do not call removeFromAllTicks() permanently when `!isEnabled` without accounting for the parked funds.

**Vulnerable Code**:
```solidity
function rebalance() public {
  require(poolMatchesOracle(), "GEV: Oracle Error");
  removeFromAllTicks();
  if (isEnabled) deployAssets();
}
...
uint vaultValueX8 = getTVL();
uint valueX8 = vaultValueX8 * liquidity / totalSupply();
amount = valueX8 * 10**ERC20(token).decimals() / oracle.getAssetPrice(token);
...
_burn(msg.sender, liquidity);
removeFromAllTicks();
```

**Fixed Code** (suggested):
```solidity
uint vaultValueX8 = getTVL();   // now includes idle token0/token1 balances of address(this)
uint valueX8 = vaultValueX8 * liquidity / totalSupply();
amount = valueX8 * 10**ERC20(token).decimals() / oracle.getAssetPrice(token);
require(amount > 0, "GEV: zero amount");
_burn(msg.sender, liquidity);
```

---

### [SOL-002] OPM.close is callable by anyone for any user: PMTransfers the victim's whole token0/token1 balances, charges a 1% fee on their collateral and swaps with maxAmount = the victim's entire balance — HIGH

**File**: `contracts/PositionManager/OptionsPositionManager.sol:223`, `contracts/PositionManager/OptionsPositionManager.sol:275`, `contracts/PositionManager/OptionsPositionManager.sol:491`
**Category**: access-control / slippage
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if victim has TR debt registered in the pool; victim's collateral mix needs a swap to repay the TR.

**Description**:
Discovery: MODIFIER-01 sibling diff. sellOptions, withdrawOptions and swapTokens all PMTransfer from msg.sender, but close() takes an arbitrary `user` with no msg.sender == user check, no health or liquidatability check. The OPM is a PMTransfer-whitelisted contract, so this single param decides whose aTokens are pulled. closeDebt withdraws ALL of the user's token0 and token1 aTokens, charges a 1% treasury fee out of the user's collateral when user != msg.sender, and if one side is short calls swapTokensForExactTokens(router, shortfall, maxAmount = other-side whole balance). The only guard is getAmountsIn from the same AMM, so there is no price protection (checkExpectedBalances only checks the TR deposit amounts, not the swap). Confirms and deepens DP1-2.

**Impact**:
Any user with an open TR debt in a ROE pool served by the OPM lose collateral lost to forced swaps at attacker-set prices plus a 1% fee on the closed debt, on a position they did not choose to close. Magnitude: up to the victim's whole balance of the swapped-in token per call.

**Proof of Concept** (code trace, not executed):
```
1. Victim has TR debt and holds token0 collateral only; closing requires token1 so a swap is needed.
2. Attacker front-runs by moving the Uniswap V3 pool price against the required swap direction.
3. Attacker calls close(poolId, victim, debtAsset, 0, collateral): OPM pulls all victim aTokens, getAmountsIn quotes the manipulated pool, amountsIn <= maxAmount (victim's entire balance) passes, swap executes at the bad price.
4. Attacker back-runs to restore the price and keeps the profit; the victim's debt is repaid but collateral is reduced by the price impact plus the 1% fee.
```

**Root Cause**:
A permissionless entry point operates on a third party's assets via PMTransfer without any authorization and with a swap whose limit is derived from the same pool it trades against.

**Recommendation**:
Bind the entry point to the position owner or to a verified-liquidatable position. Add `require(msg.sender == user, "OPM: not owner");` to close(), or if third-party soft liquidation is intended, require the user's health factor to be below a threshold. Replace the swap's maxAmount (the user's whole balance) with an oracle-derived bound, e.g. `oracle value of recvAmount * 101 / 100`.

**Vulnerable Code**:
```solidity
function close(uint poolId, address user, address debtAsset, uint repayAmount, address collateralAsset) external {
  ...
  debt = closeDebt(poolId, user, debtAsset, debt, collateralAsset);
...
  amtA = IERC20(LP.getReserveData(token0).aTokenAddress ).balanceOf(user);
  amtB = IERC20(LP.getReserveData(token1).aTokenAddress ).balanceOf(user);
  PMWithdraw(LP, user, token0, amtA );
  PMWithdraw(LP, user, token1, amtB );
  if (user != msg.sender ) { uint feeAmount = calculateAndSendFee(...); ... }
  swapTokensForExactTokens(ammRouter, token0Amount - amtA, amtB, path);
```

**Fixed Code** (suggested):
```solidity
function close(uint poolId, address user, address debtAsset, uint repayAmount, address collateralAsset) external {
  require(msg.sender == user, "OPM: not owner");
  ...
```

---

### [SOL-003] GeVault share price is manipulable by first-depositor donation: shares can be reduced to 1 wei and the vault donated to, so a following deposit mints rounded-down shares — MEDIUM

**File**: `contracts/GeVault.sol:247`, `contracts/GeVault.sol:214`, `contracts/GeVault.sol:202`
**Category**: vault share inflation / donation
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if attacker is sole shareholder / vault supply can be reduced to a few wei; victim deposit is below 2x the donated TVL.

**Description**:
Discovery: Q2/Edge Case first-depositor, vault-share-accounting module. deposit() mints liquidity = tSupply * valueX8 / vaultValueX8 with no minimum-liquidity burn and no virtual offset. TVL is read from aToken balances of the ticks, which can be inflated by a direct donation (send token0/token1 to the vault and call the public rebalance(), or deposit TR tokens in the lending pool on behalf of the vault). On a fresh vault the first depositor can withdraw all but 1 wei of shares (withdraw accepts any liquidity amount), leaving totalSupply=1 and TVL~0, then donate X value. A later deposit of V (X < V < 2X) mints floor(V/X)=1 share, i.e. half of the pool for a deposit of V, while the attacker holds the other share.

**Impact**:
The next depositor(s) into a vault whose supply is held by a single attacker lose up to roughly a sixth to a quarter of the deposit through share rounding. Magnitude: bounded by tvlCap (default 1e12 = 10,000 USD) unless the owner raises it.

**Proof of Concept** (code trace, not executed):
```
1. Vault is freshly deployed (totalSupply 0). Attacker deposits a small amount and gets shares.
2. Attacker calls withdraw(totalSupply-1, token): supply is now 1 wei, TVL ~ 0.
3. Attacker sends X of token0 to the vault and calls rebalance(), so getTVL() ~ X.
4. Victim deposits V with X < V < 2X (attacker front-runs the victim's pending deposit sized from the mempool): liquidity = 1 * V / X = 1.
5. Both hold 1 share of a pool worth X+V; victim loses about (V-X)/2-ish of value, attacker withdraws the gain.
```

**Root Cause**:
Share minting rounds down against the depositor with a supply the first holder can reduce to 1 wei and a TVL that accepts donations; no dead shares or virtual assets.

**Recommendation**:
Add inflation resistance: on the first mint burn a minimum amount of shares to a dead address (e.g. 1e3), and/or use virtual shares/assets in the ratio, and forbid withdrawals that leave totalSupply in (0, MIN_SUPPLY).

**Vulnerable Code**:
```solidity
if (tSupply == 0 || vaultValueX8 == 0)
  liquidity = valueX8 * 1e10;
else {
  liquidity = tSupply * valueX8 / vaultValueX8;
}

rebalance();
require(liquidity > 0, "GEV: No Liquidity Added");
_mint(msg.sender, liquidity);
```

**Fixed Code** (suggested):
```solidity
if (tSupply == 0 || vaultValueX8 == 0) {
  liquidity = valueX8 * 1e10;
  _mint(address(0xdead), MIN_LIQUIDITY);   // permanently locked
  liquidity -= MIN_LIQUIDITY;
} else {
  liquidity = tSupply * valueX8 / vaultValueX8;
}
```

---

### [SOL-004] GeVault.deployAssets indexes ticks[newTickIndex+3] out of bounds when the price is beyond the listed ticks, bricking deposit/withdraw/rebalance — MEDIUM

**File**: `contracts/GeVault.sol:337`, `contracts/GeVault.sol:428`
**Category**: dos / array bounds
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if price moves outside the span of configured ticks.

**Description**:
Discovery: Q5.6 / Q9 boundary check. getActiveTickIndex loops up to ticks.length - 3 and, if no boundary is found (price past the last listed ticks), returns ticks.length - 3. deployAssets then touches ticks[tick0Index + 1] with tick0Index = newTickIndex + 2, i.e. ticks[ticks.length], which reverts with out-of-bounds when both token balances are non-zero (or for the corresponding side). With ticks.length < 4 it always reverts. withdraw() calls deployAssets when enabled, so withdrawals also revert until the owner pushes more ticks.

**Impact**:
All GeVault depositors lose ability to withdraw (liveness) until the owner adds ticks. Magnitude: all vault funds frozen for the duration.

**Proof of Concept** (code trace, not executed):
```
1. Market price moves beyond the last configured tick (no boundary found in the loop).
2. getActiveTickIndex returns ticks.length - 3.
3. Any deposit, withdraw (when isEnabled) or rebalance reverts on ticks[ticks.length].
```

**Root Cause**:
The active-index search does not leave room for the +3 offset used by deployAssets and has no guard for running out of ticks.

**Recommendation**:
Make getActiveTickIndex leave room for the +3 offset used by deployAssets (bound the loop so newTickIndex + 3 < ticks.length) and revert with a clear message, or skip deployment of the out-of-range side, when the price is beyond the listed ticks. Enforce a minimum ticks.length in the constructor/modifyTick.

**Vulnerable Code**:
```solidity
uint tick0Index = newTickIndex;
uint tick1Index = newTickIndex + 2;
...
depositAndStash(ticks[tick0Index], availToken0 / 2, 0);
depositAndStash(ticks[tick0Index+1], availToken0 / 2, 0);
```

**Fixed Code** (suggested):
```solidity
require(ticks.length >= 4, "GEV: not enough ticks");
uint tick1Index = newTickIndex + 2;
if (tick1Index + 1 < ticks.length) {
  depositAndStash(ticks[tick1Index], availToken1 / 2, 0);
  depositAndStash(ticks[tick1Index + 1], availToken1 / 2, 0);
}
```

---

### [SOL-005] OPM.closeDebt swaps with no price bound (maxAmount = user's whole balance, amountsIn quoted from the same manipulable pool): every close/liquidate swap leg is sandwichable — MEDIUM

**File**: `contracts/PositionManager/OptionsPositionManager.sol:293`, `contracts/PositionManager/OptionsPositionManager.sol:491`, `contracts/PositionManager/OptionsPositionManager.sol:336`
**Category**: slippage / sandwich
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if position needs a swap to rebuild the TR underlying mix; UniV3 pool price movable by the attacker.

**Description**:
Discovery: Q4.5 / Module amm-mev-deep section 7 (zero slippage) and EXT-03. In closeDebt, when one underlying is short, swapTokensForExactTokens(router, shortfall, maxAmount, path) is called with maxAmount = the user's entire balance of the other token (amtA / amtB) or, in the liquidation path, the whole OPM balance. Inside, the only bound is amountsIn[0] <= maxAmount, and amountsIn comes from V3Proxy.getAmountsIn, i.e. the Uniswap V3 Quoter at the current (manipulable) pool price. checkExpectedBalances only validates the underlying amounts that will be deposited into the TR against the oracle (98-102 percent of the debt value); it does not bound what the swap costs. The swap leg therefore has no oracle-based limit, unlike swapExactTokensForTokens which applies oracle * 99 percent.

**Impact**:
Borrowers whose TR debt is closed (self-close or by a third party) and liquidators lose part of the collateral swapped at a manipulated price. Magnitude: price distortion times swap size, bounded by the user's balance of the sold token.

**Proof of Concept** (code trace, not executed):
```
1. Victim holds a TR debt and collateral mostly in one underlying (say token1); the debt's TR needs token0.
2. Attacker front-runs by buying token0 in the V3 pool, pushing the price against the victim's swap direction.
3. close() (called by the victim or by the attacker as soft-liquidator) PMWithdraws all aTokens and calls swapTokensForExactTokens; Quoter prices the exact-output swap at the manipulated price and it passes because maxAmount is the victim's whole token1 balance.
4. Attacker back-runs, restores the price and keeps the difference; the victim receives the leftover after overpaying.
```

**Root Cause**:
The slippage guard of the exact-output swap is the caller's full balance, not an oracle-derived maximum input. The quote used to size the swap is read from the same pool the attacker can move in the same transaction.

**Recommendation**:
Bound the exact-output swap by an oracle-derived maximum input instead of the user's whole balance: compute `maxIn = oracle value of recvAmount (token-in terms) * 101 / 100` and pass min(maxIn, balance) as maxAmount, mirroring the 99 percent oracle bound already used by swapExactTokensForTokens.

**Vulnerable Code**:
```solidity
if ( amtA < token0Amount ){
  path[0] = token1; path[1] = token0;
  swapTokensForExactTokens(ammRouter, token0Amount - amtA, amtB, path);
}
...
uint [] memory amountsIn = AmountsRouter(address(ammRouter)).getAmountsIn(recvAmount, path);
require( amountsIn[0] <= maxAmount && amountsIn[0] > 0, "OPM: Invalid Swap Amounts" );
amountsIn = ammRouter.swapTokensForExactTokens(recvAmount, maxAmount, path, address(this), block.timestamp);
```

**Fixed Code** (suggested):
```solidity
uint maxIn = recvAmount * oracle.getAssetPrice(path[1]) / oracle.getAssetPrice(path[0]) * 101 / 100;   // decimals-adjusted
swapTokensForExactTokens(ammRouter, token0Amount - amtA, min(maxIn, amtB), path);
```

---

### [SOL-006] RangeManager.removeFromStep (and OPM.withdrawOptionAssets) withdraw TokenisableRange liquidity with amountMin = 0 and no oracle check, unlike OPM.withdrawOptions: LP unwinds are sandwichable — MEDIUM

**File**: `contracts/RangeManager.sol:107`, `contracts/RangeManager.sol:151`, `contracts/PositionManager/OptionsPositionManager.sol:123`, `contracts/PositionManager/OptionsPositionManager.sol:412`
**Category**: slippage / sandwich (asymmetric guard)
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if victim unwinds a TR position through RangeManager (or buyOptions) in a block where the pool price can be moved; TR is a large share of the pool liquidity in its range or the range is wide.

**Description**:
Discovery: rescan class 2 (asymmetric operations). OPM.withdrawOptions wraps TokenisableRange.withdraw(amount,0,0) in checkExpectedBalances ('Get output amounts from oracle to avoid sandwich'), and GeVault removes from ticks only behind poolMatchesOracle. RangeManager.removeFromStep calls tokenisedRanges[step].withdraw(trAmt,0,0) and tokenisedTicker[step].withdraw(ttAmt,0,0) with no min amounts, no oracle comparison and no spot guard, and it is reached by removeAssetsFromStep and by every transferAssetsInto*Step call. OPM.withdrawOptionAssets (flashloaned TR in buyOptions) likewise calls TokenisableRange(flashAsset).withdraw(flashAmount,0,0) with no check. TR.withdraw pays out at the Uniswap slot0 composition, so a caller whose pool price was moved in the same block receives an adverse token mix (value at the true price is lower by the position's convexity loss), and the attacker back-runs.

**Impact**:
RangeManager users unwinding or moving ranger/ticker positions (and buyOptions users) lose part of the position value, realised as the adverse token mix at the manipulated price. Magnitude: the LVR/convexity loss of the position for the price displacement the attacker can fund; large for wide rangers, small for 10-tick tickers.

**Proof of Concept** (code trace, not executed):
```
1. Victim holds aTokens of a wide TokenisableRange (ranger) deposited via RangeManager.
2. Victim submits removeAssetsFromStep(step) (or transferAssetsIntoRangerStep, which calls removeFromStep first).
3. Attacker front-runs by swapping the Uniswap V3 pool so spot moves far inside the ranger's range.
4. removeFromStep PMTransfers the aTokens, withdraws the TR, and tr.withdraw(trAmt,0,0) returns the position's token mix at the manipulated price; cleanup() deposits it to the victim; hf check only looks at debt.
5. Attacker swaps back; the victim is left with tokens worth less than the position at the true price.
```

**Root Cause**:
TR.withdraw settles at manipulable pool spot composition; the callers that unwind TR positions on a user's behalf in RangeManager and OPM.withdrawOptionAssets pass amount0Min = amount1Min = 0 and perform none of the oracle-value checks used in the sibling paths.

**Recommendation**:
Add the same oracle-value check used in OPM.withdrawOptions around the TokenisableRange.withdraw calls in RangeManager.removeFromStep and OPM.withdrawOptionAssets (compare received amounts to the oracle-derived expected balances, e.g. checkExpectedBalances), or pass non-zero amount0Min/amount1Min derived from the oracle.

**Vulnerable Code**:
```solidity
trAmt = LENDING_POOL.withdraw(address(tokenisedRanges[step]), type(uint256).max, address(this));
tokenisedRanges[step].withdraw(trAmt, 0, 0);
```

**Fixed Code** (suggested):
```solidity
trAmt = LENDING_POOL.withdraw(address(tokenisedRanges[step]), type(uint256).max, address(this));
(uint min0, uint min1) = _oracleMinAmounts(tokenisedRanges[step], trAmt);   // oracle-derived, e.g. 98 percent
tokenisedRanges[step].withdraw(trAmt, min0, min1);
```

---

### [SOL-007] TokenisableRange.deposit splits the caller's tokens between fee pool and liquidity using slot0 spot, so a manipulated spot sends a two-sided depositor's tokens to the shared fee pool — MEDIUM

**File**: `contracts/TokenisableRange.sol:237`, `contracts/RangeManager.sol:151`, `contracts/PositionManager/OptionsPositionManager.sol:384`
**Category**: spot price dependence / value leakage
**Evidence**: REASONED — code trace [CODE-TRACE]

**Caveat (verified-conditional)**: holds only if TR has pending fee0 and fee1 (not yet compounded); depositor supplies both tokens and caller has no spot guard; attacker can move slot0 of the TR's Uniswap pool within the block.

**Description**:
Discovery: Q1/amm-mev-deep (spot read in value split), Module D/I. When fee0+fee1>0 and the caller supplies both sides, deposit() computes newFee0 = n0*fee0/(token0Amount+fee0) and newFee1 = n1*fee1/(token1Amount+fee1) where token0Amount/token1Amount come from IUniswapV3Pool.slot0() (flash-manipulable). If spot is pushed so the position holds almost no token0 (token0Amount -> 0), newFee0 -> n0 for any fee0>0 (even 1 wei): the caller's entire n0 is credited to fee0, the shared uncompounded fee pool, and only n1 (minus its fee share) is added as liquidity. LP minted is supply*newLiquidity/liquidity, so the depositor is not credited for the n0 moved to the fee pool, which is split among all LP holders. RangeManager.transferAssetsIntoStep (user collateral) and OPM.sellOptions call deposit without any oracle or spot guard; GeVault's guard (poolMatchesOracle) is not present there.

**Impact**:
Users depositing both tokens into a TR through RangeManager or OPM.sellOptions lose most of one token side of the deposit, redistributed to existing LP holders (including the attacker). Magnitude: up to the full n0 (or n1) minus the depositor's own pro-rata share; attacker gain = loss x attacker's LP share.

**Proof of Concept** (code trace, not executed):
```
1. Attacker holds a large share of a TokenisableRange that has any pending fee0>0 and fee1>0.
2. Victim submits transferAssetsIntoTickerStep/RangerStep(step, amount0, amount1) with both amounts non-zero.
3. Attacker front-runs by swapping the Uniswap V3 pool so spot sits at the range edge where token0Amount ~ 0 (cheap for a 10-tick ticker, flash-loan funded for a wide ranger).
4. deposit(): newFee0 ~ n0 so n0 is added to fee0; n0 ~ 0 goes to Uniswap; victim receives LP only for the n1-derived liquidity.
5. Attacker swaps back and withdraws; the victim's n0 sits in fee0 and is paid out pro rata to LP holders.
```

**Root Cause**:
Proportional fee/liquidity split is derived from spot slot0 instead of the oracle-derived price used elsewhere in the contract (returnExpectedBalanceWithoutFees), and there is no min-LP-out parameter.

**Recommendation**:
Compute the fee/liquidity split from the oracle-derived price (as returnExpectedBalanceWithoutFees does) instead of slot0, or require the pool price to be within a band of the oracle price before splitting; add a minimum-LP-out parameter to deposit().

**Vulnerable Code**:
```solidity
(uint160 sqrtPriceX96,,,,,,)  = IUniswapV3Pool(pool).slot0();
(uint256 token0Amount, uint256 token1Amount) = LiquidityAmounts.getAmountsForLiquidity( sqrtPriceX96, TickMath.getSqrtRatioAtTick(lowerTick), TickMath.getSqrtRatioAtTick(upperTick), liquidity);
if (token0Amount + fee0 > 0) newFee0 = n0 * fee0 / (token0Amount + fee0);
if (token1Amount + fee1 > 0) newFee1 = n1 * fee1 / (token1Amount + fee1);
fee0 += newFee0;
fee1 += newFee1; 
n0   -= newFee0;
n1   -= newFee1;
```

**Fixed Code** (suggested):
```solidity
function deposit(uint n0, uint n1, uint minLpOut) external returns (uint lpAmt) {
  require(poolMatchesOracle(), "TR: Oracle Error");   // or use an oracle sqrtPrice in getAmountsForLiquidity
  ...
  require(lpAmt >= minLpOut, "TR: slippage");
}
```

---

### [SOL-008] V3Proxy: swapTokensForExactETH keeps the unspent amountInMax and swapTokensForExactTokens refunds the entire proxy balance, so stranded input is claimable by the next caller — MEDIUM

**File**: `contracts/helper/V3Proxy.sol:160`, `contracts/helper/V3Proxy.sol:124`
**Category**: token-accounting / refund
**Evidence**: REASONED — code trace [CODE-TRACE]

**Severity adjusted**: High to Medium. V3Proxy.sol:160-176 swapTokensForExactETH never refunds amountInMax-amountIn; swapTokensForExactTokens (line 132) refunds the whole proxy balance of path[0], so stranded input is claimable by any later caller. Real but bounded by the slippage margin callers supply; no in-scope contract uses the ETH path. Downgraded from High.

**Description**:
Discovery: Q4.4 (amountIn < amountInMax boundary) and Module F. Both exact-output paths pull amountInMax from the caller, but the router only consumes amountIn <= amountInMax. swapTokensForExactETH never returns amountInMax-amountIn, so it stays in the proxy. swapTokensForExactTokens refunds ogInAsset.balanceOf(address(this)), which includes any previously stranded balance of that token, so the next caller of the exact-token path with the same path[0] (amountInMax can be small) receives the leftovers. The function is also payable but ETH sent is not used. Deepens DP1-4.

**Impact**:
Callers of swapTokensForExactETH (and contracts integrating it) lose amountInMax - amountIn of the input token on every call. Magnitude: the slippage margin per call, taken by the next swapTokensForExactTokens caller or the owner via emergencyWithdraw.

**Proof of Concept** (code trace, not executed):
```
1. Victim calls swapTokensForExactETH(amountOut, amountInMax = 1.01*quote, [USDC, WETH]); router spends the quote, 1% of USDC stays in V3Proxy.
2. Attacker calls swapTokensForExactTokens(1 wei, 1, [USDC, X]) (any valid direct path with USDC as input).
3. The final safeTransfer sends ogInAsset.balanceOf(proxy), including the victim's stranded USDC, to the attacker.
```

**Root Cause**:
Refund logic is not tied to this call's delta (amountInMax - amountIn); one path omits the refund, the other refunds the full balance.

**Recommendation**:
Refund only this call's unspent input: record the balance before pulling funds and send `amountInMax - amountIn` (or balanceAfter - balanceBefore) back in both exact-output paths, instead of omitting the refund in swapTokensForExactETH and sending the entire balanceOf(this) in swapTokensForExactTokens.

**Vulnerable Code**:
```solidity
amounts[0] = ROUTER.exactOutputSingle(...amountInMax...);
...
ogInAsset.safeApprove(address(ROUTER), 0);   // swapTokensForExactETH: no refund
...
ogInAsset.safeTransfer(msg.sender, ogInAsset.balanceOf(address(this)));   // swapTokensForExactTokens
```

**Fixed Code** (suggested):
```solidity
uint balBefore = ogInAsset.balanceOf(address(this)) - amountInMax;   // after pulling amountInMax
...
uint refund = ogInAsset.balanceOf(address(this)) - balBefore;
if (refund > 0) ogInAsset.safeTransfer(msg.sender, refund);
```

---

## Security Strengths

- **Reentrancy protection**: `GeVault.deposit` and `GeVault.withdraw` are `nonReentrant`, and the contract inherits OpenZeppelin `ReentrancyGuard`.
- **Token transfer safety**: `GeVault` uses `SafeERC20` (`using SafeERC20 for ERC20`) for token movements; contracts are compiled on Solidity 0.8.19 with checked arithmetic.
- **Oracle guard on rebalancing**: `GeVault.rebalance` requires `poolMatchesOracle()` (Uniswap spot within 1 percent of the oracle price) before removing and redeploying liquidity, and share pricing uses oracle-derived TVL.
- **Sandwich protection on some unwinds**: `OptionsPositionManager.withdrawOptions` wraps `TokenisableRange.withdraw` in `checkExpectedBalances`, comparing outputs with oracle values; `swapExactTokensForTokens` applies an oracle-based 99 percent bound.
- **Area for improvement**: the same oracle guard is not applied consistently (see SOL-005, SOL-006, SOL-007), and `GeVault` has no inflation protection on first mint (SOL-003).

---

## Architecture Observations

- `OptionsPositionManager` and `PositionManager` are whitelisted for PMTransfer by the lending pool, so every external entry point that takes a `user` parameter effectively controls that user's aTokens; `close()` is the one reviewed entry point without an authorization check.
- `V3Proxy` is a Uniswap V2 router look-alike over V3 `SwapRouter`/`Quoter`; it holds approvals and balances between calls and had no dedicated test file, which raised its risk score. Its refund logic is inconsistent between paths (SOL-008).
- `GeVault` correctness depends on tick configuration invariants (ordering, minimum count, coverage of the price range) that are owner-managed and not validated (see SOL-004; unreported lower-severity observations on `modifyTick`/`shiftTick` validation were killed at verification).
- Share valuation in `GeVault.getTVL` counts only aToken balances; any state in which funds sit idle in the vault (disabled pool, donations) is not reflected in pricing (SOL-001, SOL-003).
- Findings DA-1 (flashloan callback without initiator check) was killed because the pool's debt-token delegation enforces authorization; this relies on standard Aave v2 behaviour of the out-of-scope lending pool and is worth confirming against the fork.

---

## Methodology

**Audit mode**: full pipeline (`quick` = false).

Phases completed: Recon, Detection (four lenses plus final sweep, with a Pass 1 brief), Rescan, Per-unit deep dives, State Analysis and Verification (kill gates, impact premises and concrete exploit traces). No phases are listed as incomplete in `A/preflight.json`.

Notes and limitations:
- **Facts mode**: `regex`. Structural facts were pattern-matched, not compiler-verified, so unit and call-graph facts carry lower confidence.
- **Tooling mode**: `degraded`. Slither was not available; python3 and forge were present, but no foundry project/dependencies were set up.
- **Scope**: limited to the paths in the README scope (38 files). The Aave v2 fork lending pool, vendored OpenZeppelin, `contracts/lib` and tests were not audited.
- **No executable PoCs were run.** Every finding is supported by the critic's manual trace only, tagged `[CODE-TRACE]` (REASONED). Evidence tier REASONED is not a weaker finding, but exploit values are not mechanically reproduced. Running `chainsec-poc` on the two High findings is recommended.
- **Interface-only files**: the 28 interface files under `interfaces/` contain no function bodies and had no dedicated per-unit cluster; they were skimmed for signature mismatches only.
- **Warning from preflight**: per-unit: no dedicated cluster for the 28 interface-only files.
- Low-severity and informational items were not included in this report, and killed candidates (including DA-1) were excluded.

Methodology derived from Krait by Zealynx Security.

---

```
───────────────────────────────────────────────────
📋 8 findings saved to .audit/solidity/findings.json
───────────────────────────────────────────────────
```

### Next Steps

1. **Review killed findings**: 17 candidates were killed at verification (e.g. DA-1 by FP-1, DA-4/DC-5 by Gate F, DC-4 by Gate D); run `chainsec-review` for a second opinion.
2. **Prove a finding**: run `chainsec-poc SOL-001` and `chainsec-poc SOL-002` to turn the `[CODE-TRACE]` into an executed `[POC-PASS]` or `[POC-FAIL]`.
3. **Fuzz invariants**: run `chainsec-fuzz` to extract protocol invariants (e.g. share-price monotonicity, TVL including idle balances) and test them.
