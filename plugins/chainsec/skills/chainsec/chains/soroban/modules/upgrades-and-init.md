# Soroban Upgrades and Initialization Module

> **Trigger**: `update_current_contract_wasm` (counter `upgrades` > 0), `initialize`, `__constructor`, migration functions
> **Inject into**: Lens A (Access Control)
> **Priority**: CRITICAL — an unguarded upgrade or init is full contract takeover
> <!-- Ported from stellar/stellar-dev-skill skills/smart-contracts/security.md and development.md (Apache-2.0), upgradeability and constructor sections; modified by ChainSec; see ATTRIBUTION.md -->

Soroban has no proxy and no `delegatecall`: an upgrade replaces the contract's own code in place; the address and storage survive. Patterns: [UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM](../patterns/UNPROTECTED-UPDATE-CURRENT-CONTRACT-WASM.md), [REINITIALIZATION](../patterns/REINITIALIZATION.md), [ZERO-ADDRESS](../patterns/ZERO-ADDRESS.md).

## 1. Upgrade Gate

- Who can reach `update_current_contract_wasm` (older name) or `update_current_contract` (SDK 28 and later per the Stellar guide)? The authorized address must be the stored admin, governance or timelock (UPG-01). The extractor counts both names (`upgrades` counter).
- Is there a delay or governance step when users are promised one? Can users exit before it takes effect (Gate E exception)?
- Is the new wasm hash caller-supplied to a function with no auth, or checked against an allowlist?
- Is the admin itself changeable only by the admin; is the admin a single key or a custom account (`modules/soroban-auth.md`)?

## 2. Layout Compatibility

- New code must decode old entries: `#[contracttype]` enum variants and struct fields are matched by name and shape. Renames, reordering assumptions and reshaped structs strand data or fail to decode (UPG-02).
- Is there a stored schema version and an idempotent, admin-gated `migrate` that enforces `new_version > current_version`? Can `migrate` be called by anyone, or run twice?
- Error codes (`#[contracterror]`) are public ABI: renumbering breaks callers.
- The upgrade takes effect after the current invocation; code after the call still runs the old wasm (UPG-03).

## 3. Initialization

| Init path | Guarded how | Front-runnable? | Arguments validated? |
|---|---|---|---|

- `__constructor` (SDK 22 and later) runs once, atomically at deploy, and does not re-run on upgrade. Check `facts.json` `sdk`: below 22, a guarded `initialize` is the only path (INIT-01).
- A guarded `initialize` (flag or admin-present check): between deploy and init anyone can call it and take admin. Does the deploy script deploy and initialize in the same transaction (factory, or single transaction) (INIT-01, DEPLOY-01)?
- An `initialize` with no guard is REINITIALIZATION outright.
- Stored admin, token, oracle and fee recipient validated, not just non-null (INIT-02). Gate E applies when only the trusted deployer supplies a bad value.
