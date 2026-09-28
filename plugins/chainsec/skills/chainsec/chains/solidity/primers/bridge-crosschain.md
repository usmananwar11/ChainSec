# ChainSec Detection Primer: Cross-Chain Bridge

> Chain-specific half of `domains/defi/primers/bridge-crosschain.md`.

## CRITICAL — Must Check Every Bridge Audit

### 5. Signature Malleability
**Check**: Does signature verification use OpenZeppelin's ECDSA (handles malleability)? Or raw `ecrecover`?

## HIGH — Check If Relevant

### 6. LayerZero: Missing Minimum Destination Gas
If `adapterParams` doesn't enforce `minDstGas` → message arrives on destination but execution fails silently due to OOG. User loses funds with no refund.
**Check**: Is `minDstGas` set in `adapterParams`/`options`? Is it sufficient for the destination function's gas needs?

### 7. LayerZero: Untrusted Remote
If `trustedRemote[chainId]` is not set or set to wrong address → attacker deploys fake contract on source chain, sends messages that destination accepts.
**Check**: Is `trustedRemote` set for ALL supported chains? Can it be changed? By whom?
