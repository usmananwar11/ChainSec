# ChainSec Security Audit Report

**Target**: Frankencoin (ZCHF), C4 2023-04 contest snapshot
**Date**: 2026-10-16
**Auditor**: ChainSec
**Scope**: contracts/Position.sol, MintingHub.sol, Equity.sol, Frankencoin.sol, ERC20.sol, ERC20PermitLight.sol, StablecoinBridge.sol, PositionFactory.sol, MathUtil.sol, Ownable.sol (10 files, about 950 SLOC)

---

## Executive Summary

ChainSec audited the Frankencoin stablecoin, its CDP positions and auction-based liquidation hub, the FPS equity/governance token and the XCHF bridge. The main risk is the owner-controlled position price: it can be raised without bound and it drives challenger rewards, debt repayment and the loss coverage that mints unbacked ZCHF, which yields one Critical drain of the reserve, three High and three Medium findings. The liquidation/auction path (MintingHub and Position) is the highest-risk area.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 3 |
| Medium | 3 |
| Low | 0 |

---

## Findings

### [SOL-001] Challenger reward is 2% of owner-set price*size and is paid via notifyLoss even when the position has no debt: unbounded reserve drain / unbacked ZCHF mint — CRITICAL

**File**: `contracts/MintingHub.sol:252`, `contracts/Position.sol:159`, `contracts/Position.sol:329`, `contracts/Frankencoin.sol:280`
**Category**: economic-design
**Status**: verified
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DB-1, DP1-1, DC-2

**Description**:
Lens B value-flow trace of end(): volume = price * size (price is a free, owner-controlled variable, only gated by a 3-day mint cooldown when raised), reward = 2% of volume, fundsNeeded = reward + repayment. If effectiveBid < fundsNeeded the hub calls zchf.notifyLoss(fundsNeeded - effectiveBid), which transfers the whole equity reserve and then MINTS the rest to the hub; the hub then pays the reward to the challenger. The reward does not depend on the position's minted debt (repayment = min(minted, volume) can be 0), on market value, or on the challenger being independent of the owner. Unlike DP1-1 (self-liquidation of a debt-carrying position), no debt, no vetted original and no dishonest bidder are needed: a clone with minimum collateral and _initialMint = 0 (no fee, no veto window) is enough. The attacker sets price to an astronomically high value, a second address launches a challenge of size s >= minimumCollateral with its own collateral, nobody can avert (averting requires bid >= price*s), and after challengePeriod end() pays the challenger 2%*price*s out of the reserve and then out of newly minted ZCHF. The challenger's collateral is returned, and the position's collateral goes to the end() caller, so the attacker's cost is only gas plus temporary collateral.

**Impact**:
Who: FPS holders (equity reserve), minter reserve, and all ZCHF holders via inflation. Loses: entire ZCHF reserve and then unbounded newly minted unbacked ZCHF. Magnitude: 2% * price * size, with price attacker-chosen: effectively unbounded (limited only by uint256 overflow of price*size).

**Proof of Concept** (code trace, not executed):
```
1. Attacker calls MintingHub.clonePosition(vettedPosition, minCollateral, 0): gets a clone with price 0, minted 0, no veto window, no fee.
2. Attacker calls clone.adjustPrice(1e45) (increase path: no collateral check, only 3-day mint cooldown, no challenge active).
3. A second address calls launchChallenge(clone, s) with s >= minimumCollateral; averting would require a bid >= price*s, so nobody bids.
4. After challengePeriod anyone calls end(n): volume = price*s, repayment = 0, reward = 2%*volume, effectiveBid = 0, hub calls notifyLoss(reward): reserve is drained, remainder is minted to the hub.
5. Hub transfers reward to the challenger; challenger collateral is returned; the end() caller receives the position collateral. Attacker holds the minted ZCHF and can repeat.
```

**Root Cause**:
Reward and loss coverage are denominated in a position parameter the owner can set arbitrarily high at any time (adjustPrice has no upper bound or collateral-value check when raising), and notifyLoss will mint unlimited ZCHF once the reserve is exhausted; there is no cap relative to minted debt, realised bid or collateral value.

