# Solidity heuristics

Ported from Krait (heuristics-core Solidity sections + heuristics-extended). IDs unchanged.
Load together with `domains/defi/heuristics.md`.

## Core heuristics (Solidity)

**Arbitrary External Calls (AEC-01 to AEC-03):**
- AEC-01: User-controlled call target → drain approved tokens? selfdestruct?
- AEC-02: Callback after state change → re-enter during callback? grief via revert?
- AEC-03: Multicall/batch → msg.value reuse? bypass individual restrictions?

**Read-Only Reentrancy (ROR-01):**
- ROR-01: View function during callback window → stale/manipulated value for other protocols?

**Proxy/Upgrades (PRX-01, PRX-02):**
- PRX-01: Initializer → _disableInitializers in constructor? Direct implementation init?
- PRX-02: Delegatecall → Storage layout match? Collision? Gap array?

**Share Inflation (SI-01):**
- SI-01: ERC4626 → Virtual offset present? First depositor donation attack?

**Transient Storage (TS-01):**
- TS-01: TSTORE/TLOAD → Cleared after tx? Multicall stale values? Replaces reentrancy guard?

**Missing Return Check (MRV-01):**
- MRV-01: ERC20 transfer/approve → safeTransfer used? USDT no-return-bool?

**Signatures (SIG-01, SIG-02):**
- SIG-01: EIP-712/permit → Replay protection? chainId? Cross-contract? ecrecover(0)?
- SIG-02: Permit2 → Front-run? Nonce invalidation? Griefing?

**ETH Handling (ETH-01, ETH-02):**
- ETH-01: Payable → msg.value checked? Excess locked? Refund on partial fail? selfdestruct force-send?
- ETH-02: ETH to external → Recipient without receive()? Revert bricks function? Use WETH?

**Token Hooks (TOK-01 to TOK-03):**
- TOK-01: ERC721/1155 safeTransfer → onReceived callback reentrancy?
- TOK-02: Non-standard decimals → Assumes 18? USDC(6)/WBTC(8) precision loss?
- TOK-03: Wrapper token decimals ≠ underlying decimals → In Compound forks, cToken/vToken has 8 decimals but underlying has 18. Any code using `vToken.decimals()` to scale the UNDERLYING amount is wrong by 10^10. Check: is `token.decimals()` being used for the token itself, or incorrectly for its underlying?

**CREATE2/CREATE (C2-01, C2-02):**
- C2-01: CREATE2 deterministic deployment → Front-run address? Destruction + redeploy state reset?
- C2-02: CREATE (nonce-based) deployment → Reorg attack? If factory uses `new Contract()` (not CREATE2), address depends on nonce. During chain reorg, attacker can front-run deployment and steal the address. Higher risk on L2s/Polygon. Check: does the factory use CREATE or CREATE2?

**Loop Control Flow (LOOP-01):**
- LOOP-01: Manual loop increment with `continue` → Does `continue` skip the increment? In `for(uint i=0; i < len;) { ... unchecked { i++; } }` patterns, `continue` bypasses the increment → infinite loop. Check every `continue` and `break` in loops with manual increments.

**Reentrancy (RE-01):**
- RE-01: Cross-function → Function A has nonReentrant, function B doesn't, both share state?

**Cross-Chain / Bridge (BRIDGE-01 to BRIDGE-04):**
- BRIDGE-01: LayerZero integration → Minimum gas enforced for destination execution? If not, cross-chain message arrives but execution fails silently. Check adapterParams/options for minDstGas.
- BRIDGE-02: Destination liquidity → Does the destination contract assume sufficient token balance (WETH, bridged tokens) exists? If destination router has insufficient WETH, user's cross-chain TX fails with no refund path.
- BRIDGE-03: Stale swap parameters → Cross-chain messages have latency. Swap params (amountOutMin, deadline) may be stale on arrival. Is there a recovery path when destination swap fails?
- BRIDGE-04: Refund routing → When bridge/swap fails, where does the refund go? To the adapter contract (stuck forever) or back to user? Trace the full refund flow.

