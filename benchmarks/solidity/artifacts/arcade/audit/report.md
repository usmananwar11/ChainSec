# ChainSec Security Audit Report

**Target**: Arcade.xyz governance (Council Framework based): voting vaults, token, NFT multiplier, treasury, airdrop
**Date**: 2026-10-16
**Auditor**: ChainSec
**Scope**: contracts/ArcadeGSCCoreVoting.sol, contracts/ArcadeTreasury.sol, contracts/BaseVotingVault.sol, contracts/ARCDVestingVault.sol, contracts/ImmutableVestingVault.sol, contracts/NFTBoostVault.sol, contracts/ArcadeGSCVault.sol, contracts/token/ArcadeAirdrop.sol, contracts/token/ArcadeToken.sol, contracts/token/ArcadeTokenDistributor.sol, contracts/nft/ReputationBadge.sol, contracts/nft/BadgeDescriptor.sol

---

## Executive Summary

ChainSec audited the 12 in-scope Solidity files (Solidity 0.8.18, built on the Council framework). No finding at Medium severity or above survived verification. One candidate survived at Low severity after a downgrade from Medium (a shared per-block treasury expenditure counter). Low-severity items are not reported as findings, so the report lists none. Overall assessed risk is low. This conclusion comes from a blind, non-executed review (see Methodology), so it is not proof that no issues remain.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

---

## Findings

No reportable findings.

Seven candidates were killed by the kill gates (ARCDVestingVault NatSpec unit mismatch, `delegate()` zero-weight checkpoint spam, ReputationBadge overpayment, treasury approval revocation, raw `approve` token compatibility, ETH `transfer` stipend, and the NFTBoostVault empty-registration state). One candidate (DC-1) was downgraded to Low and omitted under the Low-severity exclusion. See Architecture Observations.

---

## Security Strengths

- **Access control model**: ArcadeTreasury uses OpenZeppelin `AccessControl` with distinct roles (ADMIN, CORE_VOTING, GSC_CORE_VOTING) separating governance spend/approve paths from the GSC's bounded allowance.
- **Reentrancy protection**: ArcadeTreasury inherits `ReentrancyGuard`, and the vaults (ARCDVestingVault, BaseVotingVault, NFTBoostVault) use the custom `HashedStorageReentrancyBlock`.
- **Arithmetic safety**: All contracts compile with Solidity 0.8.18 (checked arithmetic), and treasury ERC20 transfers go through SafeERC20 `safeTransfer`.
- **Battle-tested dependencies**: OpenZeppelin (ERC20, ERC1155, AccessControl, Ownable, MerkleProof) and the Council framework (CoreVoting, GSCVault, Timelock) are used for core governance and token primitives.
- **Area for improvement**: Some paths lack input validation and sanity bounds (for example `delegate()` in both vaults has no registration/grant requirement, and the vesting schedule has no bound check on cliff/expiration against the current block).

---

## Architecture Observations

- NFTBoostVault (about 650 LOC) is the highest-risk unit: it couples voting-power history, delegation, NFT multipliers and withdraw locks. It would benefit from invariant and fuzz testing, such as `registration.delegatee != 0` iff `amount > 0`.
- ArcadeTreasury `blockExpenditure[block.number]` is a single counter shared across all tokens and across the GSC and CORE_VOTING paths, summing raw units of different decimals. Executing two spends in one block can revert the later one. The harm is temporary and retryable (DC-1, downgraded to Low and not reported as a finding). Keying the counter by token (and possibly role) would remove the coupling.
- Several documented trade-offs were deliberately killed as design or trusted-role behaviour: ETH sent with `transfer` (2300 gas), and vesting schedules in block numbers while the NatSpec says timestamps. They are worth aligning in documentation.
- Council framework contracts under `contracts/external/council` are out of scope and were reviewed only at integration points.

---

## Methodology

**Audit mode**: Full pipeline (`quick` is false). The audit was blind; the linked Slither gist and Omniscia PDF were not read.

Completed phases: Recon, Detection (Pass 1, four lenses and final sweep), Rescan, Per-unit deep dives, State Analysis, Verification (kill gates and exploit traces). Incomplete phases: none.

Mode notes: facts mode is `regex` (solc is not installed, so there are no compiler-mode facts and structural facts are pattern-matched with lower confidence). Preflight tooling mode is `degraded` (Slither is missing; forge 1.7.1 and python3 were available). No executable PoCs were run: the audit pipeline's critic does not build PoCs, and chainsec-poc was not run. All evidence is therefore `REASONED` / code-trace, not executed.

Preflight warnings: rescan reinforced DA-1 (unguarded `delegate()` in ARCDVestingVault also lacks a zero-address check on `to`; an unregistered NFTBoostVault caller ends up with a non-zero `registration.delegatee`); facts mode is regex; Slither not installed (degraded mode).

Methodology derived from Krait by Zealynx Security.

---

```
───────────────────────────────────────────────────
📋 0 findings saved to .audit/findings.json
───────────────────────────────────────────────────
```

Next steps:

1. **Review killed findings**: seven candidates were killed by the automatic gates; run `chainsec-review` for a second opinion (notably the gate D and E kills).
2. **Prove a finding**: no Critical or High findings exist, so `chainsec-poc` has nothing to prove.
3. **Fuzz invariants**: run `chainsec-fuzz` to test the NFTBoostVault registration and voting-power invariants.