**Recommendation**:
Cap the reward by realised value (e.g. min(reward, bid-based or debt-based amount)), do not let price-derived quantities drive notifyLoss, and bound/validate upward price changes.

**Vulnerable Code**:
```solidity
uint256 reward = (volume * CHALLENGER_REWARD) / 1000_000;
uint256 fundsNeeded = reward + repayment;
...
} else if (effectiveBid < fundsNeeded){
    zchf.notifyLoss(fundsNeeded - effectiveBid);
}
zchf.transfer(challenge.challenger, reward);
---
function adjustPrice(uint256 newPrice) public onlyOwner noChallenge {
    if (newPrice > price) { restrictMinting(3 days); } else { checkCollateral(collateralBalance(), newPrice); }
    price = newPrice;
}
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
uint256 reward = (volume * CHALLENGER_REWARD) / 1000_000;
if (reward > effectiveBid) reward = effectiveBid; // pay the reward only out of realised bid value
uint256 fundsNeeded = reward + repayment;
// and in Position.adjustPrice: bound the increase, e.g. require(newPrice <= price * 2) or a governance-set maximum
```

---

### [SOL-002] Zero/dust bids are always accepted and extend the challenge by 30 minutes, letting anyone stall a liquidation indefinitely at gas cost — HIGH

**File**: `contracts/MintingHub.sol:188`, `contracts/MintingHub.sol:199`
**Category**: dos
**Status**: verified
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DC-1, DP1-3, DA-6, DD-3

**Description**:
Discovery: Q-attacker on bid() / lending-liquidation-deep (auction gaming), deepening DP1-3. With no prior bid, minBid() = 0*1005/1000 = 0, so bid(n, 0, size) passes the BidTooLow check, sets bidder = msg.sender, transfers 0 ZCHF and, when called inside the last 30 minutes, bumps challenge.end to now + 30 minutes. Because challenge.bid stays 0 the minimum never grows, so the same call can be repeated every <30 minutes forever. Below 200 wei, floor(bid*1.005) == bid, so a 1 wei bid has the same property. end() requires block.timestamp >= challenge.end, so the challenge can never be settled, the position stays under challengedAmount > 0 (mint, withdraw and adjustPrice all revert), and the challenger's collateral is locked in the hub. The 0-bidder is additionally set as recipient of the position collateral in end(), displacing the end() caller.

**Impact**:
Who: challengers (locked collateral, no reward) and the protocol (undercollateralised position cannot be liquidated). Loses: liveness of liquidation; challenger collateral locked for as long as the attacker keeps bidding; bad debt accrues against the reserve. Magnitude: the whole challenge size plus the position's debt, for the price of about 48 cheap txs per day.

**Proof of Concept** (code trace, not executed):
```
1. Challenger calls launchChallenge(pos, size); the position is overpriced or undercollateralised so nobody would pay price*size.
2. The position owner (or any griefer) calls bid(n, 0, size) when 29 minutes remain: tryAvertChallenge(size, 0) returns false, minBid == 0 so no revert, challenge.end = now + 30 minutes, bidder = attacker, bid = 0.
3. 29 minutes later the attacker calls bid(n, 0, size) again; minBid is still 0, end is pushed again.
4. end(n) always reverts with 'period has not ended'; the challenger cannot recover collateral or settle, the position stays locked and the bad debt is never liquidated.
```

**Root Cause**:
bid() does not require a strictly positive, strictly increasing bid when challenge.bid == 0 and applies the ebay-style time extension to such bids; the anti-stall argument in the code comment (0.5% per 30 minutes) only holds for bid > 200 wei.

**Recommendation**:
Require a strictly positive bid that strictly exceeds the previous one by at least a minimum increment, so the extension cannot be repeated for free.

