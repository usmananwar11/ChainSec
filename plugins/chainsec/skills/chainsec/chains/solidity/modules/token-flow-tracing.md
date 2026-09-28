# Token Flow Tracing Module

> Chain-specific half of `domains/defi/modules/token-flow-tracing.md`.

## 1. Token Entry Points

Where can tokens enter the contract?

| Entry Point | Function | Token Type | Tracked By | Bypass Possible? |
|-------------|----------|------------|-----------|-----------------|
| Callback | `onERC721Received` etc | ERC-721/1155 | ??? | Depends |
| Native ETH | `receive()`/`fallback()` | ETH | ??? | YES |

## 3. Token Exit Points

| Exit Point | Function | Recipient | Balance Check | CEI Order? |
|------------|----------|-----------|---------------|-----------|
| Withdraw | `withdraw()` | msg.sender | `require(bal >= amount)` | ??? |
