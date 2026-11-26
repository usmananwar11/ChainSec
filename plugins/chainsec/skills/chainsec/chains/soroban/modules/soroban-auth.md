# Soroban Authorization Module

> **Trigger**: Always — every contract has `require_auth` decisions
> **Inject into**: Lens A (Access Control)
> **Priority**: CRITICAL — authorization is opt-in; the missing or mis-targeted `require_auth` is the first bug to hunt
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0), authorization and custom-account sections; modified by ChainSec; see ATTRIBUTION.md -->

Soroban has no implicit caller. Each function authorizes the addresses it acts for with `Address::require_auth`; the host checks that the address authorized this contract, function and arguments, and handles nonces and expirations itself (AUTH-04). Patterns: [MISSING-AUTH](../patterns/MISSING-AUTH.md), [AUTH-REPLAY-MIDDLEWARE](../patterns/AUTH-REPLAY-MIDDLEWARE.md), [CUSTOM-ACCOUNT-CHECK-AUTH](../patterns/CUSTOM-ACCOUNT-CHECK-AUTH.md).

## 1. Auth Map

List every entry point (`facts.json` `entry_points`, plus default methods of `#[contracttrait]` parents, which become live entry points once mixed in) that writes storage, calls another contract or moves tokens:

| Entry point | Address args | require_auth on | Source of authority |
|---|---|---|---|

- Every `Address` argument whose rights are spent, reduced or reconfigured must be authorized (AUTH-01). Crediting a balance or a pure read needs none.
- Privileged paths authorize the admin or role holder **loaded from storage**, not a parameter (AUTH-02).
- Empty `guards` on a `mutating` entry point is a strong lead; non-empty `guards` is a hint only: a `require_auth` inside an `if` branch, or in a helper the extractor did not follow, may not cover every path.
- `#[only_owner]`, `#[only_admin]`, `#[only_role]`, `#[only_any_role]`: read what they expand to for the version in use, and check the role-admin paths (AUTH-05). `#[has_role]` / `#[has_any_role]` are membership-only checks that do NOT call `require_auth`: the checked address needs an explicit `require_auth`; the extractor does not count them as guards.

## 2. Middleware and Replay

- For each entry point that calls a token or another contract **with a user's address**, is the user authorized in this function too? Otherwise anyone can call it and consume a pre-signed auth tree that includes the inner call (AUTH-03).
- Auth does not cascade through the call graph: the signed tree must contain the inner calls. Refactoring a call between helper contracts changes the tree shape.
- Do not report nonce or replay problems on plain `require_auth`: the host handles them (FP-S2).

## 3. `require_auth_for_args`

- Which arguments are bound? A partial binding (for example the amount but not the recipient, or the recipient but not the token) lets a relayer change what is not listed (AUTH-04).
- Is the contract enforcing `actual <= signed maximum` where a maximum was signed?

## 4. Custom Accounts (`__check_auth`)

- Signatures are verified over `signature_payload`, every required signer is checked, and signer sets cannot be satisfied by duplicates (ACCT-01).
- Policy is enforced per `auth_contexts` entry: contract, function name and arguments; unrecognised contexts are rejected rather than ignored (ACCT-02).
- `__check_auth` does not `require_auth` its own address; signature counts are bounded (RES-03).
- With CAP-71 delegation, each address from `get_delegated_signers()` is verified as a registered delegate before `delegate_auth` (verify the API in the SDK version in use).

## 5. `authorize_as_current_contract`

- Entries passed to `authorize_as_current_contract` cover exactly the sub-invocation the callee needs (contract, function name, arguments), not a broader or reusable authorization.
- Contract A authorizing a call to contract B covers B's direct invocation; a deeper call that needs A's authority must be pre-authorized.

## 6. Tests

- Tests using `env.mock_all_auths()` cannot show missing auth: are there assertions on `env.auths()` for the sensitive entry points (AUTH-06)? A gap here is a testing note, not a contract bug (FP-S4).