**Vulnerable Code**:
```solidity
function minBid(Challenge storage challenge) internal view returns (uint256) {
    return (challenge.bid * 1005) / 1000;
}
...
if (_bidAmountZCHF < minBid(challenge)) revert BidTooLow(_bidAmountZCHF, minBid(challenge));
uint256 earliestEnd = block.timestamp + 30 minutes;
if (earliestEnd >= challenge.end) {
    challenge.end = earliestEnd;
}
zchf.transferFrom(msg.sender, address(this), _bidAmountZCHF);
challenge.bid = _bidAmountZCHF;
challenge.bidder = msg.sender;
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
function minBid(Challenge storage challenge) internal view returns (uint256) {
    return challenge.bid == 0 ? 1e18 : (challenge.bid * 1005) / 1000 + 1; // never 0, always strictly increasing
}
```

---

### [SOL-003] Owner can raise the liquidation price at any time (only a 3-day cooldown) and clones skip the veto window, allowing unbacked minting up to the limit — HIGH

**File**: `contracts/Position.sol:159`, `contracts/Position.sol:76`, `contracts/MintingHub.sol:124`
**Category**: access-control
**Status**: verified
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DP1-2, DA-4

**Description**:
Discovery: Q3.1 / Q1.4 (sufficiency of the check). Governance's only protection against a bad price is the veto during the first 3 days (Position.deny, start check). adjustPrice() allows increasing the price without any collateral check or governance hook; it only triggers restrictMinting(3 days). A clone is created without veto window (cooldown storage starts at 0, no OPENING_FEE) and gets price = _mint*1e18/_coll, which is 0 for _mint = 0; the clone owner can then raise the price arbitrarily. After 3 days the owner mints up to the clone's limit against dust collateral.

**Impact**:
Who: ZCHF holders and FPS holders. Loses: backing of ZCHF minted against worthless collateral (up to the position/clone limit); loss falls on the reserve when the position is later liquidated. Magnitude: up to the limit given to the clone (half of the remaining limit of the original) or the original's limit.

**Proof of Concept** (code trace, not executed):
```
1. Attacker calls MintingHub.clonePosition(vettedPosition, minCollateral, 0): receives half of the remaining limit L, no veto window, price = 0.
2. Attacker calls adjustPrice(hugePrice): price increase has no collateral check, sets a 3-day mint cooldown.
3. After 3 days attacker calls mint(attacker, L): checkCollateral passes because collateral * hugePrice >= minted * 1e18.
4. Attacker keeps L ZCHF; abandoning the dust collateral leaves bad debt covered by the reserve (see DP1-1 for extracting even the collateral).
```

**Root Cause**:
The price used by checkCollateral() is fully owner-controlled after the veto period, so the collateral invariant 'collateral * price >= minted' can be made trivially true; vetting by governance applies only at position creation, not to later price changes or clones.

**Recommendation**:
Apply a collateral/value sanity check or a governance veto to upward price changes, and make clones inherit a price (not 0) so a zero-mint clone cannot later set an arbitrary price. For example, cap the increase relative to the current price and make the cap the same for clones.

**Vulnerable Code**:
```solidity
function adjustPrice(uint256 newPrice) public onlyOwner noChallenge {
    if (newPrice > price) {
        restrictMinting(3 days);
    } else {
        checkCollateral(collateralBalance(), newPrice);
    }
    price = newPrice;
    emitUpdate();
}
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
function adjustPrice(uint256 newPrice) public onlyOwner noChallenge {
    if (newPrice > price) {
        require(newPrice <= price * 2, "increase too large"); // bounded step
        restrictMinting(3 days);
    } else {
        checkCollateral(collateralBalance(), newPrice);
    }
    price = newPrice;
    emitUpdate();
}
```

---

### [SOL-004] Owner can raise price to a value that overflows price*size, making bid() and end() revert forever: position becomes unliquidatable and challenger collateral is stuck in the hub — HIGH

**File**: `contracts/Position.sol:159`, `contracts/Position.sol:304`, `contracts/Position.sol:329`, `contracts/MintingHub.sol:199`, `contracts/MintingHub.sol:252`
**Category**: arithmetic-overflow
**Status**: verified
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DD-2