**DeFi Integration Specific (CURVE-01, UNI-01, CHAINLINK-01):**
- CURVE-01: Curve pool integration → Does the adapter correctly handle: (a) killed/paused pools, (b) native coin vs WETH distinction, (c) ETH ocean ID vs WETH ocean ID, (d) tricrypto vs 2pool differences in indexing? Check every adapter's token index mapping against the actual pool.
- UNI-01: UniV3 tick math → For negative tick deltas, does the price calculation round UP? `tickCumulativesDelta / period` must use different rounding for negative values. Also check: slippage protection on all NonfungiblePositionManager calls, deadline != block.timestamp, and sqrtRatioAtTick for boundary ticks.
- CHAINLINK-01: Chainlink feed assumptions → Does the code check: (a) staleness (updatedAt + heartbeat < now), (b) zero/negative price, (c) roundId completeness, (d) L2 sequencer uptime? Also: does it use BTC feed for WBTC (depeg risk)?

**Callback Exploitation (CALLBACK-01):**
- CALLBACK-01: ERC721/1155 callback as attack vector → onERC721Received and onERC1155Received give the RECIPIENT execution control during safeTransfer. Can the recipient: (a) re-enter to manipulate collateral configs, (b) prevent liquidation by reverting in the callback, (c) exploit stale state during the callback window? This is a recurring HIGH in audits.

**Hook Conflicts (HOOK-01):**
- HOOK-01: Transfer hook blocks admin actions → If _beforeTokenTransfer blocks transfers from/to restricted addresses, can admin still burn tokens FROM restricted addresses? The burn function is internally a transfer(from, address(0)), so the hook may block the admin burn that exists specifically to handle restricted addresses.

**Hash Collision (PACKED-01):**
- PACKED-01: abi.encodePacked collision → If abi.encodePacked is used for hash keys with multiple dynamic-length or address+uint parameters, different inputs can produce the same hash. Especially dangerous for bridge txnHash (different senders + amounts can collide if nonce is global not per-sender).

**Permit/Approval (PERMIT-01):**
- PERMIT-01: ERC20 permit token validation → When a contract accepts permit signatures, does it verify the token address matches the expected asset? A permit for the wrong token may still produce a valid ecrecover result, letting an attacker use a permit from a different token.

**Modifier Sibling Diff (MODIFIER-01) — catches 20% of missed findings:**
- For each contract, extract ALL modifiers used by state-changing functions. List them: `| Function | Modifiers |`. Flag any function MISSING a modifier that its siblings have. Example: if `bond()`, `unbond()`, `transferBond()` all have `autoCheckpoint` but `withdrawFees()` doesn't → candidate. Mechanical check — don't rely on judgment.

**Cross-Chain Replay / Domain Separation (REPLAY-01):**
- For multi-chain deployments: (1) Is chainId included in ALL signature domains? (2) Can a UserOperation/signature executed on chain A be replayed on chain B? (3) Are nonces chain-specific or global? (4) Does account creation use CREATE2 with chain-dependent salt? If cross-chain replay is possible with user funds at risk → HIGH.

## Extended heuristics

> **Usage**: Read during Tier 1 deep analysis in Pass 2. NOT a module — always available for reference.
> **Source**: Curated from pashov/skills (MIT) — 58 general-advanced vectors organized by category.
> Each entry: `[P] VECTOR-NAME: one-line detection instruction`

---

### Assembly / Yul / Low-Level

- [P] DIRTY-BITS: Check if higher-order bits are cleaned after assembly operations — `calldataload`, `mload` return full 256 bits; if used as `address` or `uint96`, dirty bits corrupt values
- [P] SIGNED-INT-ASSEMBLY: Assembly arithmetic is unsigned by default — if `sdiv`, `smod`, `slt`, `sgt` not used for signed values → wrong results for negative numbers
- [P] RETURNDATA-ZERO: `returndatasize()` used as zero shorthand — breaks if ANY external call was made earlier in the call (returndatasize reflects LAST call)
- [P] FREE-MEMORY-PTR: If assembly writes past `mload(0x40)` without updating the free memory pointer → Solidity compiler may overwrite the data later
- [P] MEMORY-STRUCT-STORAGE: Modifying a memory copy of a storage struct does NOT write back to storage — changes lost silently
- [P] DELEGATECALL-PROPAGATION: Assembly `delegatecall` must propagate both `return` and `revert` data — missing either causes silent success on failure or lost return values
- [P] CREATE-ZERO-CHECK: `CREATE`/`CREATE2` returns `address(0)` on failure but doesn't revert — if return value unchecked → protocol operates with zero-address contract
- [P] CALLDATALOAD-OOB: `calldataload(offset)` beyond calldata length returns zero-padded — if protocol reads optional params this way, it silently uses 0
- [P] SCRATCH-SPACE: Writing to memory `0x00-0x3f` (scratch space) then calling a Solidity function → compiler may overwrite scratch space for hashing
- [P] MSTORE8-PARTIAL: `mstore8` only writes lowest byte — remaining 31 bytes unmodified. If later read with `mload`, stale data included

