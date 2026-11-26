# Soroban Cross-Contract Calls Module

> **Trigger**: `*Client::new` on non-token contracts, `invoke_contract`, `try_invoke_contract`, `contractimport!`
> **Inject into**: Lens C (External / Cross-contract)
> **Priority**: HIGH — a caller-chosen callee is arbitrary code; unchecked return values drive prices and balances
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0), cross-contract sections; modified by ChainSec; see ATTRIBUTION.md -->

Chain-specific half of `domains/defi/modules/external-protocol-integration.md` and `domains/defi/modules/cross-chain-bridge.md` for Soroban. Patterns: [ARBITRARY-CONTRACT-CALL](../patterns/ARBITRARY-CONTRACT-CALL.md), [UNTRUSTED-RETURN-VALUE](../patterns/UNTRUSTED-RETURN-VALUE.md), [UNUSED-RETURN-ENUM](../patterns/UNUSED-RETURN-ENUM.md).

## 1. Callee Table

List every `*Client::new(&env, &addr)`, `invoke_contract` and `try_invoke_contract` (`facts.json` `external_calls`; targets are not in facts, read the code):

| Call site | Callee address source | Trusted? | Return value checked? | Failure handling |
|---|---|---|---|---|

- Callee address from arguments or user-writable storage: arbitrary code that can fail, trap, burn budget, emit misleading events or return anything. It cannot re-enter this contract (XC-01, XC-03).
- Trusted callees are hardcoded, set by an admin or allowlisted; check who can change the stored address.

## 2. Return Values

- Prices, rates, balances and reserves returned by another contract: range, sign and freshness (timestamp) checked? A zero or negative value (XC-02)?
- `contractimport!` clients: is the imported wasm the one deployed at the callee address? A stale import can mis-decode.

## 3. Failure Handling

- A plain call that fails reverts the whole transaction; `try_*` and `try_invoke_contract` return the error to the caller. What does the continuation assume (XC-04)? Budget exhaustion and footprint violations cannot be caught by `try_` calls.
- A `Result` dropped, `let _ =`, or `.ok()` on a call whose success the flow depends on (UNUSED-RETURN-ENUM).
- One failing callee in a loop over callees must not block the others (RES-02).

## 4. Ordering and Auth

- The host blocks re-entry into a contract on the call stack, so do not report callback reentrancy (FP-S1). State updates before an external call still matter when a `try_` call lets execution continue after a failure (XC-03).
- Calls that pass a user's address on to the callee: is the user authorized here (AUTH-03, `modules/soroban-auth.md`)? Does `authorize_as_current_contract` cover exactly the needed sub-invocation?
- Calls to a bridge or messaging endpoint: see `domains/defi/modules/cross-chain-bridge.md`; Soroban has no native messaging layer, so replay and source-chain validation are the protocol's own (BYTES-02).