**Description**:
Parameter MAX test on price. adjustPrice() has no upper bound when the price is raised (only a 3 day mint cooldown, no collateral check). Both liquidation paths multiply price by a challenge size with checked arithmetic: tryAvertChallenge computes `price * _collateralAmount` (bid path) and notifyChallengeSucceeded computes `_mulD18(price,_size)` = price*_size/1e18 (end path). For price > 2^256/size (e.g. type(uint256).max) both revert with a Panic. Hence launchChallenge (which does not touch price) still takes the challenger's collateral into the hub, but the challenge can neither be averted (bid reverts) nor ended (end reverts, and the whole tx including returnCollateral rolls back). The challenger's collateral is permanently stuck and the position can never be liquidated, regardless of how far the collateral value falls. An owner that has minted against the collateral can front-run any pending launchChallenge (noChallenge is only checked at execution) or set the price preemptively once the veto window is over.

**Impact**:
Who: Challengers (stuck collateral) and ZCHF holders / FPS reserve (undliquidatable bad debt). Loses: challenger collateral locked in MintingHub forever; minted ZCHF of the position can never be recovered via liquidation. Magnitude: entire minted amount of the position plus any collateral posted by challengers.

**Proof of Concept** (code trace, not executed):
```
1. Owner mints M ZCHF against collateral C at a vetted price.
2. After the veto window, owner calls adjustPrice(type(uint256).max) (allowed: no collateral check on increase).
3. Collateral value drops; challenger calls launchChallenge(position,size) and deposits size tokens into the hub.
4. bid(): tryAvertChallenge reverts on price*size overflow; end(): notifyChallengeSucceeded reverts on _mulD18 overflow.
5. Challenge can never be resolved: challenger's tokens are stuck, position never liquidated, loss accumulates in the system.
```

**Root Cause**:
Unbounded owner-controlled price combined with unchecked-range multiplications on the liquidation path; no sanity bound on price at adjustPrice and no fallback when volume cannot be computed.

**Recommendation**:
Bound price at adjustPrice (and in checkCollateral/constructor) so price * maxChallengeSize cannot overflow, or use mulDiv/saturating arithmetic in the liquidation path.

**Vulnerable Code**:
```solidity
function adjustPrice(uint256 newPrice) public onlyOwner noChallenge {
    if (newPrice > price) { restrictMinting(3 days); } else { checkCollateral(collateralBalance(), newPrice); }
    price = newPrice;
}
...
} else if (_bidAmountZCHF * ONE_DEC18 >= price * _collateralAmount){
...
uint256 volumeZCHF = _mulD18(price, _size);
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
uint256 constant MAX_PRICE = type(uint128).max;
function adjustPrice(uint256 newPrice) public onlyOwner noChallenge {
    require(newPrice <= MAX_PRICE, "price too high");
    ...
}
```

---

### [SOL-005] Partial challenge clears the owner's whole debt because repayment is min(minted, price*size) rather than proportional to the challenged share — MEDIUM

**File**: `contracts/Position.sol:340`, `contracts/MintingHub.sol:260`
**Category**: economic-design
**Status**: verified-conditional
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DB-3

**Caveat (conditions required)**: price*size >= minted for a slice of the collateral and market value of the slice below price*size

**Description**:
The code comment argues volume >= minted*size/colBal, so the repayment is at least proportional. But the repayment is capped only by minted, not by the proportional share. For a position with collateral C, minted M and price P with P*C >> M, a challenge of size s with P*s >= M burns the entire debt M while only s of C collateral is sold at the (market-value) bid. The owner keeps C - s collateral debt-free; the difference between M + reward and the bid is covered by notifyLoss (reserve or newly minted ZCHF). The owner (or colluding challenger) can engineer this by raising price, then self-challenging a slice of the collateral.

**Impact**:
Who: reserve / FPS holders and ZCHF holders. Loses: reserve ZCHF equal to debt not backed by the sold slice of collateral. Magnitude: up to minted per challenge sequence.

**Proof of Concept** (code trace, not executed):
```
1. Owner holds C=100 collateral, minted M=500, price P=10 (market 8); a slice s=60 gives volume 600 >= M.
2. Challenge on s=60 ends with bid 480 (market value) or none.
3. repayment = 500 (all debt), reward = 12, bid 480 < 512: notifyLoss(32+).
4. Owner keeps the remaining 40 collateral with zero debt and the unspent minted ZCHF.
```