### Storage / Memory / State

- [P] STORAGE-COLLISION-PROXY: Implementation storage slot 0 overlaps with proxy's `_implementation` slot → upgrade corrupts implementation address
- [P] IMMUTABLE-PROXY: `immutable` variables are stored in bytecode — proxy `delegatecall` reads the PROXY's bytecode (which has no immutables) → always returns 0
- [P] STORAGE-WRITE-ARBITRARY: If user-controlled index reaches a `sstore(slot, value)` → arbitrary storage write → full contract takeover
- [P] PACKED-STORAGE-DIRTY: When writing to a packed storage slot, must preserve adjacent values — assembly `sstore` without masking corrupts packed variables
- [P] TRANSIENT-MULTICALL: `TSTORE` values persist across calls within a tx — in multicall/batch contexts, transient storage from interaction 1 leaks into interaction 2

### Accounting / Precision / Math

- [P] UNSAFE-DOWNCAST: `uint128(x)` does NOT revert in Solidity 0.8+ — silently truncates. Every explicit downcast is a potential state corruption
- [P] SMALL-TYPE-OVERFLOW: `uint32` timestamps overflow in year 2106, `uint48` in year 8.9M — but `uint32` for BLOCK NUMBERS overflows much sooner on L2s with fast blocks
- [P] DIVISION-BEFORE-MULTIPLY: `(a / b) * c` loses precision — rewrite as `(a * c) / b`. Common in fee calculations
- [P] ROUNDING-DIRECTION: Protocol-favorable rounding: `deposit` rounds DOWN (fewer shares), `withdraw` rounds UP (more assets per share). Reversed = drain
- [P] FEE-DOUBLE-APPLY: Sequential fees each on REMAINING amount — total must be < 100%. If each fee calculated on GROSS → total can exceed 100%
- [P] PRECISION-MISMATCH-LIBS: Two math libraries with similar names but different precision bases (1e6 vs 1e18 vs 1e27) — wrong library at any call site → orders-of-magnitude error
- [P] MULMOD-PHANTOM: `mulmod(a, b, 0)` returns 0, not revert. If modulus is a variable that can be 0 → silent precision loss
- [P] COMPOUND-OVERFLOW: `(1 + rate)^periods` overflows uint256 at high rate*periods combinations — especially dangerous in interest calculations

### Time-Dependent / Ordering

- [P] BLOCK-TIMESTAMP-L2: Block timestamps on L2s can have same timestamp across multiple blocks — time-based logic using `block.timestamp` may not advance as expected
- [P] EPOCH-BOUNDARY-RACE: Actions at exactly the epoch transition — user can act in last moment of old epoch AND first moment of new epoch, potentially double-counting
- [P] DEADLINE-BLOCKTIMESTAMP: `deadline = block.timestamp` is always satisfied — provides zero protection. Must be user-supplied from off-chain
- [P] NONCE-REVERT: If nonce is incremented inside a sub-call that reverts → nonce not incremented but main call succeeds → replay with same nonce
- [P] RETROACTIVE-PARAM: Admin changes rate/fee/duration → applies retroactively to in-flight operations (auctions, cooldowns, pending withdrawals)

### Array / Mapping / Data Structures

- [P] DELETE-ARRAY-GAP: `delete array[i]` sets element to 0 but doesn't shift — leaves gap. If later code assumes dense array → skips entries
- [P] MERKLE-LEAF-REUSE: If Merkle proof doesn't include a `claimed[leaf]` check → same proof reused for multiple claims
- [P] ENUMERABLE-GAS: `EnumerableSet.remove` swaps last element into removed slot — changes ordering. If any logic depends on order → broken
- [P] MAPPING-DELETE: `delete mappingOfStruct[key]` zeroes the struct but doesn't remove the key — `mapping[key].someField == 0` may be confused with "never set"
- [P] UNBOUNDED-PUSH: Array grows via `push()` without max length check → eventual gas limit DoS on iteration

### Emergency / Admin / Lifecycle

