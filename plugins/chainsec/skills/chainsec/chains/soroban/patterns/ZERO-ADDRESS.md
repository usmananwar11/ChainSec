# ZERO-ADDRESS

> **Detector class**: Scout `zero-address`
> **Inject into**: Lens A
> **Category**: Initialization
> **Tier**: security
> **Related heuristics** (heuristics.md): INIT-02
> **Module**: [modules/upgrades-and-init.md](../modules/upgrades-and-init.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/20-zero-or-test-address.md and test-cases; see ATTRIBUTION.md -->

## Description

Scout's detector (`zero-or-test-address`) flags an `Address` argument stored or compared as an admin or owner without rejecting the all-zero account. Nobody can sign for it, so an admin set to it is permanently unreachable; a mistakenly or maliciously chosen value silently locks privileged functions.

## Vulnerable pattern

```rust
pub fn set(e: Env, admin: Address, data: i32) -> Result<(), Error> {
    if !ensure_is_admin(&e, admin)? { return Err(Error::NotAdmin); }
}
```

## Secure pattern

```rust
if admin == Address::from_string(&String::from_bytes(&e,
    b"GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF")) {
    return Err(Error::InvalidNewAdmin);
}
```

## Detection

- Constructor or `initialize` / `set_admin` parameters of type `Address` stored with no validity check.

## False-positive caveats (Gate C / FP-10 evidence)

- Scout asserts the zero account's private key is known; that is unverified here, so report takeover only with evidence and treat permanent lockout as the demonstrable impact.
- A caller who must `require_auth` is already a signer; validation matters for addresses supplied by another party.
- Rate lockout of a changeable admin lower than lockout of an immutable one.

## Minimum tests (PoC and regression targets)

- Initialize with the zero account and show privileged functions become uncallable.
- Regression: rejects the zero account.
