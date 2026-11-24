# Starknet Account Abstraction Module

> **Trigger**: Protocol implements an account contract, session keys, outside execution (SNIP-9) or a paymaster
> **Inject into**: Lens A (Access/State) + Lens D (Edge/Math/Standards)
> **Priority**: HIGH — every Starknet account is a contract; a validation bug hands over the account
> <!-- Ported from keep-starknet-strange cairo-auditor (MIT): AA-SELF-CALL-SESSION, attack vectors 22, 51, 96, and its account-abstraction, session-key and SNIP-9 notes; see ATTRIBUTION.md -->

Reason across `__validate__` and `__execute__` jointly: a check in one that the other relies on must hold for the same calls.

## 1. Protocol Entry Points

| Entry point | Called by | Must check |
|---|---|---|
| `__validate__(calls)` | Protocol (caller zero) | Signature over the transaction hash; cheap; no external calls; no storage writes beyond what the protocol allows; returns `starknet::VALIDATED` |
| `__execute__(calls)` | Protocol (caller zero) | `get_caller_address().is_zero()`; transaction version; then executes calls |
| `__validate_declare__`, `__validate_deploy__` | Protocol | Same signature rules; own version check (ConsenSys Argent finding) |
| `is_valid_signature(hash, signature)` | Any contract | Returns `starknet::VALIDATED` only for a valid signature; has no call context |

- `__execute__` without the zero-caller check lets any contract make the account execute arbitrary calls (CALLER-02; chipi-pay "unrestricted `__execute__` caller").
- Validation that depends on mutable external state can pass in validation and fail in execution: grief for sequencers and paymasters.
- Since Starknet v0.14.0, internal calls to an entry point named `__execute__` revert, and only V3 transactions exist; legacy accounts without `__validate__` are reached through `meta_tx_v0`.

## 2. Session Keys and Delegated Signers

| Session path | Self-call blocked? | Selector policy | Per-token value cap | Call counter | Expiry / revocation |
|---|---|---|---|---|---|

- Self-calls (`call.to == get_contract_address()`) blocked for session keys — the primary defense (AA-SELF-CALL-SESSION, AV-22).
- A denylist alone is fragile: each audit scan of one session contract found new privileged selectors (`upgrade`, session add/revoke, `__execute__`, `set_public_key` and its camelCase twin `setPublicKey`, `execute_from_outside_v2`).
- Selector allowlists don't limit value: a session allowed to call `transfer` can move the whole balance. Spending policy bound to the same token the selectors move (AV-51), with a rolling window.
- Call counters incremented after signature verification, and not resettable (chipi-pay `calls_used` findings).
- One signature authorizes one bound set of calls (AV-96); revocation removes every capability surface (AV-114).

## 3. Outside Execution (SNIP-9)

- Outside-execution nonce is separate from the transaction nonce and must be consumed before executing.
- `caller` checked unless it is `ANY_CALLER` (which lets anyone submit); `execute_after` < now < `execute_before`, with a short window.
- Signature is SNIP-12 over the full `OutsideExecution` struct with `chain_id` in the domain (signatures-and-replay.md).
- Nested outside execution / reentry into `__execute__` blocked.

## 4. Fees and Paymasters

- Guardian/escape flows cap every V3 resource bound (L1 gas, L2 gas and tip), not only the tip (ConsenSys Argent "lack of fee limits for V3 transactions").
- Paymasters: an account can pass validation and fail execution to burn the paymaster's gas; token-paying flows must collect before sponsoring; allowlists and rate limits on sponsored entry points.

## 5. Keys

- Public keys validated (on the STARK curve) before storage; key rotation (`set_public_key`) reachable only by the owner path.
- Multisig accounts dedupe signers before counting toward the threshold (AV-164); threshold floor (AV-126).
