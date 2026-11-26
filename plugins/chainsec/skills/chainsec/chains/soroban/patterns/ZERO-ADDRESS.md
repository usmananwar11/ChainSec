# ZERO-ADDRESS

> **Detector class**: Scout `zero-address`
> **Inject into**: Lens A
> **Category**: Initialization
> **Tier**: security
> **Related heuristics** (heuristics.md): INIT-02
> **Module**: [modules/upgrades-and-init.md](../modules/upgrades-and-init.md)
> <!-- Ported from CoinFabrik scout-soroban (MIT), docs/docs/detectors/20-zero-or-test-address.md and test-cases; see ATTRIBUTION.md -->

## Description

Scout's detector (`zero-or-test-address`) flags an `Address` argument stored or compared as an admin or owner without rejecting the all-zero account. Scout reports that the private key of the zero account is known, so anyone could take over a contract whose admin is set to it; that is not independently verified here. The demonstrable impact is lockout: an admin or owner set to an address nobody controls in practice leaves privileged functions uncallable, and a mistaken or malicious value does this silently.

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

- The takeover claim (key known) comes from Scout and is not independently verified here: report takeover only with evidence, and treat lockout as the demonstrable impact.
- A caller who must `require_auth` is already a signer; validation matters for addresses supplied by another party.
- Rate lockout of a changeable admin lower than lockout of an immutable one.

## Minimum tests (PoC and regression targets)

- Initialize with the zero account and show privileged functions become uncallable.
- Regression: rejects the zero account.