**Root Cause**:
Debt forgiveness is computed from the owner-controlled price instead of the proportional share minted * size / collateralBalance.

**Recommendation**:
Cap repayment at minted * size / collateralBalance (rounded up) or tie it to the realised bid.

**Vulnerable Code**:
```solidity
uint256 volumeZCHF = _mulD18(price, _size);
uint256 repayment = minted < volumeZCHF ? minted : volumeZCHF;
notifyRepaidInternal(repayment);
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
uint256 proportionalDebt = (minted * _size + collateralBalance() - 1) / collateralBalance();
uint256 repayment = proportionalDebt < volumeZCHF ? proportionalDebt : volumeZCHF;
notifyRepaidInternal(repayment);
```

---

### [SOL-006] FPS minted for dust when total supply is below 1000 FPS: calculateSharesInternal ignores the invested amount — MEDIUM

**File**: `contracts/Equity.sol:241`, `contracts/Equity.sol:266`
**Category**: share-accounting
**Status**: downgraded
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DB-2

**Severity adjusted**: High → Medium — Traced with values: supply 1000 FPS, equity E>=8000; holder redeems 500 after 90 days (cubic curve leaves 12.5% of E, still >=1000); transferAndCall(equity,1 wei) passes the equity>=1000 check, and calculateSharesInternal returns 1000e18-500e18=500e18 FPS regardless of investment. The attacker then holds 50% of supply for 1 wei. Requires FPS supply below 1000 while equity >= 1000 ZCHF, and victims can race to redeem, so the gain is not guaranteed. Downgraded from High to Medium; verified-conditional on those state conditions. PoC recommended.

**Conditions**: FPS total supply below 1000 FPS while equity() >= 1000 ZCHF

**Description**:
calculateSharesInternal returns newTotalShares - totalShares where newTotalShares = 1000e18 whenever totalSupply() < 1000e18, regardless of capitalBefore and investment. If the FPS supply ever falls below 1000 shares (the initial depositor receives exactly 1000 FPS and can redeem any part of it after the holding period; redeem only requires shares + 1e18 < totalSupply) while equity is positive, the next caller who sends any amount that keeps equity() >= MINIMUM_EQUITY (even 1 wei, since the existing equity already satisfies the requirement) receives 1000e18 - totalSupply new shares, i.e. a majority of the pool, at no real cost. After the holding period these shares redeem for the corresponding fraction of the existing equity. A related boundary: when capitalBefore <= 0 (equity <= amount) a fixed 1000 FPS is issued independent of the existing supply, so a recapitaliser into a negative-equity pool with large supply receives a negligible share (relies on restructureCapTable).

**Impact**:
Who: existing FPS holders. Loses: most of the equity value through dilution. Magnitude: up to (1000 - supply)/1000 of equity per exploit.

**Proof of Concept** (code trace, not executed):
```
1. Initial depositor holds 1000 FPS and redeems e.g. 500 after the 90-day holding period; supply = 500 FPS, equity still E (> 1000 ZCHF).
2. Attacker calls zchf.transferAndCall(equity, 1 wei, '') (equity() after transfer >= 1000 ZCHF holds from existing balance).
3. onTokenTransfer mints 1000e18 - 500e18 = 500 FPS to the attacker, now 50% of supply.
4. After the holding period the attacker redeems and receives about 87.5% of the capital via the cubic curve for 50% of shares (or votes with 50%).
```

**Root Cause**:
Bootstrap special case keyed on totalSupply rather than on capital: share issuance is not a function of the amount paid when supply < 1000 FPS.

**Recommendation**:
Apply the fixed 1000-share bootstrap only when capitalBefore is 0 (or supply is 0); otherwise use the bonding curve.

**Vulnerable Code**:
```solidity
uint256 newTotalShares = totalShares < 1000 * ONE_DEC18 ? 1000 * ONE_DEC18 : _mulD18(totalShares, _cubicRoot(_divD18(capitalBefore + investment, capitalBefore)));
return newTotalShares - totalShares;
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
uint256 newTotalShares = totalShares == 0 || capitalBefore == 0 ? 1000 * ONE_DEC18 : _mulD18(totalShares, _cubicRoot(_divD18(capitalBefore + investment, capitalBefore)));
return newTotalShares - totalShares;
```

