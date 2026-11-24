# Components & Storage Layout Module

> **Trigger**: Contract embeds components (`component!`, `#[substorage(v0)]`) or customizes storage (storage nodes, custom `Store`, derived storage keys)
> **Inject into**: Lens A (Access/State) + Lens D (Edge/Math/Standards)
> **Priority**: MEDIUM-HIGH — components add entry points and storage the contract file does not show
> <!-- Ported from keep-starknet-strange cairo-auditor (MIT): storage-layout notes and attack vectors 62, 74, 111, 112, 116, 157, 158, 160, 161, 167; see ATTRIBUTION.md -->

Analyze the contract together with every component it embeds (`recon/clustering.md`).

## 1. Storage Address Model

- Plain variable: address = `sn_keccak(name)`. `Map` entry: hash of the base and the key(s). Storage nodes and `Vec` derive member addresses from the parent path.
- With `#[substorage(v0)]`, a component's members sit in the contract's flat namespace: the address comes from the member name alone, not from the component name.
- Values wider than one felt (`u256`, structs) span consecutive slots from the base (U256-02).

## 2. Collisions

| Storage member | Declared in (contract / component) | Name collides with |
|---|---|---|

- Two components, or a component and the contract, with the same member name share a slot (AV-111). OZ components prefix their members (`ERC20_balances`, `Ownable_owner`); check custom and third-party components.
- Custom `Store` impls and `storage_address_from_base` / raw `storage_read_syscall` / `storage_write_syscall` keys bypass namespacing: a derived key must include every discriminator — domain, action, actor, id (AV-74, AV-112).
- Composite keys hashed from mixed encodings (felts, spans, `ByteArray`) without boundaries alias (AV-116).
- Registering an existing id or address silently overwrites the entry (AV-157).

## 3. Embedded Surface

| Embedded impl (`#[abi(embed_v0)]`) | Component | Selectors exposed | Privileged? | Guard |
|---|---|---|---|---|

- Mixin impls expose snake_case and camelCase twins; account impls expose key rotation; any of them reachable by a session key or an unprivileged caller is a finding (AA-SELF-CALL-SESSION).
- `InternalImpl` never embedded; internal functions such as `UpgradeableComponent::upgrade` or `ERC20Component::mint` are exposed only through guarded wrappers.
- Component initializers called once, in the constructor.
- Hooks (OZ ERC20/ERC721 `before_update`/`after_update`): logic placed there covers every transfer route; a hook that calls out is a reentrancy window (COMP-03).

## 4. Storage Data Structures

- `Map` reads return zero for missing keys: zero must not mean registered/authorized (MAP-01, AV-62); burned/revoked entries cleared where reads assume deletion (AV-63).
- `Vec` and manual arrays: user-growable without a cap (UNBOUNDED-LOOP); stored length updated with the elements (AV-158); removal updates every secondary index (INCORRECT-LIST-REMOVAL, AV-160).
- Counters shared by several functions updated on every path (AV-161, AV-167).
- Reads through an `@self` snapshot while writing live state in a loop (STALE-SNAPSHOT-READ); a field written twice from a stale copy (STALE-STATE-WRITE).

## 5. Upgrade Interaction

Storage names, types, `Map` key types and component substorage names must stay stable across class upgrades (UPG-02 in heuristics.md; `modules/starknet-access-and-upgrades.md` section 3).
