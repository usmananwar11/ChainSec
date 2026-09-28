# Domain module triggers

Based on what you discovered in Steps 1-5, evaluate each detection module's trigger condition and select the ones that apply. **This is deterministic — if the trigger condition is met, the module is selected.**

Evaluate each module file in `domains/defi/modules/` against what you found:

**Module tier hierarchy:**
- **Tier 0 (always-load)**: `domains/defi/modules/access-control-state.md` — always active for every audit
- **Tier 1 (protocol-type)**: Core domain modules — selected when protocol matches a specific type (lending, DEX, vault, etc.)
- **Tier 2 (feature-detected)**: Specialized modules — selected when specific features/patterns are detected in code

| Module | Tier | Trigger (chain-agnostic) |
|---|---|---|
| `domains/defi/modules/access-control-state.md` | 0 | Always active |
| `domains/defi/modules/oracle-analysis.md` | 1 | Protocol uses Chainlink, TWAP, Pyth, Band, or any external price feed |
| `domains/defi/modules/vault-share-accounting.md` | 1 | Protocol implements a share-based vault |
| `domains/defi/modules/lending-liquidation-deep.md` | 1 | Protocol has lending/borrowing/liquidation mechanics |
| `domains/defi/modules/amm-mev-deep.md` | 1 | Protocol is DEX/AMM or deeply integrates with liquidity pools |
| `domains/defi/modules/economic-design.md` | 1 | Protocol has token economics, fee structures, liquidation mechanics, or incentive systems |
| `domains/defi/modules/governance-voting.md` | 1 | Protocol has voting, proposals, delegation, quorum, or governance tokens |
| `domains/defi/modules/flash-loan-interaction.md` | 2 | Protocol reads its own token balance, uses spot prices, has deposit/withdraw, or integrates with flash-loan-capable protocols |
| `domains/defi/modules/token-flow-tracing.md` | 2 | Any token transfer, mint, burn, or own-balance read |
| `domains/defi/modules/external-protocol-integration.md` | 2 | Protocol integrates with Uniswap, Aave, Compound, Curve, Chainlink, Convex, Lido, or any external DeFi protocol |
| `domains/defi/modules/cross-chain-bridge.md` | 2 | Protocol bridges assets/messages across chains |
| `domains/defi/modules/multi-tx-attack.md` | 2 | Protocol has deposit+withdraw, staking+claiming, or sequenceable operations |

**Selection rules:**
- Select ALL modules whose trigger condition is met — do not cap the count
- `domains/defi/modules/access-control-state.md` is ALWAYS selected
- For DeFi protocols, `domains/defi/modules/token-flow-tracing.md` and `domains/defi/modules/economic-design.md` are almost always selected
- Record the trigger evidence (what you found that triggered the module)

Each pack's module-triggers.md adds its own modules and the code-level evidence strings for these triggers.
