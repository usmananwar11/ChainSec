# Cairo heuristics

Cairo 1+ / Starknet heuristics. The core set is written for ChainSec from the cairo-auditor
security notes (MIT, keep-starknet-strange) and well-established Starknet behavior; the extended set
is cairo-auditor's 170 attack vectors with their numbers kept (`AV-<n>`). Credit: [ATTRIBUTION.md](ATTRIBUTION.md).
Load together with `domains/defi/heuristics.md`. Vulnerability classes: [patterns/README.md](patterns/README.md).

## Core heuristics (Cairo)

Where the engine names a Solidity-era mandatory heuristic, use the Cairo equivalent:

| Engine ID | Cairo equivalent |
|---|---|
| SIG-01, SIG-02, REPLAY-01, PERMIT-01 | SIGN-01 to SIGN-03, AA-03 |
| PRX-01, PRX-02 | INIT-01, UPG-01 to UPG-03, COMP-01 |
| AEC-01 to AEC-03 | LIBC-01, DISP-01, AV-25 |
| RE-01, ROR-01, TOK-01, CALLBACK-01, HOOK-01 | REENT-01, COMP-03 |
| ETH-01, ETH-02, MRV-01 | DISP-02 (no native `payable` value: STRK and ETH are ERC20 contracts) |
| BRIDGE-01 to BRIDGE-04 | L1H-01, L1H-02, MSG-01 to MSG-03 |
| PACKED-01, HASH-01 | FELT-04, AV-116, AV-144 |
| MODIFIER-01 | GUARD-01 |
| TS-01, C2-01, C2-02 | No transient storage; deployment addresses: DEPLOY-01 |

