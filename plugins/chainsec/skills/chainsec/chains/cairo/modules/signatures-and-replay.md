# Signatures & Replay Module

> **Trigger**: Protocol verifies off-chain signatures (`check_ecdsa_signature`, account `is_valid_signature`, SNIP-12 typed data, permits, signed oracle prices) or keeps nonces
> **Inject into**: Lens D (Edge/Math/Standards) + Lens A (Access/State)
> **Priority**: HIGH — a replayable signature repeats a payment or an authorization
> <!-- Ported from keep-starknet-strange cairo-auditor (MIT): signature/nonce notes and attack vectors 67, 68, 73, 96, 116, 117, 163, 164, 168; see ATTRIBUTION.md -->

## 1. What Is Signed

For every signature check, list the fields bound by the signed hash:

| Signed action | chain_id | verifying contract | signer/account | nonce | expiry | action type | all parameters |
|---|---|---|---|---|---|---|---|

Any unbound field is attacker-chosen at submission time:
- No nonce → replay the same action (SIGN-02; the classic Cairo `claim_reward(amount, r, s)` bug).
- No `chain_id` → replay between mainnet, Sepolia and forks.
- No verifying contract → replay on another deployment or another contract of the protocol (AV-117).
- No action discriminator → a signature or proof for one action used for another (AV-73, AV-168).
- Unsigned parameters (recipient, amount, token) → substituted.

## 2. SNIP-12 Typed Data

- Domain: `name`, `version`, `chain_id`, `revision`. The final hash binds the signer's account address but not the verifying contract — separation between contracts relies on the domain name/version or an explicit contract field.
- Revision 0 (`StarkNetDomain`, Pedersen) vs revision 1 (`StarknetDomain`, Poseidon): signer and verifier must use the same revision.
- Hardcoded type hashes match their type strings character by character (field names, `felt` vs `ContractAddress` vs `u256`, `u128` for expiry since SNIP-12 has no `u64`).
- Prefer OZ `OffchainMessageHash` / `StructHash` over hand-rolled hashing; check any hand-rolled hash for domain separation and canonical field boundaries (AV-67, AV-116).

## 3. Nonces

- Nonce consumed before effects and in the same transaction as the check (OZ `NoncesComponent::use_checked_nonce` validates and increments atomically; `use_nonce` does not check).
- Nonce scope: per signer and per action domain (AV-73); advanced on every transition that invalidates signed intent, including unset/reset (AV-68).
- Bundled operations bind the whole call set to one nonce (AV-96).

## 4. Verification Mechanics

- `check_ecdsa_signature(hash, public_key, r, s)` returns `bool`: is the result asserted?
- `Span<felt252>` signatures: length checked before reading `r`, `s` (or multiple signers).
- Account signatures via `ISRC6Dispatcher { contract_address: signer }.is_valid_signature(hash, sig)`: compared to `starknet::VALIDATED`, and the signer address is the one the action is for.
- Public keys validated on the STARK curve before use (C4 Starknet Perpetual L-04).
- Multisig / aggregated verification dedupes signers (AV-164).
- Signed data read from storage maps: a missing key returns zero — never accept a zero public key or zero oracle entry (MAP-01; C4 Starknet Perpetual H-01).

## 5. Permits

- ERC20 permit (SNIP-12 approvals) can be front-run: integrations must not assume their `permit` call is the one that sets the allowance, and must not revert the whole flow if the allowance is already set.
- Permit token address validated against the expected asset; deadline enforced.
