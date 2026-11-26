# Soroban Resource Limits Module

> **Trigger**: loops over storage `Vec` / `Map`, per-user lists, batch entry points
> **Inject into**: Lens D (Edge Cases / DoS)
> **Priority**: MEDIUM-HIGH — a function that no longer fits the per-transaction limits is a DoS on every legitimate user
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0), resource exhaustion and fee sections; modified by ChainSec; see ATTRIBUTION.md -->

Each transaction has per-transaction ceilings on CPU instructions, memory, ledger entries read and written, bytes, and events. The values are network-configured and change by validator vote: read the live values (Stellar Lab network limits, or `stellar network settings`) instead of assuming. Patterns: [DOS-UNBOUNDED-OPERATION](../patterns/DOS-UNBOUNDED-OPERATION.md), [DOS-UNEXPECTED-REVERT-WITH-VECTOR](../patterns/DOS-UNEXPECTED-REVERT-WITH-VECTOR.md), [RESOURCE-EXHAUSTION](../patterns/RESOURCE-EXHAUSTION.md).

## 1. Loops and Batches

| Function | Loop bound source | Who grows it? | Per-iteration cost (storage, events, calls) | Cap? |
|---|---|---|---|---|

- Bound from an argument or from a stored collection that anyone can append to (RES-01). Can an attacker push it past the limits cheaply, and does a legitimate user's function then stop fitting (RES-02)?
- Per-iteration storage reads and writes, events and cross-contract calls multiply the cost and the footprint; every entry touched must be in the footprint.
- A batch where one failing element (frozen recipient, missing trustline, panicking `unwrap`) reverts everyone: does the design isolate failures (RES-02, PANIC-01)?

## 2. Growable Collections

- A `Vec` / `Map` in one entry that grows per user: the whole entry is read and rewritten on each touch, and the entry size is capped (STOR-04, STOR-03). Per-key entries avoid both.
- Is removal possible, or does the collection only grow?

## 3. Fee Griefing and Rent

- An attacker-shaped input that makes other users' transactions costlier (larger entries, more entries in a shared footprint, more rent to extend) without the attacker bearing the cost (RES-03).
- Unbounded signature or signer counts in `__check_auth`: every transaction the account signs pays for the verifications (RES-03).

## 4. What Does Not Count

- A loop bounded by a small constant, or by a collection only the admin can grow, is not a finding (Gate E, FP-5). State the bound.
- Cost that only hurts the caller who chose the input is not a DoS on others; severity needs a third-party victim.
