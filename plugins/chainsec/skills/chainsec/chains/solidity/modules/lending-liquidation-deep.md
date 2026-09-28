# Lending & Liquidation Deep Analysis Module

> Chain-specific half of `domains/defi/modules/lending-liquidation-deep.md`.

## 5. Health Factor During Callbacks

- During ERC721/ERC1155 `onReceived` callback: health factor reflects pre-transfer state → borrow more than allowed
