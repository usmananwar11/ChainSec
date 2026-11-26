# TTL-ARCHIVAL

> **Source class**: stellar-dev-skill security.md class 8
> **Inject into**: Lens D
> **Category**: Storage
> **Tier**: security
> **Related heuristics** (heuristics.md): TTL-01, TTL-02, TTL-03
> **Module**: [modules/storage-and-ttl.md](../modules/storage-and-ttl.md)
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md (Apache-2.0), class 8; modified by ChainSec; see ATTRIBUTION.md -->

## Description

There are two distinct failure modes.

- Critical state expires. A `temporary()` entry silently disappears for good once its TTL lapses. `persistent()` entries archive and need restoration before they can be used, which adds friction or blocks calls until someone pays to restore them. Extend TTLs in hot paths and monitor entry TTLs in production.
- TTL used as a security mechanism. Anyone can extend any entry's TTL (via `ExtendFootprintTTLOp`), so "this entry expires, therefore the permission ends" is broken by design. Store an explicit deadline in the value and check it.

An attacker keeping an entry alive is therefore not a finding by itself; an entry that must disappear to revoke something is.

## Vulnerable pattern

```rust
// BAD: a permission that "expires" only when the entry's TTL lapses
env.storage().temporary().set(&DataKey::Approved(user.clone()), &true);
// anyone can extend this entry's TTL, so it may never lapse
```

## Secure pattern

```rust
// GOOD: explicit deadline in the value, checked on use
env.storage().persistent().set(&DataKey::Approval(user.clone()), &deadline);
let deadline: u64 = env.storage().persistent().get(&DataKey::Approval(user)).unwrap();
if env.ledger().timestamp() > deadline {
    panic_with_error!(&env, Error::Expired);
}
// extend TTLs of state that must stay available
env.storage().persistent().extend_ttl(&key, threshold, extend_to);
```

## Detection

- `storage_writes` to `temporary:` targets for balances, positions, admin, nonces or anything that must survive.
- Persistent or instance writes with no `extend_ttl` on the path or anywhere in the contract (grep the source; `extend_ttl` is not a facts.json field).
- Logic that treats the presence or absence of an entry as a time-limited right, with no stored deadline.

## False-positive caveats (Gate C / FP-10 evidence)

- Temporary storage used for genuinely short-lived data (caches, one-shot nonces with explicit semantics, rate-limit windows).
- TTL extension happens in a different entry point that every user flow passes through, or the operator maintains it off-chain with monitoring.
- Expiry of a permission via TTL is acceptable only if the contract also stores and checks a deadline.
- Extending an entry's TTL by third parties is expected behaviour, not a vulnerability.

## Minimum tests (PoC and regression targets)

- Advance the ledger sequence past the entry's TTL in a test and assert the contract's behaviour: funds or rights must not be lost or locked.
- For deadline logic: extend the TTL as a third party and assert the permission still ends at the stored deadline.
