# Cross-Chain Bridge Security Module

> Chain-specific half of `domains/defi/modules/cross-chain-bridge.md`.

## 2. Destination Gas

| Bridge | Min Gas Enforced? | Configured Value | Sufficient? |
|--------|-------------------|-----------------|-------------|
| LayerZero | adapterParams minDstGas? | | |
| CCIP | gasLimit in message? | | |

## 5. Refund Routing

When destination execution fails:
- Refund goes to msg.sender on destination? → wrong person
