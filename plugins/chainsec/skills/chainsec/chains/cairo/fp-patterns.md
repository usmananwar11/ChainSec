# Cairo false-positive patterns and gate overrides

## FP patterns

### FP-3: OpenZeppelin Contracts for Cairo Standard Protection
The finding reports a vulnerability in code that embeds battle-tested components:
- `ERC20Component` / `ERC721Component` / `ERC1155Component` with `u256` checked arithmetic and zero-address checks
- `OwnableComponent` (`assert_only_owner`, two-step transfer via the two-step impl) and `AccessControlComponent` / `AccessControlDefaultAdminRulesComponent`
- `UpgradeableComponent`, whose internal `upgrade` rejects a zero class hash and emits `Upgraded`
- `ReentrancyGuardComponent`, `PausableComponent`, `InitializableComponent` (one-shot `initialize()`), `NoncesComponent` (`use_checked_nonce`)
- `AccountComponent`, whose `__execute__` requires a zero caller and whose `__validate__` checks the signature over the transaction hash
- `ERC4626Component` with its decimals offset against share inflation

**Check**: Verify the exact version in `Scarb.toml` / `Scarb.lock` (e.g. CVE-2024-45304, `renounce_ownership` before v0.16.0). Check how the component is wired: internal-only functions (`UpgradeableComponent::upgrade`, `InternalImpl`) are only as safe as the contract's wrapper; check overridden hooks and which impls are embedded with `#[abi(embed_v0)]`. Protection from a component the contract does not actually call is no protection.

### FP-7: Cairo Integer Arithmetic Safety
The finding claims overflow/underflow but:
- The values are `u8`…`u128`, `u256` or `i8`…`i128`, which panic on overflow and underflow
- The overflow would revert the transaction, not silently wrap
- This is a DoS (revert), not value extraction → lower severity (unless the engine's DoS exception applies: an unprivileged attacker permanently blocks a core lifecycle function)

**Check**: Is the arithmetic on `felt252`, or through `wrapping_*`, `overflowing_*`, `saturating_*` or `u128_overflowing_add`? Those do not panic.

**IMPORTANT EXCEPTION**: `felt252` arithmetic wraps modulo the field prime P and has NO overflow panic, and `felt252` division is field division, not floor division. Do NOT dismiss felt252 findings with this FP pattern. Also not covered: narrowing `try_into()` whose `None` is replaced by a default (silent wrong value), manual `u256 { low, high }` construction, and bit-packing into a `felt252` beyond 251 bits. These corrupt state silently.

### FP-8: Read-Only / View Function Confusion
The finding claims state manipulation via a view function:
- A function taking `self: @ContractState` cannot write this contract's storage through `self` (compiler-enforced)
- The "vulnerability" only affects off-chain reads (`starknet_call`)

**Check**: Starknet has no static call. A `self: @ContractState` function can still call `storage_write_syscall` directly, make dispatcher or `library_call` calls into state-changing functions, or emit through another contract — those DO change state. Only kill when the function makes none of these calls. Also: does it matter if the value is temporarily wrong for an on-chain consumer that reads it mid-transaction?

### FP-9: Test/Script/Interface-Only (Cairo test files)
Cairo items of FP-9 (`engine/phases/verify.md`):
- Test files and folders: `tests/`, `test/`, `src/tests/`, `*_test.cairo`, `test_*.cairo`, `tests.cairo`
- Test-only code inside source files: `#[cfg(test)]` modules and `#[test]` functions
- Mocks (`mock/`, `mocks/`) and `sncast` deployment scripts
- Interface-only modules (`#[starknet::interface]` traits with no implementation)

## Gate overrides and examples

Cairo examples for the gates in `engine/kill-gates.md`, keyed by gate letter. Several cairo-auditor
vulnerability classes (`patterns/`) are admin-side hygiene; these notes say when they survive.

### Gate A — Generic Best Practice
- Kill gate: "check ERC20 `transfer` return value" without naming a protocol token that returns `false`, "use a two-step admin transfer" (UNSAFE-ADMIN-TRANSFER as hygiene), "missing event" (AV-40, AV-69, AV-70 without a concrete off-chain consumer harmed), "migrate `LegacyMap` to `Map`", "use OZ components instead of hand-rolled code", "add a non-zero check on `get_caller_address()`" (dead code: CALLER-02), randomness from `get_block_timestamp`/block number without a concrete payout an attacker controls.
- Detection pre-filter: Do NOT report: ERC20 return-value wrappers generically, two-step ownership, missing events, unused constructor parameters with no security effect (CONSTRUCTOR-DEAD-PARAM), weak on-chain randomness.

### Gate C — Design Is Intentional
- Detection pre-filter: patterns from reference implementations include OpenZeppelin Contracts for Cairo, Alexandria, StarkGate, Ekubo core and the Argent/Braavos account contracts.
- Each pattern's "False-positive caveats" section lists the evidence that makes it intentional (documented immutable admin, documented queue semantics, documented zero-recipient burn sink).

### Gate E — Admin Trust Boundary
- Kill: IRREVOCABLE-ADMIN, MISSING-FEE-BOUNDS, ONE-SHOT-REGISTRATION, CRITICAL-ADDRESS-INIT-WITHOUT-NONZERO-GUARD, UPGRADE-CLASS-HASH-WITHOUT-NONZERO-GUARD and UNSAFE-ADMIN-TRANSFER when the only path is a trusted admin or deployer supplying a bad value.
- Survives under the gate's exception: IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK when `replace_class_syscall` (or an equivalent `library_call` path, AV-85) is reachable with no delay and users cannot exit before it takes effect — an irreversible destructive action (Medium at most unless the role is broad or reachable by non-admins, AV-9).
- Never killed by this gate: the same classes when an UNPRIVILEGED caller reaches the path (NO-ACCESS-CONTROL-MUTATION, UNPROTECTED-INITIALIZER, COMMENTED-OUT-ACCESS-CONTROL, UNEXPECTED-ACCESS-CONTROL, `#[l1_handler]` without a `from_address` check, session-key escalation in AA-SELF-CALL-SESSION).

### Gate B / Gate D — Theoretical or speculative
- Kill: attacks that need a compromised prover or sequencer, sequencer–prover divergence, or reorgs, with no realistic trigger path.
- Kill: `felt252` overflow on values that are provably bounded far below P (e.g. a counter incremented by one per transaction) — but state the bound.

## Masking code examples

Cairo masking patterns for the state auditor Phase 7 (`engine/phases/state.md`):

- **Swallowed safe-dispatcher errors**: `match dispatcher.call(..) { Result::Err(_) => { /* log, continue */ } }`. A call that was expected to succeed is failing; what invariant does the continuation assume (AV-32, AV-94, AV-100)?
- **`try_into` with a default**: `x.try_into().unwrap_or(0)` or a `None => 0` arm silences an out-of-range value. Why can the value exceed the target type?
- **Saturating arithmetic**: `saturating_sub`/`saturating_add` clamps a divergence that panicking `u*` arithmetic would have exposed. Checked arithmetic prevents the revert but doesn't fix why the values diverged.
- **Selector fallback retry**: retrying `call_contract_syscall` with another selector casing after `is_err()` hides an integration bug (SYSCALL-SELECTOR-FALLBACK-ASSUMPTION).
