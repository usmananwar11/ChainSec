# DeFi heuristics (chain-agnostic)

Ported from Krait heuristics-core; IDs unchanged.

Each heuristic was extracted from a real missed finding in a blind shadow audit, or from
a real exploit. They are **triggers**, not a checklist to recite: match the trigger
against the code in front of you, and only then apply the check.

Heuristics with a "missed in N shadow audits" note earned their place by costing Krait a
real finding. Treat those as mandatory whenever their trigger appears.

---

**Business Logic (BL-01 to BL-12):**
- BL-01: Multi-step process → Can steps execute out of order?
- BL-02: State machine → Can transitions be skipped/reversed?
- BL-03: Dual accounting (internal + balanceOf) → Can they diverge? Donation attack?
- BL-04: Reward distribution → Stake-before-distribution gaming? Double-claim?
- BL-05: Auction/timelock → Griefing? Expired execution? Timestamp manipulation?
- BL-06: Whitelist/blacklist → Transfer through intermediary bypass?
- BL-07: Liquidation → Over-extraction? Self-liquidation profit? Oracle-triggered?
- BL-08: Withdrawal queue → Front-run? Exchange rate locked at request or fulfillment?
- BL-09: Fee-on-transfer tokens → amount sent != amount received? Rebasing stale cache?
- BL-10: ERC4626/share vault → First depositor inflation? (Only if LACKS virtual offset)
- BL-11: Governance voting → Flash loan votes? Snapshot timing? Transfer-and-revote?
- BL-12: Cross-chain/bridge → Replay? Source chain verification? Failed message recovery?

**Fee Logic (FDC-01, FDC-02):**
- FDC-01: Sequential fees → Each on REMAINING amount? Total bounded < 100%?
- FDC-02: Fee precision → Consistent denominator? Division before multiplication? Rounding direction?

**Oracle (ORC-01, ORC-02):**
- ORC-01: AMM spot price → Flash loan manipulable? Use TWAP instead?
- ORC-02: Chainlink → Staleness check? Zero price? roundId? L2 sequencer?

**Access Control (AC-01, AC-02):**
- AC-01: Multiple roles → Escalation? Admin can grant critical roles? Compromised non-critical causes fund loss?
- AC-02: Ownership transfer → Two-step? Wrong address permanent loss?

**Flash Loan (FL-01):**
- FL-01: balanceOf-based accounting → Flash loan deposit manipulation?

**NFT/Gaming Attributes (NFT-01 to NFT-03):**
- NFT-01: Attribute manipulation via user-controlled params → Can users choose/influence their NFT attributes during mint/redeem? If params like weight/element come from user input → they'll pick the rarest.
- NFT-02: Randomness manipulation via revert → If attributes are assigned from on-chain randomness, can users revert and retry until they get desired attributes? Only safe with commit-reveal or VRF.
- NFT-03: Type/category mismatch in limits → If per-type limits exist (e.g., maxRerolls per fighterType), can users pass a DIFFERENT type than the actual to bypass the check?

**Access Control Extended (AC-03, AC-04):**
- AC-03: Periphery contract access control → Main contracts may have proper access control, but check EVERY helper/adapter/bridge token contract. DcntEth.setRouter() with no access control = anyone takes over.
- AC-04: Role irrevocability → If roles can be GRANTED (addMinter, addStaker) but NEVER REVOKED (no removeMinter), compromised or malicious role holders persist forever. Check every role: is there a symmetric revoke function?

**Injection (INJ-01):**
- INJ-01: On-chain metadata injection → Does tokenURI, contractURI, or any on-chain string concatenation include user-controlled data without escaping? JSON injection via art piece names/descriptions → malicious metadata, broken marketplaces.

**Governance (GOV-01, GOV-02):**
- GOV-01: Phantom voting power → When governance tokens are burned/auctioned/locked, is the voting power properly removed from quorum denominators? Inaccessible tokens inflating totalVotesSupply → quorum unreachable.
- GOV-02: Delegation griefing → Can a malicious delegatee prevent the delegator from redelegating? If delegatee's checkpoint manipulation causes gas exhaustion on redelegate → permanent delegation lock.

**Precision (PR-01 to PR-03):**
- PR-01: Small amount division → Rounds to zero? Repeated small tx profit? **Can attacker FORCE rounding to zero via flash loan (inflate denominator)?** If division uses totalSupply or reserve as denominator, and attacker can inflate it → zero-amount exploit.
- PR-02: Price/rate as integer → Rounding direction safe? One-sided manipulation?
- PR-03: Dual conversion (assets↔shares) → Round OPPOSITE directions? mint(1 wei) paying 0?