**felt252 arithmetic (FELT-01 to FELT-04):**
- FELT-01: Value math in `felt252` → `+ - *` wrap modulo P = 2^251 + 17·2^192 + 1 with NO panic. `balance - amount` with `amount > balance` yields a huge value. Any balance, amount, price, fee, counter or index held in `felt252` is a candidate.
- FELT-02: `felt252` division (`felt252_div`) is field division (multiply by the modular inverse), not floor division: 10 / 3 is not 3. Any felt252 division in financial math is wrong.
- FELT-03: felt252 ordering and conversions → comparisons near the field boundary misbehave, and a wrapped result looks valid. `u256 → felt252` (`try_into`) fails at ≥ P; `felt252 → ContractAddress` requires < 2^251; 32-byte external identifiers (EVM hashes, other chains' keys) do not fit (AV-169).
- FELT-04: Bit-packing into one `felt252` must stay within 251 bits; check width asserts before packing and the final `try_into`. Parameters fed to hashes, bit ops or storage-key derivation need range checks (AV-145).

**Bounded integers (INT-01 to INT-03):**
- INT-01: `u8`…`u128`, `u256`, `i8`…`i128` panic on overflow/underflow → the bug is a revert, not a wrap. Ask whether an attacker can force that panic on someone else's critical path (liquidation, withdrawal, settlement, epoch close: AV-60).
- INT-02: Explicit opt-outs (`wrapping_*`, `overflowing_*`, `saturating_*`, `u128_overflowing_add`) wrap or clamp silently — treat them like Solidity `unchecked`.
- INT-03: Narrowing `try_into().unwrap()` / `.expect()` on user-influenced values → panic DoS (UNSAFE-TYPE-CONVERSION); `try_into()` with a fallback (`unwrap_or(0)`, `None => 0`) → silent wrong value. Unsigned loop counters decremented past zero (`while i >= 0` on `u32`) panic.

**u256 limbs (U256-01, U256-02):**
- U256-01: `u256` is `{ low: u128, high: u128 }` and serializes as two felts, low first. Decoders over `Span<felt252>` (calldata, L1 message payloads, signed data) that read one felt, swap the limbs, or build `u256 { low: x, high: 0 }` drop or corrupt the high limb. Check every manual `u256 { low, high }` and every `payload.at(i)` decode against the encoder on the other side.
- U256-02: A `u256` storage value spans two slots (base, base + 1). Custom `Store` impls and raw `storage_read_syscall`/`storage_write_syscall` code must read and write both.

**Storage defaults (MAP-01):**
- MAP-01: `Map` reads of a missing key return the type's default (zero, false, zero address) with no panic. Zero must not mean "registered", "authorized" or "valid" (C4 Starknet Perpetual H-01: a zero oracle entry let an attacker sign over zeroed data; AV-62).

**Caller identity (CALLER-01, CALLER-02):**
- CALLER-01: `get_caller_address()` is the immediate caller (the account contract for a top-level invoke). `get_tx_info().account_contract_address` is the transaction's account — using it for auth lets any contract the victim calls act as the victim (AV-87). In an `#[l1_handler]` the L1 sender is the `from_address` parameter; `get_caller_address()` does not identify it.
- CALLER-02: Zero caller. Calls from accounts and contracts never have a zero caller, so `get_caller_address().is_zero()` checks in ordinary entry points are dead code. Protocol-invoked account entry points (`__validate__`, `__execute__`, `__validate_declare__`, `__validate_deploy__`) run with caller zero: an account's `__execute__` must assert the caller is zero, otherwise any contract can make the account execute calls (chipi-pay "unrestricted `__execute__` caller").

**L1 handlers (L1H-01, L1H-02):**
- L1H-01: Every `#[l1_handler]` must assert `from_address` (a `felt252` L1 address, not a `ContractAddress`) equals the stored trusted L1 contract, and that stored value must be set and non-zero. Missing check → anyone on L1 can send a message that mints or credits.
- L1H-02: A handler that reverts leaves the L1 side's state (locked or burned funds) without the L2 effect. Any input-dependent revert (invalid recipient, pause, cap, decode panic) needs an L1 recovery path (message cancellation) or an idempotent retry; trace whether user funds can get stuck.

**L1↔L2 messaging (MSG-01 to MSG-03):**
- MSG-01: L2→L1 `send_message_to_l1_syscall(to_address, payload)`: payload layout (recipient, token, amount as low/high) must match the L1 decoder exactly; `to_address` must be the right L1 contract; the L2 burn/lock must happen before the send (AV-97); amounts within caps (AV-139).
- MSG-02: The Starknet core contract makes each L1→L2 message consumable once (the message hash includes a nonce). App-level replay matters for custom relayed messages: replay keys need the full message identity (AV-29, AV-91); cancellation timestamps must not be overwritable (AV-35, AV-165); one bad message must not block a batch (AV-136, AV-141).
- MSG-03: Address domains: L1 addresses are 20 bytes, Starknet addresses are `felt252` < 2^251. A recipient from L1 must be converted explicitly and validated non-zero; a failing conversion in the handler is an L1H-02 stuck-message path.

**Upgrades (UPG-01 to UPG-03):**
- UPG-01: `replace_class_syscall` / OZ `UpgradeableComponent` (whose `upgrade` is internal — the contract must wrap it with auth): who can reach it, is the class hash non-zero, is there a delay, do all upgrade routes share one gate? The new class applies to later calls; the running call finishes on the old code, so upgrade-then-configure in the same flow needs care (AV-125).
- UPG-02: There is no proxy: storage stays at the contract address and a variable's address is derived from its name. Renaming, retyping, changing `Map` key types or renaming a component substorage strands data. Post-upgrade migrations/initializers must be versioned and not replayable (AV-10, AV-86, AV-118, AV-128).
- UPG-03: Any declared class hash is accepted unless checked: no interface/storage compatibility check (AV-130), downgrade to an older class (AV-113).

**Library calls (LIBC-01):**
- LIBC-01: `library_call_syscall` / `I*LibraryDispatcher { class_hash }` runs another class's code in the caller's context (Cairo's `delegatecall`): it can write any of the caller's storage and use syscalls as the caller. A class hash that is user-supplied, or read from mutable storage without allowlist/timelock, is full takeover (AV-37, AV-85, AV-142).

**External calls (DISP-01, DISP-02):**
- DISP-01: A plain dispatcher call that fails reverts the whole transaction — there is no try/catch, so a token or recipient that panics blocks the caller (a DoS lever). `Safe*Dispatcher` returns `Result`, but some failures (missing contract, undeclared class, return-value deserialization) still revert everything (AV-134, AV-135), and `Err(panic_data)` is attacker-controlled (AV-133).
- DISP-02: ERC20 `transfer`/`transfer_from` return `bool` — check it. Tokens differ in casing (`transfer_from` vs legacy `transferFrom`); runtime selector fallback masks errors (SYSCALL-SELECTOR-FALLBACK-ASSUMPTION). `decimals()` and other metadata are optional (AV-138).

**Reentrancy (REENT-01):**
- REENT-01: Callees can call back. Receiver callbacks (`on_erc721_received`, `on_erc1155_received` via SRC5), caller-supplied contracts and component hooks open windows — apply CEI. OZ `ReentrancyGuardComponent` needs explicit `start()`/`end()`: an early `return` that skips `end()` leaves the guard locked in storage (permanent DoS), and functions sharing state must share the guard (AV-26, CEI-VIOLATION-ERC1155).

**Account abstraction (AA-01 to AA-04):**
- AA-01: `__validate__` must be cheap and deterministic: signature over the transaction hash, no external calls, no storage writes beyond what the protocol allows, returns `starknet::VALIDATED`. `__execute__` must check caller zero (CALLER-02) and the transaction version.
- AA-02: Session keys / delegated signers: block calls to the account itself (`call.to != get_contract_address()`); a selector denylist alone misses camelCase twins and new embedded selectors (`upgrade`, `set_public_key`/`setPublicKey`, `__execute__`, `execute_from_outside_v2`); enforce per-token spending caps and count calls after signature checks (AA-SELF-CALL-SESSION, AV-22, AV-51).
- AA-03: Nonces: the protocol checks the transaction nonce; SNIP-9 `execute_from_outside` has its own nonce that the account must consume, plus `caller` (`ANY_CALLER` is permissive) and `execute_after`/`execute_before` checks; block nested outside execution.
- AA-04: `is_valid_signature(hash, signature)` gets no calls, so it cannot enforce selector policy. Guardian/escape flows must cap every V3 resource bound (L1 gas, L2 gas, tip), not only one (ConsenSys Argent finding).

**Signatures and replay (SIGN-01 to SIGN-03):**
- SIGN-01: Off-chain messages should be SNIP-12 typed data: domain `name`, `version`, `chain_id`, `revision`. No `chain_id` → replay across mainnet/Sepolia/forks. The SNIP-12 hash binds the signer's account but not the verifying contract: two contracts sharing a domain name/version accept each other's signatures unless the message carries the contract address or a contract-scoped nonce (AV-117). `StarkNetDomain` (revision 0) vs `StarknetDomain` (revision 1) mismatches break verification.
- SIGN-02: Every signed action needs a nonce consumed before effects (OZ `NoncesComponent::use_checked_nonce`), scoped per action type (AV-73), advanced on every state transition (AV-68), plus an expiry. Raw `pedersen`/`poseidon` over fields without domain or nonce is replayable.
- SIGN-03: `check_ecdsa_signature` returns `bool` — assert it. Check `Span<felt252>` signature length before indexing, validate public keys on the STARK curve, dedupe signers in multisig thresholds (AV-164), and compare account `is_valid_signature` results to `starknet::VALIDATED`.

**Components (COMP-01 to COMP-03):**
- COMP-01: With `#[substorage(v0)]` a component's members live in the contract's flat namespace (address from the member name alone). Two components, or a component and the contract, declaring the same member name share a slot — OZ prefixes members (`ERC20_balances`, `Ownable_owner`) to avoid this; custom components often do not (AV-111). Custom `Store` packing and `storage_address_from_base` keys bypass namespacing (AV-112).
- COMP-02: Every function of an `#[abi(embed_v0)]` impl is a public entry point. List embedded impls and their selectors (mixins add camelCase twins; OZ account impls expose key rotation); an `InternalImpl` must never be embedded. Component initializers (`ownable.initializer(owner)`) must be called in the constructor — a missed one leaves the owner zero.
- COMP-03: Component hooks (OZ ERC20/ERC721 `before_update`/`after_update`) run on every transfer path. Pause, auth or accounting enforced in a hook must cover all paths; a hook that calls out is a reentrancy window.

**Initialization and deployment (INIT-01, DEPLOY-01):**
- INIT-01: The constructor runs atomically inside the deployment and cannot be front-run. The risk is a post-deploy external `initialize`/`initializer` (UNPROTECTED-INITIALIZER), one that can run again after an upgrade, or OZ `InitializableComponent::initialize()` used from more than one function.
- DEPLOY-01: A contract address is derived from deployer (or zero), salt, class hash and constructor calldata. With `deploy_from_zero` or a non-unique UDC deployment anyone can deploy the same address first; check counterfactual addresses that get funded or registered before deployment.

**Access sibling diff (GUARD-01):**
- GUARD-01: For each contract (with its embedded components), list every state-writing entry point and its guards: `| Function | assert_only_* / caller check | assert_not_paused | reentrancy_guard |`. Flag any function missing a guard its siblings have, including alias and camelCase routes (AV-19, AV-89). Mechanical check — don't rely on judgment.

**Environment (TIME-01, PRIV-01, BOOL-01):**
- TIME-01: Since Starknet v0.14.0 blocks are ~6s (was ~30s), there is a mempool and several sequencers. Block-count windows calibrated for 30s are 5× shorter; ordering is not deterministic, so slippage and deadlines matter; `get_block_timestamp`/block number/tx hash are not randomness.
- PRIV-01: All storage is public (`starknet_getStorageAt`). Stored "secrets" are readable.
- BOOL-01: `&&` binds tighter than `||`: unparenthesized mixed conditions in `assert` often mean something else than intended.

## Extended heuristics

> **Usage**: Read during Tier 1 deep analysis in Pass 2. NOT a module — always available for reference.
> **Source**: cairo-auditor attack vectors (MIT, keep-starknet-strange), 170 vectors in four groups, numbers unchanged.
> Each entry: `AV-<n> Name: detection pattern. FP: when the pattern is safe.`

---

### Access Control + Upgradeability

- **AV-1** Immediate upgrade without delay: privileged `upgrade` path calls `replace_class_syscall` or `upgradeable.upgrade` in one transaction with no schedule/execute split. *FP:* explicit timelock state with pending hash and `now >= scheduled + delay` check.
- **AV-2** Missing class-hash non-zero guard (direct syscall path): direct `replace_class_syscall(new_class_hash)` without `is_non_zero` guard. *FP:* local guard exists or call goes through OZ `UpgradeableComponent` internal guard.
- **AV-3** Constructor critical role without non-zero guard: constructor writes `owner/admin/upgrade/governor` directly with no non-zero validation. *FP:* explicit constructor guard or trusted initializer with proven internal non-zero check.
- **AV-4** Irrevocable privileged role: privileged role seeded at deploy time with no reachable rotate/revoke path. *FP:* exposed ownership/role rotation path exists (for example Ownable transfer or AccessControl grant/revoke).
- **AV-5** One-shot registration of critical dependency: `register_*` write-once gate sets critical dependency and no recovery setter exists (ForgeYields-style risk). *FP:* documented immutable dependency or owner/governance recovery path exists.
- **AV-6** Ungated privileged mutation: external `set_*`, `register_*`, `upgrade*`, or pause path mutates privileged state without caller gate. *FP:* strict access check in-path (`assert_only_*`, role check, or explicit caller assertion).
- **AV-7** Caller alias bypass in access checks: caller stored in alias and compared to wrong role slot or stale authority field. *FP:* alias resolves to correct authority source tied to the same function path.
- **AV-8** External ABI mutation hidden behind helper: externally callable function delegates to helper that mutates privileged state; entrypoint lacks auth. *FP:* helper or parent enforces strict auth with no bypass path.
- **AV-9** Upgrade path reachable from broad role: upgrade guarded by overly broad role set (for example generic admin role with many holders). *FP:* dedicated upgrade role with constrained grant/revoke controls.
- **AV-10** Upgrade initializer omission: class replacement leaves migration state uninitialized, enabling unsafe defaults. *FP:* migration is atomically executed or new class is migration-free by design and documented.
- **AV-11** Mixed ownership models with orphan authority: contract uses both Ownable and AccessControl; privileged paths depend on stale model. *FP:* single authority model or explicit synchronization between models.
- **AV-12** Emergency controls not actually privileged: `pause`, `unpause`, or `emergency_*` paths callable through weak predicate. *FP:* dedicated emergency role, explicit gate, and no user-facing bypass.
- **AV-13** Timelock bypass through alternate upgrade entrypoint: one upgrade path enforces delay while another admin path upgrades immediately. *FP:* all upgrade routes converge on a shared timelock gate.
- **AV-14** Role-admin misconfiguration enables privilege escalation: `set_role_admin` ties sensitive role admin to itself or user-controlled role without constraints. *FP:* role hierarchy maps to governance/owner-only admin chain.
- **AV-15** Upgrade auth delegated to mutable external contract: upgrade permission depends on external contract state that can be swapped or desynced. *FP:* external dependency is immutable or integrity-checked per call.
- **AV-16** Initializer re-entry / double-init path: initializer callable more than once or callable post-deploy by non-trusted party. *FP:* initialized flag and strict deploy-time only gate prevent re-entry.
- **AV-17** Factory dependency validation missing on one constructor branch: multi-branch init validates non-zero dependencies on one branch but not another. *FP:* all constructor/init branches apply identical dependency checks.
- **AV-18** Role revocation impossible after bootstrap: privileged role granted in constructor but no external revoke flow (common mis-embed of AccessControl). *FP:* role management ABI (`grant/revoke/renounce`) is exposed and reachable.
- **AV-19** Pause bypass via equivalent state-mutating function: deposits/transfers are paused, but equivalent state-changing route remains open. *FP:* pause invariant enforced at shared internal gate for all equivalent routes.
- **AV-20** Admin transfer lockout edge: admin transfer path allows zero/self/inconsistent target and can lock governance flows. *FP:* transfer validates target and preserves recoverability guarantees.
- **AV-81** Mixed authority drift between Ownable and AccessControl: one privileged path checks Ownable while another checks role state, enabling desynced authority. *FP:* single authority model or explicit sync invariant across both models.
- **AV-82** Mutable timelock-delay downgrade: governance can set timelock delay to zero (or near-zero) and immediately execute privileged action. *FP:* delay changes are themselves timelocked with minimum floor enforcement.
- **AV-83** Schedule cancellation by lower privilege: pending upgrade/action can be canceled by role that cannot schedule/execute it. *FP:* cancellation privilege is equal or stricter than scheduling privilege.
- **AV-84** Pending upgrade overwrite race: new pending class hash overwrites existing schedule without explicit cancellation workflow. *FP:* overwrite blocked unless prior schedule is canceled/expired.
- **AV-85** Library-call governance bypass: privileged flow uses `library_call` path controlled by mutable class hash/registry. *FP:* class hash is immutable or strictly timelocked and allowlisted.
- **AV-86** Upgrade without initializer version guard: post-upgrade initializer can be replayed because version/init slot is not advanced. *FP:* initializer versioning is monotonic and replay-safe.
- **AV-87** Caller source confusion in auth check: auth compares wrong caller source (`get_tx_info` account vs `get_caller_address`) for path semantics. *FP:* caller primitive matches the actual trust boundary of the entrypoint.
- **AV-88** Role grant seeds invalid principal: grant/seed path accepts zero or malformed principal for critical role. *FP:* role grant validates non-zero and expected principal domain.
- **AV-89** Pause gate bypass via alias entrypoint: one selector is paused while an equivalent alias/casing path remains active. *FP:* shared pause gate covers all equivalent privileged/state-mutating routes.
- **AV-90** Internal privileged helper exposed externally: helper intended for privileged internal use is reachable through unguarded external wrapper. *FP:* every external wrapper enforces the same auth invariant as the helper contract.
- **AV-121** Constructor assumes deployer role without explicit grant: constructor logic assumes deployer already holds a specific role (governor, admin) without granting it, causing post-deploy auth failures or requiring external setup. *FP:* role is explicitly granted in constructor or documented as a pre-deployment requirement with verified setup script.
- **AV-122** Ownership transfer to non-deployed or zero-class contract: `transfer_ownership` or admin transfer accepts any `ContractAddress` without validating the target is a deployed contract or non-zero. *FP:* transfer validates target is non-zero and optionally confirms deployment via class hash check.
- **AV-123** Forced shutdown override precedence inversion: contract has inferred mode plus forced/shutdown override, but inferred-mode branch returns early before forced override check, leaving critical paths active when forced shutdown is set. *FP:* forced override is checked first (or centralized) before any inferred-mode branch logic.
- **AV-124** Extension or module parity failure on new capability: new state override or mode (e.g., overwrite shutdown) implemented in core but not propagated to extension/oracle/adapter modules that also enforce the same state. *FP:* all extensions implement or delegate to the same capability surface as core.
- **AV-125** Non-atomic upgrade-then-configure race window: upgrade (`replace_class_syscall`) and post-upgrade configuration happen in separate transactions, creating a window where new code runs with stale config. *FP:* upgrade and migration are atomic (same transaction) or new class is backward-compatible by design.
- **AV-126** Multi-sig threshold set below safe minimum: multi-sig or quorum threshold can be set to zero or one, allowing single-signer execution of privileged actions. *FP:* threshold setter enforces minimum floor (e.g., `threshold >= 2`) or is immutable.
- **AV-127** Factory-deployed contract inherits deployer privilege: factory deploys child contracts that inherit factory address as admin/owner, but factory itself has broad access or is upgradeable. *FP:* child contracts use explicit admin parameter independent of factory, or factory is immutable with constrained interface.
- **AV-128** Upgrade migration resets or drops permission state: post-upgrade migration overwrites or fails to carry forward role/permission mappings from previous class, silently dropping access control state. *FP:* migration explicitly preserves or re-validates all permission state, with post-migration invariant checks.
- **AV-129** Self-revocation of sole admin locks governance: sole admin can call `revoke_role` or `renounce_ownership` on themselves with no remaining admin, permanently locking privileged functions. *FP:* revocation checks that at least one admin remains, or renounce requires pending transfer to be accepted first.
- **AV-130** Arbitrary declared class hash accepted without compatibility verification: upgrade or registry path accepts any declared class hash without validating expected interface, storage-layout compatibility, or migration invariants, allowing incompatible implementations to be installed. *FP:* class hash is allowlisted or validated for interface/version/storage compatibility before upgrade, with migration invariants checked explicitly.
- **AV-131** Proxy storage layout collision after class replacement: new implementation class uses storage slots that collide with proxy-level state (admin slot, implementation slot), corrupting proxy metadata. *FP:* implementation uses explicit non-overlapping Starknet storage namespaces/substorage roots and preserves proxy-reserved metadata invariants.
- **AV-132** Authorization/policy check occurs after state mutation on non-reverting error path: function writes critical state before auth/policy check or before a non-reverting `Err` return branch, allowing inconsistent state when the operation reports failure without transaction revert. *FP:* auth/policy checks execute before any state write and failure paths do not persist partial mutations.

### External Calls + Reentrancy + Messaging

- **AV-21** CEI violation on ERC1155 transfer path: state mutation happens after `safe_transfer_from` (directly or through helper chain). *FP:* critical state committed before interaction or robust non-reentrant guard blocks re-entry.
- **AV-22** Session self-call hazard: session execution loop permits calls to account contract itself. *FP:* explicit self-target block plus policy constraints prevent self-call.
- **AV-23** Selector fallback assumption: on syscall error, logic retries alternate selector and masks root failure. *FP:* single canonical selector with fail-fast behavior.
- **AV-24** Untrusted callback caller: callback handler mutates state without validating caller contract identity. *FP:* callback explicitly pinned to expected contract address.
- **AV-25** External call proxy without target constraints: privileged function forwards arbitrary `call_contract_syscall` target/selector/calldata. *FP:* strict allowlist, Merkle policy verification, or immutable target set.
- **AV-26** Cross-function reentrancy window: helper performs interaction; parent updates critical state after helper returns. *FP:* shared lock or state update-before-interaction across entire call chain.
- **AV-27** Transfer consistency mismatch: one transfer primitive disabled while equivalent primitive remains enabled (ForgeYields redeem NFT pattern). *FP:* mismatch is intentional and protected by additional invariants.
- **AV-28** Caller-controlled reward contract invocation: harvest/claim path takes arbitrary reward contract and invokes it. *FP:* caller and reward contract are both tightly policy-constrained.
- **AV-29** L1/L2 message replay gap: consumed message nonce/hash not tracked, allowing repeated processing. *FP:* replay set keyed by unique message hash and nonce.
- **AV-30** Callback state confusion with stale flags: callback logic depends on flags written only after interaction. *FP:* callback preconditions are finalized before external call.
- **AV-31** Fee-transfer call result ignored: transfer return value ignored and state progresses as if payment succeeded. *FP:* transfer failure reverts before state transition.
- **AV-32** External denial path swallowed: external call failures are caught/logged but execution continues into state writes. *FP:* denial path reverts or compensates with full rollback.
- **AV-33** ERC721 callback reentrancy on order fill: `transfer_from`/`safe_transfer_from` to callback-capable recipient happens before order status commit. *FP:* order status or nonce invariant prevents same-order reentry before callback.
- **AV-34** Fee-on-transfer token accounting drift: logic assumes nominal transfer amount equals received amount on external token call. *FP:* post-transfer balance delta is used for accounting.
- **AV-35** Message cancellation timestamp overwrite: repeated cancellation start overwrites prior timestamp and weakens timeout assumptions. *FP:* first cancellation timestamp is immutable or monotonic.
- **AV-36** Cross-domain origin verification missing: L1/L2 handler validates payload but not expected sender/domain binding. *FP:* explicit sender/domain hash verification in message path.
- **AV-37** Library-call target controlled by user input: `library_call`/dispatcher target derives from user-controlled path without allowlist. *FP:* target selector pair pinned to immutable registry.
- **AV-38** External decoder response schema trust: external decoder/sanitizer output is accepted without shape/value validation. *FP:* strict schema and bounds checks on returned payload.
- **AV-39** Cross-contract call succeeds with wrong selector casing fallback: retrying camelCase/snake_case on failure accidentally invokes unintended function. *FP:* explicit ABI mapping known at compile-time with no runtime selector fallback.
- **AV-40** Event emission before interaction finality: event logs success before external call outcome is known, confusing off-chain automation. *FP:* success events emitted only after all critical interactions and writes succeed.
- **AV-91** L1 handler replay by weak message keying: L1 handler marks processed messages with incomplete key material (missing nonce/sender/value domain). *FP:* replay key includes full domain-separated message identity.
- **AV-92** Dispatcher callback reentrancy via trusted adapter: adapter marked trusted can still re-enter caller path before state finalization. *FP:* reentrancy lock/effects-first invariant spans adapter callback boundaries.
- **AV-93** External return decoding without length validation: call result is decoded into struct/tuple without asserting expected span length. *FP:* decode path validates result shape/length before interpretation.
- **AV-94** Fallback-to-default on external read failure: failed external read (price/balance/config) silently falls back to unsafe default and continues. *FP:* failed read reverts or routes to explicit fail-safe mode.
- **AV-95** Multicall order dependence on mutable shared state: same transaction can reorder calls to bypass per-call assumptions (auth/limits/nonce checks). *FP:* order-independent invariants or explicit topological restrictions are enforced.
- **AV-96** Session signature replay across bundled calls: one signature/nonce authorizes multiple operations without per-call binding. *FP:* signature domain binds call set/hash and nonce monotonicity per execution.
- **AV-97** Bridge emit-before-lock/burn inconsistency: outbound bridge message/event emitted before asset lock/burn is irreversible. *FP:* bridge side effects are emitted only after asset state commit.
- **AV-98** External call target mutable in same tx path: target address can be changed then used immediately in same execution path without delay. *FP:* target mutation and target use are separated by governance delay/checkpoint.
- **AV-99** Post-interaction authorization check: external interaction occurs before caller/role authorization is fully validated. *FP:* full auth and policy checks happen strictly before any external interaction.
- **AV-100** Error-logging without rollback in privileged path: privileged flow catches/logs external error but keeps partial state updates. *FP:* privileged path either reverts or atomically compensates all partial state.
- **AV-133** Safe-dispatcher panic data drives privileged fallback logic: call through a safe dispatcher returns `Result::Err(panic_data)` and caller parses attacker-controlled `panic_data` to choose a privileged fallback path, effectively turning error payload into authorization/config input. *FP:* `Err` branches treat panic payload as opaque diagnostics only; privileged decisions never depend on panic-data content.
- **AV-134** Safe-dispatcher fallback assumes catchability of non-catchable syscall failures: fallback logic assumes all external call failures are catchable, but cases like non-existent contract/class hash or Cairo 0 edge paths revert the entire transaction and bypass fallback. *FP:* fallback logic is limited to documented catchable failure modes and pre-validates contract/class existence where needed.
- **AV-135** Deserialization failure in try_* syscall wrapper causes unexpected revert: `try_call_contract` or similar wrapper reverts on deserialization failure of the return value instead of returning an error, breaking fallback logic. *FP:* wrapper handles both call failure and decode failure paths, or return type is guaranteed by target ABI.
- **AV-136** L1/L2 message ordering gap enables blocking attack: `update_state` or L1 handler processes messages sequentially; a single malformed or oversized message blocks all subsequent messages in the batch. *FP:* messages are processed independently with per-message error isolation, or batch validation rejects invalid entries before processing.
- **AV-137** Race condition in multi-step token activation: token bridge activation requires multiple transactions (deploy + register + configure); between steps, another actor can front-run or interfere with an incomplete activation. *FP:* activation is atomic or protected by a pending-state lock that blocks interference.
- **AV-138** Optional token metadata/interface assumption without capability check: protocol assumes optional token metadata/interface functions (for example `decimals()`) are present and trusted, causing runtime failure or incorrect normalization on non-standard tokens. *FP:* token capability is validated at registration and missing optional interfaces are handled explicitly.
- **AV-139** Cross-chain bridge missing rate limit or circuit breaker: single bridge transaction can drain the entire locked pool with no per-transaction cap or pause mechanism. *FP:* bridge enforces per-tx and per-period caps with automatic pause on anomalous volume.
- **AV-140** Batch executor reuses stale external-state cache across legs: batched execution caches external state (allowance/balance/config) from an early leg and reuses it after intervening calls mutate that state, so even fixed call ordering can execute against invalid assumptions. *FP:* each leg refreshes external state at point-of-use or invalidates cache on every state-changing leg.
- **AV-141** Excessive message or output size causes DoS in state update: bridge `update_state` or message handler does not validate input array sizes; excessively large payloads cause out-of-gas or computation overflow. *FP:* handler enforces maximum array/message size bounds before processing.
- **AV-142** Registry-to-dispatch TOCTOU on class-hash validation: class hash is validated only at registration time, but dispatch uses a mutable registry value later without re-validating against current allowlist/snapshot. *FP:* dispatch re-validates class hash against immutable snapshot/allowlist at execution time.
- **AV-143** Callback during token transfer enables cross-protocol reentrancy: ERC721/ERC1155 safe transfer triggers receiver callback; receiving contract re-enters a different protocol function that reads stale state from the transferring contract. *FP:* cross-protocol reentrancy guard or effects-before-interaction pattern across all dependent state.
- **AV-144** Bridge message hash collision via non-canonical preimage encoding: bridge participants hash semantically identical messages with different field packing/serialization rules (felt vs bytes layout, padding, or array framing), creating hash mismatches or collisions across domains. *FP:* bridge defines one canonical preimage encoding shared by all participants and enforces it with cross-implementation test vectors.

### Math + Pricing + Economic Logic

- **AV-41** Unchecked fee bound: external/config fee parameter stored or forwarded without explicit max bound. *FP:* same-path assertion enforces max fee.
- **AV-42** Fee recipient zero-address DoS: fee recipient accepted as zero and later transfer path reverts permanently (ForgeYields-style risk). *FP:* recipient validated non-zero or transfer path handles zero safely.
- **AV-43** Rounding bias against one side: repeated rounding direction systematically favors protocol/one actor over time. *FP:* bias is documented, bounded, and validated by invariants.
- **AV-44** Felt/int boundary misuse: implicit felt<->u* conversion in accounting without range checks. *FP:* checked conversion and bounded domain assertions.
- **AV-45** Underflow guarded only by assumptions: subtraction in accounting path lacks explicit `amount <= balance` check. *FP:* invariant or guard enforces safe subtraction precondition.
- **AV-46** Oracle trust concentration: single role controls critical pricing/AUM with weak or absent second-layer limits. *FP:* independent caps, delay, quorum, or circuit-breakers constrain updates.
- **AV-47** Fee-share dilution drift: repeated fee-mint formula introduces systematic dilution beyond intended policy. *FP:* fee accrual invariants bound drift and match policy math.
- **AV-48** Boundary double-spend across period reset: hard-window reset permits max spend just before and after boundary. *FP:* sliding window or explicit boundary hardening.
- **AV-49** Zero-amount side-effect call: zero-value `approve/transfer` or policy call still changes privileges or approvals. *FP:* zero-value side-effecting selectors are blocked.
- **AV-50** Denominator stabilization hack leakage: ad-hoc `+1` denominator/sentinel math leaks value over repeated operations. *FP:* mathematically justified stabilization with bounded error tests.
- **AV-51** Multi-token spending-policy mismatch: policy accounting binds to one token while selectors can move others. *FP:* selector gate enforces same token domain as spending policy.
- **AV-52** Repricing path bypasses caps: cap checked on one update path but bypassed through alternate report/settlement path. *FP:* shared invariant enforced for every repricing entrypoint.
- **AV-53** Division-before-multiplication precision loss: integer division happens before scaling multiply in value-sensitive calculations. *FP:* multiply-then-divide with overflow-safe helper is used.
- **AV-54** WAD/RAY scale mismatch across modules: mixed precision units combined without explicit conversion. *FP:* explicit scale conversion and tests across module boundaries.
- **AV-55** Signed/unsigned tick or price cast hazards: unchecked cast between signed tick and unsigned storage value. *FP:* bounds checks and safe cast wrappers enforce domain.
- **AV-56** Slippage guard missing on liquidity ops: add/remove liquidity path lacks min-out/max-in assertions. *FP:* slippage constraints validated on all liquidity-changing routes.
- **AV-57** Comparator misuse in bounds validation: wrong comparator helper (`is_le`-style misuse seen in Cartridge audit class) accepts invalid range. *FP:* comparator semantics explicitly tested on edge values.
- **AV-58** Price bound mismatch with decimal scaling: price limit compared in different decimal domains. *FP:* both operands normalized to the same precision before comparison.
- **AV-59** Reward distribution overcounts due stale accumulator: distribution uses stale accumulator snapshot after state changed. *FP:* accumulator is refreshed before every distribution computation.
- **AV-60** Epoch settlement can be blocked by negative/overflow edge: settlement path panics on signed-edge value and blocks epoch close. *FP:* settlement branch handles signed edge and remains progress-safe.
- **AV-101** Liquidation bonus rounding inversion: liquidation reward math rounds in favor of liquidator when policy requires protocol/user protection. *FP:* rounding direction is explicit, documented, and invariant-tested.
- **AV-102** Cap check after value mint/accounting mutation: mint/accounting state is updated before cap/limit assertion executes. *FP:* cap/limit validation is enforced prior to state mutation.
- **AV-103** Interest accrual uses stale timestamp snapshot: accrual math reuses stale/cached timestamp state (or validation-phase rounded timestamp) instead of refreshing execution-phase time at accounting boundary. *FP:* accrual reads execution-phase timestamp fresh at settlement/accounting boundary and tests validation-vs-execution semantics.
- **AV-104** BPS denominator mismatch: one path uses `10_000` while another uses alternate denominator for same fee/rate domain. *FP:* denominator constant is shared and tested across all rate paths.
- **AV-105** Signed funding-rate clamp asymmetry: positive and negative funding bounds are clamped differently, creating directional leakage. *FP:* symmetric clamp policy with explicit signed-bound tests.
- **AV-106** Batch update bypasses cumulative delta guard: per-item delta checks pass while aggregate batch delta exceeds policy limit. *FP:* both per-item and cumulative deltas are enforced.
- **AV-107** Decimal normalization source mismatch: normalization uses one asset's decimals for another asset path. *FP:* each asset path resolves and validates its own decimal domain.
- **AV-108** Multiply chain overflow before safe divide: high-order multiply happens before overflow-safe divide/cast boundary. *FP:* operation ordering or helpers ensure overflow-safe intermediate math.
- **AV-109** Timestamp/block-number domain confusion: staleness/expiry check compares timestamp-based values to block-number domain. *FP:* freshness checks are domain-consistent and unit-tested.
- **AV-110** Reciprocal pricing missing zero/underflow guards: inverse price math executes without zero-floor and bound checks. *FP:* reciprocal path validates non-zero numerator/denominator and bounds.
- **AV-145** Felt252 range violation via unbounded parameter: parameter passed to cryptographic function, bit operation, or storage derivation is not bounds-checked against safe range below felt252 field prime, enabling wrap-around or invalid proof inputs. *FP:* explicit range assertion (e.g., `value < 2^64`, `bit_size < 252`) enforced before use.
- **AV-146** Modulo arithmetic edge case causing index wrap or overwrite: index derived via modulo (`value % CAPACITY`) wraps to a previously used slot, overwriting pending state (e.g., root history ring buffer). *FP:* modulo-derived index checked for collision with occupied slot, or monotonic index prevents overwrite.
- **AV-147** Collected fee balance stuck with no withdrawal mechanism: contract collects fees (transfer-in on operations) but exposes no function to withdraw accumulated fee balance, permanently locking funds. *FP:* dedicated fee withdrawal function exists with appropriate access control.
- **AV-148** Fee hook or callback always reverts blocking operation: fee collection path delegates to hook/callback that unconditionally reverts (wrong interface, missing implementation, or incorrect return value), blocking all fee-bearing operations. *FP:* fee hook is validated at registration or has a bypass/fallback for misconfigured hooks.
- **AV-149** First-depositor vault share inflation attack: first depositor mints minimal shares then donates assets directly, inflating share price so subsequent depositors receive zero shares for non-trivial deposits. *FP:* vault enforces minimum initial deposit, uses virtual shares/assets offset, or dead shares mechanism.
- **AV-150** Instruction sequence interaction causing negative balance state: specific combination of batch instructions (borrow + swap + repay) creates intermediate negative balance that either reverts unexpectedly or underflows storage. *FP:* batch executor validates intermediate invariants between instructions, or instruction ordering is constrained.
- **AV-151** Staking reward front-run by new depositor before checkpoint: reward distribution checkpoint occurs after new stake is recorded, allowing just-in-time depositor to claim share of pending rewards without contributing to the earning period. *FP:* checkpoint/accumulator updated before new stake is recorded, or time-weighted distribution prevents instantaneous dilution.
- **AV-152** Cross-market timestamp-key alias contaminates accrual state: two market/reward streams resolve to the same timestamp storage key (aliasing bug), so updates in one stream silently mutate accrual baseline of another. *FP:* each stream has a unique storage key namespace and invariant tests prove no cross-market key aliasing.
- **AV-153** Route-level slippage check omitted despite per-leg checks: each leg in a batched route satisfies local min/max checks, but no final route-level min-out/slippage assertion is enforced at settlement, allowing harmful composite paths. *FP:* protocol enforces both per-leg checks and a final route-level aggregate slippage/invariant check.
- **AV-154** Emergency withdrawal fails due to insufficient contract balance: emergency withdrawal path assumes contract holds sufficient assets, but partial withdrawals or external drains leave insufficient balance, causing revert when users need funds most. *FP:* emergency path handles partial fulfillment or has priority claim mechanism with clear accounting.
- **AV-155** Deficit handling branch reachable but debt accounting not persisted: settlement reaches the deficit/socialization path but fails to persist updated debt/socialization state before exit, causing repeated deficit handling or inconsistent recovery accounting. *FP:* deficit branch atomically persists debt/socialization state and integration tests cover consecutive negative-settlement cycles.
- **AV-156** Fee override path bypasses canonical normalization: primary setter normalizes fee inputs correctly, but admin/import/override path writes raw fee values directly, letting consumers apply mixed-scale state. *FP:* every fee write path goes through the same normalization helper, and override/import routes are tested against the canonical stored unit.

### Storage + Components + Trust Chains

- **AV-61** Constructor dead parameter: constructor accepts security-critical parameter but never uses it (ForgeYields redeem request pattern). *FP:* parameter is explicitly deprecated/compat-only and cannot affect privilege/invariants.
- **AV-62** Map-zero default confusion: zero default map entry is treated as initialized/authorized state. *FP:* explicit existence flag or non-zero sentinel separates unset from set.
- **AV-63** Stale storage after burn/revoke: post-burn/revoke mappings remain active where logic assumes deletion. *FP:* retention is intentional and read paths are gated accordingly.
- **AV-64** Cross-contract role dependency break: auth depends on mutable external contract state that can desync or be upgraded unexpectedly. *FP:* dependency immutable or validated with integrity checks.
- **AV-65** External decoder/sanitizer trust assumption: proof/policy validation relies on external decoder contract without integrity pinning. *FP:* decoder identity pinned and governed with fail-safe fallback.
- **AV-66** Immutable dependency without recovery path: critical dispatcher/dependency set once and not recoverable after failure. *FP:* immutable-by-design and explicitly covered by ops runbook/threat model.
- **AV-67** Registry hash/domain mismatch: hashed keys/signatures omit domain separator or key-length semantics. *FP:* domain-separated and length-aware hashing.
- **AV-68** Nonce monotonicity gap across transitions: nonce not incremented on unset/reset transitions, enabling stale signature replay. *FP:* nonce increments on every transition that invalidates signed intent.
- **AV-69** Event visibility gap for bulk revocation: bulk state updates omit per-item events needed by indexers. *FP:* per-item event emission or equivalent query-safe indexing contract.
- **AV-70** Upgrade audit trail loss: upgrade/change event omits prior class hash/identifier. *FP:* old and new identifiers emitted atomically.
- **AV-71** Initialization branch deadlock: constructor config can permanently disable required init branch. *FP:* constructor validates branch preconditions or exposes safe alternate init.
- **AV-72** Over-broad registry persistence: helper registry accepts arbitrary writes enabling spam/indexer DoS. *FP:* bounded writes, scoped permissions, or explicit pagination caps.
- **AV-73** Nonce domain collision across action types: same nonce key reused for distinct actions (set/unset/upgrade) enabling cross-action replay. *FP:* nonce scope includes action domain and contract context.
- **AV-74** Storage key composition collision: composite storage keys omit one discriminator and collide across logical records. *FP:* full key tuple encoded in storage address/hash derivation.
- **AV-75** Merkle/root history overwrite without uniqueness check: root history accepts repeated/invalid replacement that weakens finality assumptions. *FP:* root insertion enforces expected progression and duplicate handling rules.
- **AV-76** Proof verifier address mutability without governance delay: verifier endpoint mutable via immediate admin call, enabling sudden trust shift. *FP:* verifier changes timelocked and event-auditable.
- **AV-77** ABI variant fallback masks integration breakage: integration tries multiple ABI variants and proceeds on partial decode assumptions. *FP:* one canonical ABI and strict decode failure handling.
- **AV-78** Pending-owner/admin stale state leak: ownership transfer leaves stale pending/old authority state that still influences checks. *FP:* old pending authority cleared on transfer completion.
- **AV-79** Wrong event payload branch: event emits mismatched payload (for example claim payload in refund path), causing off-chain accounting to overcount due to stale accumulator state. *FP:* event payload strictly tied to executed branch and tested.
- **AV-80** Unbounded user-controlled iteration: loops over user-controlled array/span without bound checks can DoS execution. *FP:* explicit max bounds and fail-fast checks enforce bounded work.
- **AV-111** Component storage namespace overlap: Cairo component composition assigns overlapping component storage base/namespace, so writes in one component corrupt another. *FP:* component storage namespaces are uniquely derived at composition time and collision-tested across all embedded components.
- **AV-112** Derived storage key missing discriminator: application-level derived key generation (for example via `storage_address_from_base`) omits record/action discriminator and aliases unrelated records. *FP:* derived key includes full logical tuple (domain + action + actor + nonce/id) and is invariant-tested for alias resistance.
- **AV-113** Class-hash registry downgrade without monotonicity: registry accepts class hash replacement without version/epoch monotonicity checks. *FP:* upgrades enforce monotonic versioning and downgrade policy.
- **AV-114** Revocation leaves active authorization residue: revocation clears primary role map but leaves secondary authorization surface (cache/root/session capability) still accepted by auth checks. *FP:* revoke flow invalidates every authorization surface (role map + capability cache/root/session state) consumed by runtime checks.
- **AV-115** Queue/index wraparound overwrite: bounded index/counter wraps and overwrites pending operation state. *FP:* queue/index arithmetic enforces monotonic non-overwrite behavior.
- **AV-116** Hash preimage ambiguity in composite keys: composite key hashing mixes heterogeneous field encodings (felt packing/spans/byte arrays) without canonical boundaries, creating preimage aliasing. *FP:* composite keys use canonical encoding with explicit domain/version separators and deterministic field boundaries.
- **AV-117** Signature domain omits chain or contract binding: signature domain binds action/nonce but omits Starknet chain-id or verifier/account contract binding, enabling cross-deployment replay. *FP:* signature domain explicitly binds chain-id, verifying contract/account context, action, and nonce.
- **AV-118** Upgrade migration not idempotent: migration step can be re-run and mutates state inconsistently on repeat execution. *FP:* migration guarded by version bit and repeat-safe behavior.
- **AV-119** Trusted relayer set mutation lacks auditability: relayer/trusted-actor mutation occurs without event trail or immutable checkpoint. *FP:* mutation emits complete audit event and is recoverable/observable.
- **AV-120** Cross-module invariant gap after dependency swap: dependency swap updates pointer successfully but does not revalidate post-swap invariants across tightly-coupled modules, leaving inconsistent cross-module state. *FP:* swap path performs explicit post-swap invariant revalidation across coupled modules and aborts on inconsistency.
- **AV-157** Storage key collision via duplicate token or pool identifiers: adding a pool/token with the same identifier (address, denomination) overwrites the existing mapping entry silently, corrupting prior state. *FP:* registration path checks for existing entry and reverts or uses unique composite key.
- **AV-158** Dynamic felt252 array storage with incorrect size tracking: `StoreFelt252Array` or manual array storage writes elements but stores incorrect length, causing reads to return truncated or out-of-bounds data. *FP:* array length updated atomically with element writes and validated on read.
- **AV-159** ByteArray/felt encoding accepts malformed input without validation: `ByteArray` or raw felt spans are accepted from external input without validating canonical encoding (non-canonical `bytes31` padding, declared-length mismatch, oversized chunk values), causing downstream decode failures. *FP:* input validation at the boundary rejects malformed ByteArray/felt encoding before storage or processing.
- **AV-160** Array element removal leaves stale reference or index gap: removing element from storage array (swap-and-pop or shift) does not update all secondary indices/references, leaving stale pointers (e.g., lock ID array after unlock). *FP:* removal atomically updates all dependent indices and validates consistency.
- **AV-161** State counter not updated in secondary function path: primary function updates a state counter (e.g., `notesCount`, `totalDeposits`) but secondary function that also modifies the underlying data skips the counter update. *FP:* all mutation paths update the shared counter, enforced by shared internal helper.
- **AV-162** Fiat-Shamir challenge omits public input binding in proof composition: challenge derivation in zero-knowledge proof composition omits critical public inputs (bit proofs, commitments, statement components), allowing proof forgery via input substitution. *FP:* challenge hash includes all public inputs, statement components, and proof-stream commitments per protocol specification.
- **AV-163** Signature replay via omitted nonce or commitment binding: signed payload (encrypted notes, transfer authorization) does not bind to a unique nonce or commitment, allowing the same signature to authorize multiple distinct operations. *FP:* signature domain includes monotonic nonce, unique commitment hash, and operation-specific context.
- **AV-164** Multisig or aggregation ISM allows duplicate signatures: multi-signature verification (ISM, multisig wallet) counts duplicate signatures from the same signer toward the threshold, allowing single signer to reach quorum. *FP:* verification deduplicates signers before counting, or enforces strictly ascending signer order.
- **AV-165** Repeated state update overwrites pending timestamp or deadline: calling the same state-update function again (e.g., `start_cancellation`, `start_withdrawal`) overwrites the original timestamp, resetting or extending the waiting period. *FP:* repeated call blocked while pending, or first timestamp is immutable until completion/expiry.
- **AV-166** Non-reverting failure path lacks durable failure signal: operation records a non-reverting failure state (for example status flag/partial retry state) but emits no event or durable queryable marker, leaving off-chain systems blind. *FP:* non-reverting terminal outcomes emit explicit failure events or write a queryable failure-state record.
- **AV-167** Cross-function state inconsistency via unsynchronized counters: two functions read/write the same logical counter (e.g., `notesCount`) but one uses stale or differently-scoped state, producing inconsistent results across queries. *FP:* shared counter accessed through single internal getter/setter with consistent scope.
- **AV-168** Proof or commitment reuse across distinct protocol actions: zero-knowledge proof, encrypted note, or commitment valid for one action (deposit) can be replayed for a different action (withdrawal) because the action type is not bound in the proof domain. *FP:* proof/commitment domain explicitly includes action discriminator preventing cross-action replay.
- **AV-169** ContractAddress/felt252 narrowing mismatch for 32-byte external identifiers: cross-chain or interop path receives a 32-byte identifier and narrows it into `ContractAddress` (`[0, 2**251)`) or `felt252` (`< P`, where `P = 2**251 + 17*2**192 + 1`) via unchecked truncation/modular reduction, causing collisions or invalid mappings. *FP:* external identifiers remain in explicit 256-bit storage (`u256`/byte array) and boundary conversions into `ContractAddress`/`felt252` are explicit, range-checked, and fail-fast.
- **AV-170** Aggregation element-count truncation via unsafe narrow/wrapping conversion: aggregation module narrows validator/message count into small integer (`u8`) via wrapping/unchecked conversion; counts above boundary are truncated and quorum checks mis-evaluate. *FP:* count stays in sufficiently large type (`u32`/`u64`) or narrowing is guarded by explicit upper-bound assertion with fail-fast revert.
## Lens B additions

Cairo items for Lens B (`engine/mindsets.md`):

- **[Edge Case]** What happens with amount=0, amount=1 (smallest unit), amount=`u256` max / `u128` max, a `felt252` value near P, or the first/last depositor?
- **Payment destination correctness (Module O)**: Is `self.ownable.owner()` (contract owner) vs `erc721.owner_of(token_id)` (token holder) vs `get_caller_address()` the right recipient? Double payout? Conditional payment with unconditional cost? A zero fee recipient that makes payouts revert (FEES-RECIPIENT-ZERO-DOS)?
- Value moves only through token contracts (STRK and ETH are ERC20s): there is no native `msg.value`-style payment to double-count, but every ERC20 dispatcher call is an external call (Lens C).

## Lens C additions

Cairo items for Lens C (`engine/mindsets.md`):

- Reentrancy via callbacks: ERC721/ERC1155 `safe_transfer_from` receivers (`on_erc721_received`, `on_erc1155_received`), component hooks, caller-supplied contracts, `library_call` targets (REENT-01, LIBC-01)
- Failure semantics: a failing dispatcher call reverts the whole transaction; safe-dispatcher `Err` paths and uncatchable failures (DISP-01)
- L1↔L2 boundary: `#[l1_handler]` `from_address` checks, payload encoding, stuck messages (L1H-01, L1H-02, MSG-01 to MSG-03)
- Version compatibility: Cairo version and Scarb `edition` (edition `2025_12` changes snapshot member access), OpenZeppelin Contracts for Cairo version (embedded selectors differ across versions; CVE-2024-45304 `renounce_ownership` before v0.16.0), Starknet version (v0.14.0: ~6s blocks, only V3 transactions, internal calls to `__execute__` revert)

## Lens D additions

Cairo items for Lens D (`engine/mindsets.md`):

- **[Spec Auditor]** Does this implementation match its SNIP exactly? SNIP-2 (ERC20 on Starknet), SNIP-12 typed data (domain fields, revision, type strings character by character), SNIP-9 outside execution (nonce, caller, time bounds), SRC5 interface IDs, SRC6 accounts (`is_valid_signature` returns `starknet::VALIDATED`).
- Type cast safety: every `try_into()` across `felt252` ↔ `u*`/`i*` ↔ `ContractAddress` ↔ `EthAddress` — can the source exceed the target, and what happens on `None` (panic or silent default)? Every manual `u256 { low, high }` (FELT-03, INT-03, U256-01).
- `felt252` arithmetic and division in value math (FELT-01, FELT-02); bit-packing width (FELT-04).
- SNIP-12 type hash verification: the hardcoded type hash matches the type string, character by character.
- Standard compliance (ERC20, ERC721, ERC1155, ERC4626 components and SNIPs): actual vs spec, including camelCase twins.

## Detector modules (Cairo)

Cairo items for the detector (`engine/phases/detect.md`).

### Module A: Untrusted Recipient Analysis

For every ERC20 dispatcher `transfer`/`transfer_from` and every ERC721/ERC1155 `safe_transfer_from` to an address that is NOT `get_caller_address()` or a known protocol address. Only safe transfers call the recipient (`on_erc721_received`/`on_erc1155_received`); a plain ERC20 transfer cannot be blocked by the recipient, but a zero or invalid recipient makes OZ tokens panic, which reverts the whole transaction.

### Module B: Type Cast Safety
Check EVERY narrowing conversion: `try_into()` to `u8`…`u128`, `u256 → felt252`, `felt252 → ContractAddress`, signed ↔ unsigned. Cairo never truncates silently on `try_into`; it returns `Option`. For each:
- Is the `None` case `unwrap()`/`expect()` (panic → DoS: who can trigger it, on whose path?) or replaced by a default (`unwrap_or(0)`: silent wrong value)?
- Values in `felt252` that should be bounded integers: wrap modulo P with no panic (FELT-01).
- Manual `u256 { low, high }` construction and limb order (U256-01); bit-packing within 251 bits (FELT-04).

### Module F: Token Compatibility
- `transfer`/`transfer_from` return values checked? Token entry-point casing (`transfer_from` vs `transferFrom`)?
- `decimals()` assumed 18 or assumed present (USDC on Starknet has 6; AV-138)?
- Zero-value transfers and approvals: do they still change privileges or approvals (AV-49)?
- Received amount vs nominal amount for any listed token with transfer fees (AV-34).

### Module G: Factory/Deployment Patterns
- `deploy_syscall` with `deploy_from_zero: true` or a caller-chosen salt: can someone deploy the address first (DEPLOY-01)?
- Separate deploy and `initialize` calls: can someone else initialize (UNPROTECTED-INITIALIZER)?
- Factory-deployed children that inherit the factory as admin (AV-127); multi-transaction activation (AV-137).

### Module O: Payment/Distribution Flow Tracing

1. **Trace each payment**: For every ERC20 dispatcher `transfer`/`transfer_from`, ERC721 `transfer_from`/`safe_transfer_from` and L2→L1 withdrawal message — WHO is the actual recipient? Is it `self.ownable.owner()` (contract owner), `owner_of(token_id)` (token holder), `get_caller_address()`, or a configured address? Verify the recipient is semantically correct.

### Question additions

- **Q3.7 [ACCESS CONTROL EXHAUSTIVE CHECK]**: List EVERY entry point that takes `ref self: ContractState` — `#[external(v0)]` functions, functions in `#[abi(embed_v0)]` / `#[abi(per_item)]` impls (including embedded component impls) and `#[l1_handler]` functions. For each: WHO can call it? Is that the right set of callers? Look for `assert_only_owner`, `assert_only_role`, `get_caller_address()` comparisons and `from_address` checks. Especially check: sync/checkpoint functions, functions that should be admin-only, and functions that should check the caller against a parameter.
- **Q6.3**: Can external calls FAIL SILENTLY? (ERC20 `transfer` returning `false`; a safe-dispatcher `Err` that is logged and ignored; a selector fallback retry)

### Rules

- **Track OpenZeppelin Contracts for Cairo (`openzeppelin_*` packages) and Alexandria usage.** Don't flag standard component implementations as custom bugs; do check how they are embedded and wrapped (COMP-02, UPG-01).

## Recon additions

Cairo items for recon (`engine/phases/recon.md`).

### Analyzer command (Step 2b)

Caracal prints text, so its output is wrapped as JSON for the pack's analyzer script
(`recon/caracal-summary.py`, `pack.json` `analyzers[].run`). `A` and `<root>` are absolute paths;
`<root>` is the Scarb project root.

```bash
mkdir -p A/analyzers && rm -f A/analyzers/caracal.json
caracal detect --target <root> 2>&1 | python3 -c 'import json,sys; json.dump({"output": sys.stdin.read()}, sys.stdout)' > A/analyzers/caracal.json
python3 CORE/chains/cairo/recon/caracal-summary.py A/analyzers/caracal.json A/analyzers/caracal.md
```

- The pipeline's exit code is Python's, not Caracal's. Judge success by the wrapped output: if it
  holds a compile or usage error rather than detector results, treat the pre-scan as failed
  ("caracal pre-scan: SKIPPED (failed)") and delete both files.
- Caracal compiles the project itself and lags new Cairo releases (cairo-auditor notes v0.2.x
  targets Cairo ≤ 2.5); failure on a modern project is expected and is not a ChainSec error.
- **IMPORTANT**: Many Caracal detectors produce informational/low noise (dead code, unused arguments, benign reentrancy, event-only reentrancy). Only extract HIGH and MEDIUM impact blocks for the summary.

### Project identification (Step 1)

- Manifests: `Scarb.toml` (`[dependencies] starknet`, `edition`, `cairo-version`), `Scarb.lock`, `snfoundry.toml`
- **Key dependencies**: OpenZeppelin Contracts for Cairo (`openzeppelin_*`), Alexandria, Pragma (oracle), Ekubo, Vesu, AVNU, StarkGate bridges, LayerZero / Hyperlane endpoints

### Scope expansion (Step 3)

- OpenZeppelin Contracts for Cairo and Alexandria are excluded (`pack.json` `novelty_allowlist`) — only project-specific components and libraries.
- A project component embedded through `component!` is in scope and clusters with each contract that embeds it (`recon/clustering.md`).
- `novel_code_bonus` — `# +15 if NOT from OpenZeppelin Contracts for Cairo / Alexandria`

### Risk-score counters (Step 3)

Where (counted per file by `recon/extract.py`):
- **external_calls**: syscalls (`call_contract_syscall`, `library_call_syscall`, `replace_class_syscall`, `deploy_syscall`, `send_message_to_l1_syscall`, `storage_write_syscall`) plus `*Dispatcher { ... }` constructions, inside functions
- **state_writers**: entry points taking `ref self` that contain a `self.<x>...write(` storage write
- **syscalls**: the syscall subset of external_calls
- **l1_handlers**: `#[l1_handler]` functions
- **felt_arith**: lines mixing `felt252` with `+ - * /` arithmetic
- **novel_code_bonus**: +15 if the file is not matched by `pack.json` `novelty_allowlist`
- **value_handling_bonus**: +10 if the file calls ERC20 `transfer` / `transfer_from`
- Cairo has no `payable`, assembly or `unchecked` blocks; those Solidity terms score zero.

### Untrusted Recipient Map (Step 3c)

List every token transfer where the recipient is NOT `get_caller_address()` and NOT a hardcoded protocol address:
- Safe-transfer receivers (`on_erc721_received`, `on_erc1155_received`, discovered via SRC5)
- Caller-supplied callback, reward or hook contracts (AV-24, AV-28) and lock/flash callbacks
- L1 recipients encoded in `send_message_to_l1_syscall` payloads

### Attacker mindset (Step 4)

3. **What's novel?** What code was written specifically for this protocol (not OpenZeppelin Contracts for Cairo / Alexandria components)? Novel code = novel bugs. Flag custom components, custom accounts, custom `Store` impls and hand-rolled nonce/signature logic.

### Integration checklists (Step 5)

**Pragma Integration**: price non-zero, `last_updated_timestamp` freshness (recalibrated for ~6s blocks), `num_sources_aggregated` floor, decimals normalized per asset.

**Ekubo Integration**: the lock/`locked` callback asserts the caller is the Ekubo core; deltas settled before the callback returns; slippage bounds on swaps and position changes.

**StarkGate / L1 bridge Integration**: `#[l1_handler]` `from_address` pinned to the L1 bridge; u256 amounts decoded low/high; withdrawal limits and a stuck-deposit recovery path.

## State audit additions

Cairo original of the Phase 4 operation-ordering example in `engine/phases/state.md`:

```
fn withdraw(ref self: ContractState, amount: u256):
  1. READ  self.shares.entry(caller).read()           ← reads coupled state
  2. WRITE self.shares.entry(caller).write(s - x)     ← updates primary
  3. CALL  IERC20Dispatcher { .. }.transfer(..)       ← EXTERNAL CALL
  4. WRITE self.total_shares.write(t - x)             ← updates coupled AFTER external call!
```

## Security strengths examples

Cairo examples for the Security Strengths section of `engine/report-template.md`:

- **Access control model**: Which components (OZ `OwnableComponent` two-step, `AccessControlComponent`, `AccessControlDefaultAdminRulesComponent`)? Consistent across all `ref self` entry points and embedded impls?
- **Reentrancy protection**: CEI before dispatcher calls? `ReentrancyGuardComponent` `start()`/`end()` on every path that calls out?
- **Arithmetic safety**: Value math in `u128`/`u256` (panicking) rather than `felt252`? Narrowing via handled `try_into`?
- **Battle-tested dependencies**: Which OpenZeppelin Contracts for Cairo version? Current?
- **Upgrade safety**: `UpgradeableComponent` behind auth and a delay? Non-zero class hash? Storage names stable across versions?
- **Cross-domain safety**: `#[l1_handler]` `from_address` checks; SNIP-12 signatures with chain id and `NoncesComponent` nonces.

Example bullet: `- **[Category]**: [Specific observation with contract/file names — e.g., "All 6 state-mutating entry points in vault.cairo call assert_only_role before any storage write"]`
