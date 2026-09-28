# ChainSec Detection Primer: GameFi / NFT / Play-to-Earn

> Chain-specific half of `domains/defi/primers/gamefi-nft.md`.

## CRITICAL — Must Check Every GameFi/NFT Audit

### 1. Mint Supply Cap Bypass
**Check**: Find EVERY function that calls `_mint` or `_safeMint`. Does each one enforce the supply cap?

### 2. Transfer Hook Missing Game State Update
**Check**: Read `_beforeTokenTransfer` / `_afterTokenTransfer` / `_update`. Does it reset/transfer ALL associated game state?

### 5. On-Chain Randomness Manipulation
If attributes/loot use `block.timestamp`, `blockhash`, or `prevrandao` → player can revert and retry until they get desired result.

## HIGH — Check If Relevant

### 10. Asset Locking Bypass via External Marketplace
**Check**: Does `_beforeTokenTransfer` check lock status? Does `approve` check lock status?
