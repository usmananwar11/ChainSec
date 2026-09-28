# Oracle Analysis Module

> Chain-specific half of `domains/defi/modules/oracle-analysis.md`.

## 1. Oracle Inventory

For EVERY external data source the protocol reads:

| Oracle | Type | Source | Functions Called | Consumers | Heartbeat |
|--------|------|--------|-----------------|-----------|-----------|
| {name} | Chainlink/TWAP/Spot/Pyth | {address/contract} | {latestRoundData/observe} | {list all consumer functions} | {documented or UNKNOWN} |

## 2. Staleness Analysis

For EACH oracle:

| Check | Code Location | Status |
|-------|--------------|--------|
| `updatedAt` checked? | | YES/NO |
| `answeredInRound >= roundId`? | | YES/NO |
| `updatedAt != 0`? | | YES/NO |
| L2 sequencer uptime feed? (L2 only) | | YES/NO/N/A |

## 5. Failure Modes (WHERE HIGH/CRIT FINDINGS HIDE)

- What if oracle returns a negative price? (`int256` from Chainlink — checked?)