**External Protocol Integration (EXT-01 to EXT-03):**
- EXT-01: Permissionless external calls → Can anyone call getReward/claim/harvest on behalf of the contract? If yes → front-running breaks assumed state.
- EXT-02: External shutdown/migration → What if Convex pool shuts down? What if operator changes? What if Aave market is deprecated? Does the contract have a fallback?
- EXT-03: Silent external failures → Does the external call silently return without effect (instead of reverting)? If contract assumes effect happened → wrong state.

**Batch/Multi-Call Interaction (BATCH-01):**
- BATCH-01: Cross-interaction balance accounting → In batch/multicall systems with intra-transaction balance deltas, can a user reference balances from earlier interactions that haven't been finalized? Can wrapped token balances be spent before they exist? Trace the delta accounting across the full batch — this is NOT visible from single-function analysis.

**Economic Design (ECON-01, ECON-02):**
- ECON-01: Circular/endogenous collateral valuation → Is a token's value derived from TVL that includes the token itself? (e.g., kerosine valued by TVL but counted as collateral in TVL.) If yes → reflexive death spiral on downturn.
- ECON-02: Liquidation profitability → Is it ALWAYS profitable to liquidate? Check: does liquidator receive ALL collateral types? Is there a minimum position size? Can positions become so large that no one has enough debt token to liquidate? If liquidation is ever unprofitable → bad debt accumulates.

**Missing Functionality (MISSING-01, MISSING-02):**
- MISSING-01: Missing unsetters/clearers → For every admin setter function (addChain, setOracle, addAsset), does a corresponding REMOVER exist? If config can only be added, never removed → permanent misconfiguration risk.
- MISSING-02: Restriction coverage gaps → If a restriction system exists (blocklist, pause, role restrictions), does it cover ALL exit paths? Check every function that moves value out — if even one path bypasses the restriction, it's useless. (e.g., blocklist blocks transfer() but not unstake() → restricted users exit via unstake.)

**Zero-Value Operations (ZERO-OP-01):**
- ZERO-OP-01: Zero-value operations as griefing → Can a zero-value deposit, transfer, or approval be used to grief? Common pattern: deposit(0) updates lastDepositBlock, preventing same-block withdrawals. Attacker front-runs withdrawal with deposit(0) to block it permanently.

**Library Precision Mismatch (LIB-01):**
- Two math libraries with similar names but different precision? (MathUtils 1e6 vs PreciseMathUtils 1e27). Wrong library at any call site = silent precision loss or underflow.

**Cross-Chain Decimal (CHAIN-01):**
- When values cross chains, is token decimal normalized? Same token can have different decimals on different chains (USDC: 6 on ETH, 18 on BSC).

**External Skim/Sweep Destination (EXT-SKIM-01):**
- When calling external `skim()`, `sweep()`, `rescue()`, `claimRewards()`: where do tokens ACTUALLY go? To caller or external treasury? Read the external code.

**Hash Field Completeness (HASH-01):**
- If a struct is hashed for verification, does hash include ALL struct fields? Compare field-by-field. Missing field = anyone can substitute arbitrary values.

**ID Mutability (ID-01):**
- Can a loan/position/order ID change after creation (merge, refinance)? Do ALL consumers handle ID changes? Stale ID = broken accounting.

**TVL Staked Balance (TVL-01):**
- Does TVL calculation account for tokens staked in external gauges/farms, not just `balanceOf(this)`? Missing staked tokens = understated TVL = wrong share prices.

**Zero-Weight Actor (ZERO-WEIGHT-01):**
- Can an actor with 0 weight/stake still trigger state changes affecting other users? Slashed validator voting, 0-balance user distributing, etc.

**Wrong Constant / Magic Number (CONST-01) — missed in 2 shadow audits:**
- For EVERY named constant (WAD, RAY, ONE_HUNDRED_WAD, BPS, PRECISION, etc.), verify: (1) its value matches its name — `ONE_HUNDRED_WAD` should be `100 * 1e18` not `1e20` (these ARE different if WAD != 1e18 in the codebase), (2) it's used in the correct context — a percentage constant used where an absolute constant is needed, or vice versa, (3) compare every usage site — if the same formula uses WAD in one function and ONE_HUNDRED_WAD in another, one is wrong. This is mechanical: `grep` for all constant definitions, verify values, trace every usage.

**Gauge/Voting Removal Safety (GAUGE-01) — missed in 1 shadow audit:**
- When a gauge, market, pool, or entity can be REMOVED or DEACTIVATED: can users who interacted with it before removal still unwind their positions? Check: (1) Can users withdraw votes/stake/liquidity from removed entities? (2) Does the removal function properly update all user-facing state (voting power, rewards, balances)? (3) Is there a contradiction between "allow cleanup on removed entity" guards and "entity must exist" guards that prevents unwinding? If users' voting power, staked tokens, or rewards get permanently locked when an entity is removed → HIGH.
