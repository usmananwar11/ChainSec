# Soroban Token Integration Module

> **Trigger**: `token::Client`, `TokenClient`, `StellarAssetClient`, SEP-41 implementations, `transfer_from`, counter `token_transfers` > 0
> **Inject into**: Lens B (Arithmetic / Value) and Lens C (External Calls)
> **Priority**: HIGH — token handling is where value moves; sign, decimals and untrusted token addresses are the usual bugs
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0), token sections; modified by ChainSec; see ATTRIBUTION.md -->

A "token address" can be a custom SEP-41 contract, a wrapped classic asset's Stellar Asset Contract (SAC) or native XLM's SAC. Complements `domains/defi/modules/token-flow-tracing.md`. Patterns: [UNRESTRICTED-TRANSFER-FROM](../patterns/UNRESTRICTED-TRANSFER-FROM.md), [ARBITRARY-CONTRACT-CALL](../patterns/ARBITRARY-CONTRACT-CALL.md), [INTEGER-OVERFLOW-OR-UNDERFLOW](../patterns/INTEGER-OVERFLOW-OR-UNDERFLOW.md).

## 1. Token Table

| Token | Kind (SAC/custom) | Source of address | Decimals | Freeze/clawback exposure |
|---|---|---|---|---|

- Source of address: hardcoded, set by an admin, allowlisted, or taken from a caller argument (TOK-03). Permissionless means class ARBITRARY-CONTRACT-CALL applies.
- Decimals: SAC is 7; custom tokens can differ. Read `decimals()` at registration and normalize (TOK-05).
- Freeze and clawback: SAC issuers can freeze (`set_authorized`) and `clawback`; accounts need trustlines. Does one frozen or unauthorised recipient block a shared flow (TOK-02)? Name the asset before reporting (Gate B), unless token addresses are permissionless (factories, a token passed as an argument): then an attacker-issued classic asset with `AUTH_REVOCABLE` or clawback counts as the named token.

## 2. Amount Validation

- `i128` amounts are signed. Is `amount < 0` (and usually `amount <= 0`) rejected at every entry point before it reaches a `transfer`, fee or share computation (TOK-01)? A negative amount reverses a flow.
- Zero amounts: do they still change state, allowances or privileges?
- Casts of `i128` amounts to narrower types (ARITH-02).

## 3. Transfer Semantics

- SEP-41 `transfer` panics on failure and returns no bool: do not report an unchecked return value; look at what the failure does to the surrounding flow (XC-04).
- Auth pattern: `transfer`, `approve` and `burn` authorize `from`; `transfer_from` and `burn_from` authorize the **spender**. A contract that takes `from` from the caller and calls `transfer_from` spends a third party's allowance (TOK-04).
- Allowances expire (`expiration_ledger`); re-approving overwrites, so the approve race applies to standing allowances.
- Mint, clawback, `set_admin`, `set_authorized` belong to the SAC admin surface, not SEP-41: who holds that authority in this protocol?

## 4. Custom and Fee-on-Transfer Tokens

- A custom token can charge a fee, burn, or deliver less than requested. Where the contract credits an internal balance from the nominal amount, compare the balance before and after (only for tokens actually in the protocol's list: Gate B; with permissionless token addresses an attacker-deployed fee-charging token counts).
- A custom token can fail, trap or burn budget on any call: a shared flow that calls it (batch payout, liquidation) must not let one token break everyone's path (RES-02).
- Standard event shapes (`transfer`, `approve`, `mint`, `burn`, `clawback`) emitted, so indexers and wallets see the flows.