- [P] PAUSE-LIQUIDATION: If `whenNotPaused` is on `liquidate()` → pausing during crash prevents liquidation → bad debt accumulates
- [P] IRREVOCABLE-ROLE: Roles can be granted but never revoked — compromised role holder persists forever
- [P] INIT-REENTRANCY: During `initialize()`, contract state is partial — if an external call happens mid-init → reenter to exploit incomplete state
- [P] SELFDESTRUCT-FORCE-ETH: `selfdestruct(target)` (pre-Dencun) force-sends ETH — breaks `address(this).balance`-based accounting
- [P] FRONTRUN-INIT: Separate `deploy()` and `initialize()` txs → attacker front-runs init with malicious params

### Token / ERC Patterns

- [P] ERC777-REENTER: ERC777 `tokensReceived` hook gives recipient execution during transfer — reentrancy even with SafeERC20
- [P] PERMIT-WRONG-TOKEN: `permit(token, owner, spender, value, deadline, v, r, s)` — if `token` is not validated, permit from a different token may produce valid ecrecover
- [P] REBASE-CACHE: If protocol caches `balanceOf` for a rebasing token → cache becomes stale after rebase → accounting drift
- [P] FOT-ACCOUNTING: `transfer(amount)` delivers `amount - fee` — if protocol assumes `amount` was delivered → inflation, eventually drains
- [P] NFT-CALLBACK-REENTER: `safeTransferFrom` triggers `onERC721Received` — recipient gets execution during transfer. If state is partially updated → exploit
- [P] APPROVAL-RACE: ERC20 `approve(newValue)` without first setting to 0 → front-run: spender uses old + new allowance
- [P] MSGVALUE-LOOP: `msg.value` in a loop or multicall → same ETH counted multiple times. Each iteration uses the SAME `msg.value`

### Cross-Contract / Integration

- [P] RETURN-BOMB: External call returns huge data → calling contract OOGs copying return data. Use assembly `call` with bounded returndatasize
- [P] CROSS-REENTRANCY: Function A has `nonReentrant`, function B doesn't, both read/write same state → reenter B from A's external call
- [P] DIAMOND-STORAGE: Diamond proxy storage must be namespaced — if two facets use the same storage slot → silent corruption
- [P] FLASH-CALLBACK-TRUST: Flash loan callback — verify `msg.sender` is the expected pool. If callback doesn't validate caller → attacker triggers fake callback
- [P] EXTERNAL-SILENT-FAIL: External call silently returns without effect (mint returns without minting) → protocol continues with wrong assumptions

## Lens B additions

Solidity items of Krait's Lens B (`engine/mindsets.md`), verbatim:

- **[Edge Case]** What happens with amount=0, amount=1 wei, amount=type(uint256).max, or first/last depositor?
- **Payment destination correctness (Module O)**: Is `owner()` (deployer) vs `ownerOf(tokenId)` (NFT holder) correct? Double payout? Conditional payment with unconditional cost?

## Lens C additions

Solidity items of Krait's Lens C (`engine/mindsets.md`), verbatim:

- Reentrancy via callbacks (ERC721/1155 onReceived, ETH receive)
- Version compatibility: Safe version, OZ version, Solidity version

## Lens D additions

Solidity items of Krait's Lens D (`engine/mindsets.md`), verbatim:

- **[Spec Auditor]** Does this ERC implementation match the EIP spec exactly? Character-by-character for EIP-712.
- Type cast safety: every uint128(x), uint96(x) — can source exceed target max?
- EIP-712 typehash verification: character-by-character comparison
- Standard compliance (ERC20/721/4626/3156): actual vs spec

## Detector modules (Solidity)

(ported in a later task)

## Recon additions

(ported in a later task)

## Security strengths examples

Solidity examples for the Security Strengths section of `engine/report-template.md`, verbatim
from Krait's report template:

- **Access control model**: What pattern is used (Ownable2Step, AccessControl, role-based)? Is it consistent across all privileged functions?
- **Reentrancy protection**: Are state-mutating external calls guarded? CEI pattern followed? nonReentrant modifier coverage?
- **Arithmetic safety**: Solidity 0.8+ checked math, explicit unchecked blocks only where safe, SafeCast usage for downcasts?
- **Battle-tested dependencies**: Which libraries (OpenZeppelin vX.Y, Solmate, etc.)? Are they current versions?
- **Upgrade safety**: If upgradeable — initializer guards, storage gap patterns, UUPS vs Transparent?

Example bullet: `- **[Category]**: [Specific observation with contract/file names — e.g., "All 8 state-mutating functions in CfdEngine.sol follow CEI pattern with nonReentrant guards"]`
