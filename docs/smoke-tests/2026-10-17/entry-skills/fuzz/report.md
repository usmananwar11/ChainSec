# Fuzz Report — Vault

Framework: Foundry invariant (forge 1.7.1), 256 runs x 500 depth (128,000 calls per invariant), handler with 3 actors.
Test file: [`VaultInvariant.t.sol`](tests/VaultInvariant.t.sol). The archived run's generated `.audit/solidity/fuzz/tests/` directory is not included in this repository; the test file is preserved here. The fixture source is [`tests/fixtures/solidity-basic/src/Vault.sol`](../../../../../tests/fixtures/solidity-basic/src/Vault.sol).

To rerun from the repository root, use the fixture as the Foundry project and point `FOUNDRY_TEST` at the archived test directory:
`cd tests/fixtures/solidity-basic && FOUNDRY_TEST=../../../docs/smoke-tests/2026-10-17/entry-skills/fuzz/tests forge test --match-path '*/VaultInvariant.t.sol' --fuzz-runs 1000 -vv`

## Summary
| Result | Count | IDs |
|---|---|---|
| HOLDS | 5 | INV-001, INV-002, INV-004, INV-006, INV-010 |
| VIOLATED | 3 | INV-003, INV-005, INV-009 |
| INCONCLUSIVE (not tested) | 4 | INV-007, INV-008, INV-011, INV-012 |

## Violated invariants

### INV-005 — ETH balance covers ETH credits (high)
Counterexample (shrunk to 2 calls): `depositEth(...)` by an actor, then `sweep(to)` by any other actor.
Impact: any caller drains all native balance to an address of their choice; depositors' ETH credits become unbacked. Matches the planted bug and the [recon's attack-surface item 1](../../../2026-10-16/opencode/audit/solidity/recon.md). Root cause: `Vault.sweep` has no access control in the [fixture source](../../../../../tests/fixtures/solidity-basic/src/Vault.sol).

### INV-003 — ledger is backed by assets held (high)
Same 2-call counterexample (`depositEth` then `sweep`). Sum of `balances` exceeds token plus native assets held. Same root cause as INV-005.

### INV-009 — every ledger balance is redeemable (high)
Counterexample (1 call, no sweep): `depositEth(5, 1.5e24)`. The actor is credited 1.5e24 in `balances`, but the vault holds no tokens, and `withdraw` pays out in tokens only. There is no ETH withdrawal path other than the unauthenticated `sweep`. Impact: ETH deposits are unredeemable by their owner, and the shared ledger lets ETH credit be redeemed against other users' tokens (recon item 2). Root cause: `depositEth` credits the same `balances` ledger as ERC20 `deposit` while `withdraw` only pays tokens, as shown in the [fixture source](../../../../../tests/fixtures/solidity-basic/src/Vault.sol).

## Holding invariants
- accounting: INV-002 (`totalDeposits` never exceeds real deposits), INV-004 (ledger <= `totalDeposits` + ETH credited)
- token-conservation: INV-001 (token balance >= `totalDeposits`)
- access-control: INV-006 (owner changes only through the owner)
- bounds: INV-010 (`FEE_BPS` <= 10000)

Caveat: INV-001/INV-002 hold only because the handler skips `withdraw` when the vault's token balance is below the amount. Without that guard, a user with ETH credit withdrawing more tokens than `totalDeposits` would wrap the `unchecked` subtraction. The handler's guard hides this reachable case; `withdraw` would revert in the token transfer, but with a token that does not revert on insufficient balance (return values are unchecked) the wrap is reachable. Treat this as untested rather than safe.

## Inconclusive
- INV-007: same property as INV-005; covered by it.
- INV-008: over-withdrawal revert is a single-call property (checked arithmetic on `balances`), not an invariant; not generated.
- INV-011: fee is never applied (`FEE_BPS` and `setFee` are dead); not expressible as a state invariant without a spec for the intended fee. Flagged for manual review.
- INV-012: `setFee` access control; not generated (owner-only modifier is visible in source).
