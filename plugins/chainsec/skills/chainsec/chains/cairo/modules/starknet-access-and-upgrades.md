# Starknet Access Control & Upgrades Module

> **Trigger**: Always active for Cairo — every contract has entry points, and most are upgradeable through `replace_class_syscall`
> **Inject into**: Lens A (Access/State/Governance)
> **Priority**: HIGH — an unguarded entry point or upgrade is full contract takeover
> <!-- Ported from keep-starknet-strange cairo-auditor (MIT): attack vectors 1-20, 81-90, 121-132 and vuln-db classes; see ATTRIBUTION.md -->

## 1. Entry-Point Inventory

Build the table from `A/facts.json` `entry_points`, then read each function:

| Entry point | Source (`#[external(v0)]` / embedded impl / component / `#[l1_handler]` / constructor) | `ref self`? | Guard | Writes |
|---|---|---|---|---|

- Every function in an `#[abi(embed_v0)]` impl is public, including component impls (COMP-02 in heuristics.md). Check the embedded set, not only the contract's own functions.
- `self: @ContractState` functions cannot write storage through `self`, but can still call out (fp-patterns.md, FP-8).
- External wrapper → internal helper that mutates privileged state with the guard on neither (AV-8, AV-90).
- Guards: `assert_only_owner`, `assert_only_role`, `get_caller_address()` comparison. Check the comparison targets the right storage slot (AV-7) and uses the caller, not `get_tx_info().account_contract_address` (AV-87).
- Commented-out guards (COMMENTED-OUT-ACCESS-CONTROL) and OR-combined actor checks (UNEXPECTED-ACCESS-CONTROL).
- Apply GUARD-01 (heuristics.md): siblings missing a guard, pause gates bypassed through alias or camelCase routes (AV-19, AV-89).

## 2. Upgrade Path

For each path that reaches `replace_class_syscall`, `UpgradeableComponent` `upgrade`, or a `library_call` with a stored class hash:

| Route | Caller gate | Non-zero hash | Delay / timelock | Event (old + new hash) |
|---|---|---|---|---|

- `UpgradeableComponent::upgrade` is internal: the contract's wrapper is the only access control (UPG-01).
- Every route shares one gate and one delay (AV-13); the delay itself cannot be set to zero immediately (AV-82); a pending hash is not silently overwritten (AV-84); cancellation needs at least the scheduling privilege (AV-83).
- Broad roles holding upgrade rights (AV-9); upgrade auth read from a mutable external contract (AV-15, AV-64).
- The new class takes effect for later calls; upgrade and configure in separate transactions leave a window on stale config (AV-125).
- Patterns: IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK, UPGRADE-CLASS-HASH-WITHOUT-NONZERO-GUARD (read the Gate E notes in fp-patterns.md before reporting either).

## 3. Storage Compatibility Across Classes

Starknet has no proxy: storage stays at the contract address and each variable's address comes from its name.

- Unsafe across versions: removing, renaming or retyping a variable, changing a `Map` key type, renaming a component substorage, changing a custom `Store` layout. Safe: adding variables or substorages.
- Migration/initializer after upgrade: versioned, idempotent, not replayable (AV-10, AV-86, AV-118); permission state carried forward (AV-128).
- Any declared class is accepted unless checked: interface/version compatibility (AV-130), downgrade (AV-113).

## 4. Initialization

- Constructor init is atomic with deployment. Post-deploy `initialize`/`initializer` entry points need caller auth and a one-shot flag (UNPROTECTED-INITIALIZER, AV-16); OZ `InitializableComponent::initialize()` is used in exactly one function.
- Embedded components initialized in the constructor (`ownable.initializer(owner)`, `access_control.initializer()` + role grants) — a missed call leaves the owner zero or no admin (AV-121).
- Critical addresses non-zero (CRITICAL-ADDRESS-INIT-WITHOUT-NONZERO-GUARD, AV-88); every constructor branch applies the same checks (AV-17, AV-71); no dead security parameters (CONSTRUCTOR-DEAD-PARAM).

## 5. Role Lifecycle

- Rotation and revocation reachable (IRREVOCABLE-ADMIN, AV-4, AV-18); a sole admin cannot renounce into lockout (AV-129).
- Ownable and AccessControl mixed with paths checking different models (AV-11, AV-81).
- `set_role_admin` cannot make a role its own admin or hand it to a user-controlled role (AV-14).
- Admin transfer validates the target; pending state cleared on completion (UNSAFE-ADMIN-TRANSFER, AV-20, AV-78, AV-122).
- Revocation clears every authorization surface — role map, session/capability caches, roots (AV-114).
- Multisig thresholds have a floor (AV-126).

## 6. Emergency Controls

- `pause`/`unpause`/`emergency_*` actually privileged (AV-12).
- Liquidation and risk functions are NOT blocked by `assert_not_paused()` (C4 Starknet Perpetual L-05).
- Forced shutdown override checked before inferred mode (SHUTDOWN-OVERRIDE-PRECEDENCE, AV-123) and propagated to extensions (AV-124).
- Auth/policy checks run before any state write on non-reverting error paths (AV-132).
