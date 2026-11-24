# Cairo vulnerability patterns

The 28 vulnerability classes of keep-starknet-strange's `cairo-auditor` vulnerability DB, ported
with their IDs unchanged (credit: [ATTRIBUTION.md](../ATTRIBUTION.md)). One file per class:
description, vulnerable pattern, secure pattern, detection cues, false-positive caveats and the
minimum tests that prove or disprove it.

How the engine uses them:

- **Detection**: a pattern is a lead, not a finding. A candidate still needs a concrete attack path
  (caller → reachable entry point → state change → impact) and goes through `engine/kill-gates.md`.
- **Verification**: the "False-positive caveats" section lists the evidence that supports a Gate C
  or FP-10 kill; the "Minimum tests" section is the starting list for a PoC or regression test.
- **Cross-reference**: each header names the related attack vectors (`AV-<n>`) in
  [heuristics.md](../heuristics.md), section "Extended heuristics", and the pack module, if any.
- **Naming**: findings keep the pack's `CAIRO-<n>` ID; a finding that matches a class cites the
  class ID (for example in its `category`) so it can be traced back.

| ID | Lens | Category | One-line description |
|---|---|---|---|
| [AA-SELF-CALL-SESSION](AA-SELF-CALL-SESSION.md) | A + D | Account abstraction | Session key escalates privilege by calling back into its own account |
| [CEI-VIOLATION-ERC1155](CEI-VIOLATION-ERC1155.md) | C | Reentrancy | ERC1155 `safe_transfer_from` before critical state updates |
| [COMMENTED-OUT-ACCESS-CONTROL](COMMENTED-OUT-ACCESS-CONTROL.md) | A | Access control | Access checks commented out while the mutation path stays live |
| [CONSTRUCTOR-DEAD-PARAM](CONSTRUCTOR-DEAD-PARAM.md) | A | Initialization | Constructor parameter never used in initialization |
| [CRITICAL-ADDRESS-INIT-WITHOUT-NONZERO-GUARD](CRITICAL-ADDRESS-INIT-WITHOUT-NONZERO-GUARD.md) | A | Initialization | Critical `ContractAddress` stored in constructor without a non-zero check |
| [FEES-RECIPIENT-ZERO-DOS](FEES-RECIPIENT-ZERO-DOS.md) | B | Fees | Zero fee recipient later makes payout paths revert |
| [IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK](IMMEDIATE-UPGRADE-WITHOUT-TIMELOCK.md) | A | Upgrades | Class-hash upgrade in one privileged call, no delay |
| [INCORRECT-LIST-REMOVAL](INCORRECT-LIST-REMOVAL.md) | D | Storage | Removal mutates the wrong element and desyncs index mappings |
| [IRREVOCABLE-ADMIN](IRREVOCABLE-ADMIN.md) | A | Access control | Admin seeded with no rotation, transfer or revocation path |
| [MISSING-FEE-BOUNDS](MISSING-FEE-BOUNDS.md) | B | Fees | Privileged fee setter accepts unbounded values |
| [NO-ACCESS-CONTROL-MUTATION](NO-ACCESS-CONTROL-MUTATION.md) | A | Access control | Privileged/config mutation callable by anyone |
| [ONE-SHOT-REGISTRATION](ONE-SHOT-REGISTRATION.md) | A | Dependencies | Write-once critical dependency with no recovery path |
| [OVERLY-RESTRICTIVE-VALIDATION](OVERLY-RESTRICTIVE-VALIDATION.md) | D | Validation | Strict bounds reject legitimate configurations |
| [PRECISION-LOSS](PRECISION-LOSS.md) | B | Math | Low scale factor truncates percentage/vesting math |
| [SHUTDOWN-OVERRIDE-PRECEDENCE](SHUTDOWN-OVERRIDE-PRECEDENCE.md) | A | Emergency controls | Inferred mode returns before the admin override is checked |
| [SILENT-NO-OP](SILENT-NO-OP.md) | D | State updates | Update branch does nothing on the existing-key path |
| [STALE-SNAPSHOT-READ](STALE-SNAPSHOT-READ.md) | D | State updates | Reads through an `@self` snapshot while writing live state in the same loop |
| [STALE-STATE-WRITE](STALE-STATE-WRITE.md) | B | State updates | Field updated, then overwritten with a stale pre-update value |
| [SYSCALL-SELECTOR-FALLBACK-ASSUMPTION](SYSCALL-SELECTOR-FALLBACK-ASSUMPTION.md) | C | External calls | Failed `call_contract_syscall` retried with another selector casing |
| [UNBOUNDED-LOOP](UNBOUNDED-LOOP.md) | D | DoS | Iteration over unbounded state with no pagination |
| [UNCHECKED-FEE-BOUND](UNCHECKED-FEE-BOUND.md) | B | Fees | Caller-supplied fee forwarded to deploy/storage without bounds |
| [UNEXPECTED-ACCESS-CONTROL](UNEXPECTED-ACCESS-CONTROL.md) | A | Access control | Sensitive action callable by an unintended actor class |
| [UNPROTECTED-INITIALIZER](UNPROTECTED-INITIALIZER.md) | A | Initialization | External initializer with no caller authorization |
| [UNSAFE-ADMIN-TRANSFER](UNSAFE-ADMIN-TRANSFER.md) | A | Access control | Single-step, unvalidated admin transfer |
| [UNSAFE-TYPE-CONVERSION](UNSAFE-TYPE-CONVERSION.md) | D | Conversions | Narrowing `try_into().expect()` panics or truncates in a critical path |
| [UNVALIDATED-ORACLE-PRICES](UNVALIDATED-ORACLE-PRICES.md) | B | Oracles | Price updates bypass signature/median/deviation validation |
| [UPGRADE-CLASS-HASH-WITHOUT-NONZERO-GUARD](UPGRADE-CLASS-HASH-WITHOUT-NONZERO-GUARD.md) | A | Upgrades | Upgrade accepts a zero `new_class_hash` |
| [WRONG-PARAMETER-USAGE](WRONG-PARAMETER-USAGE.md) | B | Parameters | Distinct fields (min/max) filled from the same input |
