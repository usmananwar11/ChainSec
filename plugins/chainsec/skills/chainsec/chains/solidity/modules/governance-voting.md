# Governance Voting Integrity Module

> Chain-specific half of `domains/defi/modules/governance-voting.md`.

## 6. Advanced Governance Vectors
<!-- Vectors from pashov/skills (MIT) -->

- **Self-delegation doubling**: If delegating to self counts as both holder AND delegatee voting power → 2x votes. Check: does `_delegate(msg.sender)` double-count?
