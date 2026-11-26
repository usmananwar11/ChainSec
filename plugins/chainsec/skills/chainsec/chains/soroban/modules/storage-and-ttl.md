# Soroban Storage and TTL Module

> **Trigger**: Always — every contract stores data with a TTL
> **Inject into**: Lens D (Edge Cases / State)
> **Priority**: HIGH — expired or colliding entries lose or corrupt funds without any attacker privilege
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0), storage and TTL sections; modified by ChainSec; see ATTRIBUTION.md -->

Soroban storage has three tiers with different lifetimes: `instance()` (one entry shared with the contract instance; archived and restorable), `persistent()` (per-key; archived and restorable) and `temporary()` (per-key; deleted for good on expiry). Patterns: [TTL-ARCHIVAL](../patterns/TTL-ARCHIVAL.md), [STORAGE-KEY-COLLISION](../patterns/STORAGE-KEY-COLLISION.md), [VEC-COULD-BE-MAPPING](../patterns/VEC-COULD-BE-MAPPING.md).

## 1. Storage Inventory

For every key (`#[contracttype]` enum variant or ad-hoc key; `facts.json` `storage_writes` lists the writers and the tier):

| Key | Tier | Writer | Grows per user? | TTL extended where? |
|---|---|---|---|---|

`facts.json` has no `extend_ttl` calls: grep for `extend_ttl` and fill the last column from the code.

## 2. Tier Choice

- Data that must survive (balances, positions, admin, config, allowance-like grants) in `temporary()` is lost for good (TTL-02).
- Per-user or unbounded data in `instance()`: instance storage is one entry read on every call and size-capped (STOR-03).
- Is `temporary()` used only for expendable data (caches, quotes, allowances that expire with their TTL by design)?

## 3. Archival Paths

- For each persistent or instance entry, what keeps it alive, and what happens to the flows that read it when it is archived: stuck funds, DoS, or a restore path (TTL-01)?
- Is instance TTL extended on hot entry points, and per-user entries on write?
- `get(..).unwrap()` on an entry that can be archived or deleted turns expiry into a panic on someone else's path (PANIC-01); a silent `unwrap_or(0)` turns it into a wrong zero.
- Anyone can extend any entry's TTL, so an attacker extending TTLs is not a finding by itself. TTL expiry used as the mechanism that ends a permission or deadline is: store a deadline in the value and check it (TTL-03).

## 4. Key Collisions and User-Controlled Keys

- One `#[contracttype]` key enum for the contract; no overlapping tuple shapes or raw `Symbol` keys across modules or library crates (STOR-01).
- Keys built from user-controlled input (`Symbol`, `String`, `Bytes`): can an attacker choose a key that overwrites or shadows another entry (STOR-02)?

## 5. Growth

- A `Vec` or `Map` in a single entry that grows per user (STOR-04); prefer per-key entries. See `modules/resource-limits.md` for the cost side.
- Entry size limits on instance and persistent entries (read the live network setting).