---

### [SOL-007] Costless launchChallenge + self-avert bid re-arms the 1-day mint/withdraw cooldown on any position, locking the owner's collateral and blocking cloning indefinitely — MEDIUM

**File**: `contracts/Position.sol:304`, `contracts/Position.sol:263`, `contracts/MintingHub.sol:140`, `contracts/MintingHub.sol:199`
**Category**: dos
**Status**: downgraded
**Evidence**: REASONED — code trace [CODE-TRACE] (no executable PoC was run)
**Merged from**: DA-1, DD-5, DC-5

**Severity adjusted**: High → Medium — Traced: launchChallenge is permissionless; self-bid with price*size makes tryAvertChallenge true, restrictMinting(1 days), ZCHF paid to self and collateral returned to self; repeat daily blocks withdrawCollateral/mint/reduceLimitForClone (noChallenge/noCooldown). Real and cheap, but funds are only frozen (not lost), bounded by position expiration (+1 day), and the attacker must tie up price*size ZCHF and size collateral. Downgraded from High to Medium (DoS exception keeps it at Medium minimum). PoC recommended.

**Conditions**: position not yet expired; attacker can temporarily hold price*size ZCHF and size collateral (size >= minimumCollateral)

**Description**:
Discovery: MODIFIER-01 / state-transition check (who may trigger restrictMinting). launchChallenge is permissionless, and bid() lets the challenger himself be the averting bidder: tryAvertChallenge only checks bid*1e18 >= price*size and then calls restrictMinting(1 days) on the position. In the averted path bid() pays the bid to challenge.challenger and returns the collateral to msg.sender, so when challenger == bidder both legs net to zero. The attacker pays only gas (and needs price*size ZCHF / size collateral for the duration of the two calls). Each round sets cooldown = now + 1 day on the position, and while the challenge is open challengedAmount > 0 as well. withdrawCollateral, mint and reduceLimitForClone (hence clonePosition) all require noCooldown (and noChallenge), so repeating once per day keeps the owner from withdrawing collateral or minting and prevents anybody from cloning the position, until the position expires (tryAvertChallenge returns false after expiration).

**Impact**:
Who: position owners (borrowers) and would-be cloners. Loses: access to their collateral (withdraw/repay-then-withdraw) and minting capacity for as long as the attack is sustained. Magnitude: whole collateral of any non-expired position can be frozen until expiration at gas cost only.

**Proof of Concept** (code trace, not executed):
```
1. Attacker holds minimumCollateral of the position's collateral token and price*minimumCollateral ZCHF (both recovered at the end).
2. Attacker calls MintingHub.launchChallenge(pos, minimumCollateral): challengedAmount > 0, owner cannot mint, adjustPrice or withdrawCollateral for the challenge duration.
3. Just before challenge.end attacker calls bid(n, price*size/1e18 rounded up, size): tryAvertChallenge returns true, restrictMinting(1 days) sets cooldown = now + 1 day; ZCHF goes to himself, collateral returns to himself.
4. Attacker immediately repeats from step 2; the owner is never outside challenge or cooldown, cannot withdraw collateral or mint, and clonePosition reverts with Hot().
5. Result: owner's collateral frozen until expiration at attacker cost of gas only.
```

**Root Cause**:
A costless, permissionless action (challenge then self-avert) is allowed to extend a cooldown that guards the owner's core operations. Nothing prevents the challenger from being the averting bidder and the cooldown extension is not conditional on the bid being paid by a third party or costing the averting party anything.

**Recommendation**:
Make the cooldown extension in tryAvertChallenge conditional on the averting bidder paying a third party (bidder != challenger), or do not restrict minting on an averted challenge by the same account that launched it.

