# MISSING-AUTH

> **Source class**: stellar-dev-skill security.md class 1
> **Inject into**: Lens A
> **Category**: Access control
> **Tier**: security
> **Related heuristics** (heuristics.md): AUTH-01, AUTH-02, AUTH-06
> **Module**: [modules/soroban-auth.md](../modules/soroban-auth.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 1; modified by ChainSec; see ATTRIBUTION.md -->

## Description

Soroban authorization is opt-in: nothing runs `require_auth` unless the contract does. A `mutating` entry point that moves value or changes rights and never authorizes anyone is callable by everyone. Forgetting the call is the failure mode to hunt for first.

"Authorize" must also mean the *right* address: the one holding policy authority, loaded from storage (the admin, the owner, the account whose balance is debited). `who.require_auth()` on a caller-supplied `who` only proves the caller controls `who`, not that `who` may do anything. For each `Address` argument, ask whether the call spends, reduces or reconfigures something that address owns; if so that address must be authorized. Crediting a balance or reading public data needs no auth.

## Vulnerable pattern

```rust
// BAD: anyone can drain
pub fn withdraw(env: Env, to: Address, amount: i128) {
    transfer_tokens(&env, &to, amount);
}
```

## Secure pattern

```rust
// GOOD
pub fn withdraw(env: Env, to: Address, amount: i128) {
    let admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();
    admin.require_auth();
    transfer_tokens(&env, &to, amount);
}
```

## Detection

- Use `facts.json` to find candidates: `entry_points` with `mutability: mutating`, visibility `external` and empty `guards`; counter `unguarded_mutators` ranks the contracts. Then read each function signature and body to see whether an `Address` parameter loses balance or rights.
- `auth_sites` that call `require_auth` on an `Address` taken from an argument while the privileged action belongs to a stored admin/owner (the stored-authority check is missing).
- `storage_writes` or `value_transfers` in entry points with no `require_auth`, `require_auth_for_args`, `auth_macro` or helper guard on the path.

## False-positive caveats (Gate C / FP-10 evidence)

- The guard sits in a helper (`require_admin(&e)`): facts show it as `... via <helper>`; read the helper.
- OpenZeppelin `#[only_owner]`, `#[only_admin]`, `#[only_role]` and `#[only_any_role]` authenticate the stored holder and count as a guard. `#[has_role]` / `#[has_any_role]` only check membership and do NOT call `require_auth`: the checked address still needs an explicit `require_auth`, otherwise it is MISSING-AUTH.
- Public-by-design writes (crediting a balance, permissionless `bump`/`extend_ttl`, price pokes that only store a value anyone may supply) need no auth; judge by what the write consumes.
- A loaded-but-unused admin variable is the bug, not a guard.
- Contracts whose only callers are other contracts that authorize upstream still need their own auth when they hold funds or rights themselves.

## Minimum tests (PoC and regression targets)

- Call the entry point with no auth mocked (`env.set_auths(&[])`): it must fail with an auth error. A suite that only uses `env.mock_all_auths()` cannot show this; assert on `env.auths()`.
- Call with an unrelated address authorized: it must fail.
- Regression: only the stored authority's auth entry succeeds.
