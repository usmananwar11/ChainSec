# Known issues (Gate H)

Source: README "Automated Findings / Publicly Known Issues": everything in the automated findings output is a publicly known issue. The local copy is `slither/FullReport.md`. The linked gist is not available offline and was not fetched. The prior audit is `audits/Omniscia2023.pdf` (not parsed).

Known categories from `slither/FullReport.md` that touch in-scope files:
- arbitrary-send-eth: `ArcadeTreasury._spend`, `ReputationBadge.withdrawFees`
- unchecked-transfer: `ARCDVestingVault.deposit` (ID-2) and other transfer sites (IDs 4-6)
- incorrect-equality: `ARCDVestingVault.claim` (strict equality)
- reentrancy-no-eth / benign / events / unlimited-gas: several, including `ARCDVestingVault.revokeGrant` and `ReputationBadge.withdrawFees`
- unused-return: `ArcadeTreasury._approve` and others
- shadowing-local: `NFTBoostVault` and `ArcadeGSCVault` constructors
- calls-loop: `ArcadeTreasury.batchCalls`
- timestamp comparisons: `ReputationBadge.publishRoots`, `ArcadeTreasury.setGSCAllowance`, `ArcadeToken.mint`, `ArcadeAirdrop.reclaim`
- assembly, low-level-calls, naming-convention, too-many-digits, dead-code, solc-version, and `ArcadeMerkleRewards.votingVault` should be immutable

Out of scope per README: `contracts/external/` (Council contracts) and `contracts/test/`. Integration or edge-case misuse of the external Council contracts by in-scope code remains reportable.