**Vulnerable Code**:
```solidity
} else if (_bidAmountZCHF * ONE_DEC18 >= price * _collateralAmount){
    // challenge averted, bid is high enough
    challengedAmount -= _collateralAmount;
    restrictMinting(1 days);
    return true;
}
---
zchf.transferFrom(msg.sender, challenge.challenger, _bidAmountZCHF);
challenge.position.collateral().transfer(msg.sender, challenge.size);
```

**Fixed Code** (suggested, illustrative; needs review against protocol design):
```solidity
// in MintingHub.bid(), averting branch
require(msg.sender != challenge.challenger, "self-avert");
// or only call restrictMinting(1 days) when msg.sender != challenge.challenger
```

---

## Security Strengths

- **Arithmetic safety**: All ten in-scope contracts compile under Solc 0.8.26 with checked arithmetic, so overflow reverts instead of wrapping (this also bounds several findings to reverts rather than silent corruption).
- **Governance veto on new risk**: Frankencoin.sol minter proposals and Position.sol positions have an application/init window (3 days minimum for positions) in which FPS holders above the quorum can deny them via checkQualified in Equity.sol.
- **Reserve backstop**: Frankencoin.notifyLoss in Frankencoin.sol covers liquidation shortfalls from the equity reserve first, keeping ZCHF backed before any new mint.
- **Access control model**: Position.sol privileged actions are onlyOwner or hub-only (notify*, reduceLimitForClone, initializeClone), and Ownable.sol is minimal and used consistently.
- **Area for improvement**: no reentrancy guard on MintingHub.bid/end (collateral tokens are arbitrary ERC20) and price parameters in Position.sol are unbounded; the visible test suite breadth was not assessed beyond a basic Foundry test.

---

## Architecture Observations

- MintingHub.sol (auction, challenge splitting, pooled custody of collateral and bids) and Position.sol (price, clones, limit transfer) carry the highest complexity and risk scores and are where all report findings except the Equity share issuance issue sit.
- Several findings share the unbounded `price` parameter as an enabler (SOL-001, SOL-003, SOL-004, SOL-005); fixing price bounds centrally would reduce the surface, though each finding keeps a distinct fix.
- Equity.sol bootstrap special cases (supply below 1000 FPS, capital at or below zero) deserve extra tests, as does restructureCapTable (it indexes `addressesToWipe[0]` on every iteration; judged Low and not listed as a finding).
- Collateral tokens are arbitrary and trusted only via the governance veto; callback-capable tokens were considered and not reported because no concrete token was named.
- Candidates killed by the critic gates (not reported): minter bootstrap at zero supply, checkQualified at zero votes, postponed collateral return, splitChallenge front-running, clone price flooring, zero challenge period, overpaying averting bid, stale allowance override, bridge donation DoS (known issue L-2), vote anchor reset, bid/end reentrancy with callback tokens. Two Low-severity verified items (restructureCapTable index typo; zero-mint clone limit capture) were excluded as Low.

---

## Methodology

**Audit mode**: Full pipeline (`quick` is false; no incomplete phases recorded).

Completed phases: Recon, Detection (four lenses and final sweep), Rescan, Per-unit deep dives, State Analysis, Verification (kill gates and traces by the critic).

Facts mode: compiler (forge build required the `FOUNDRY_VIA_IR=true` environment variable to avoid stack-too-deep). Preflight tooling mode: degraded, because slither is not installed, so no static-analysis signal table was produced during recon.

Limitations, stated honestly:
- No executable PoCs were run in this pipeline; the critic performed code-trace verification only, so every finding is evidenced as REASONED [CODE-TRACE]. PoCs are recommended for the Critical and High findings.
- The README's automated-findings gist (publicly known issues) was not fetched (no web access), so some findings may overlap with publicly known automated results; known issues from the previous audit readme were applied at Gate H.
- Preflight warnings: rescan reinforced SOL-006 (supply==0 launch path mints 1000 FPS for dust) and SOL-001 (the reward-from-notifyLoss drain also works on expired zero-debt positions).

Methodology derived from Krait by Zealynx Security.

```
───────────────────────────────────────────────────
📋 7 findings saved to .audit/solidity/findings.json
───────────────────────────────────────────────────
```
