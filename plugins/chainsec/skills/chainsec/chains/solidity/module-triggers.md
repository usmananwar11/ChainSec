# Solidity module triggers

Rows from the Krait recon Step 6 table for the modules in `chains/solidity/modules/`. Tier hierarchy and selection rules: `domains/defi/triggers.md`.

| Module File | Tier | Trigger Condition | Select If... |
|---|---|---|---|
| `chains/solidity/modules/access-control-state.md` | 0 | Always active | Always selected — every protocol has access control |
| `chains/solidity/modules/oracle-analysis.md` | 1 | Protocol uses Chainlink, TWAP, Pyth, Band, or any external price feed | You found oracle imports, `latestRoundData`, `getPrice`, TWAP calls, or price-dependent logic |
| `chains/solidity/modules/erc4626-vault-deep.md` | 1 | Protocol implements ERC-4626 or custom share-based vault | You found ERC4626 inheritance, `convertToShares`, `convertToAssets`, share-based deposit/withdraw |
| `chains/solidity/modules/lending-liquidation-deep.md` | 1 | Protocol has lending/borrowing/liquidation mechanics | You found `borrow`, `repay`, `liquidate`, health factor checks, or interest accrual |
| `chains/solidity/modules/amm-mev-deep.md` | 1 | Protocol is DEX/AMM or deeply integrates with liquidity pools | You found swap functions, liquidity provision, tick math, or pool interaction |
| `chains/solidity/modules/governance-voting.md` | 1 | Protocol has voting, proposals, delegation, quorum, or governance tokens | You found governance contracts, voting functions, delegation, or quorum logic |
| `chains/solidity/modules/token-flow-tracing.md` | 2 | Any `transfer`, `transferFrom`, `safeTransfer`, `mint`, `burn`, `balanceOf(this)` | You found token transfers (virtually always selected for DeFi) |
| `chains/solidity/modules/external-protocol-integration.md` | 2 | Protocol integrates with Uniswap, Aave, Compound, Curve, Chainlink, Convex, Lido, or any external DeFi protocol | You found external protocol imports or interface calls to known DeFi protocols |
| `chains/solidity/modules/eip-standard-compliance.md` | 2 | Protocol implements ERC-20, ERC-721, ERC-4626, ERC-1155, ERC-2981, ERC-3156, EIP-712 | You found ERC/EIP interface implementations or standard compliance claims |
| `chains/solidity/modules/cross-chain-bridge.md` | 2 | Protocol bridges assets/messages across chains | You found LayerZero, CCIP, Wormhole, Axelar, Hyperlane, or custom bridge/relayer code |
| `chains/solidity/modules/eip7702-delegation.md` | 2 | Protocol uses EIP-7702 or handles delegated EOAs | You found `EXTCODESIZE` checks for EOA detection, `tx.origin` usage, or EIP-7702 delegation handling |
| `chains/solidity/modules/account-abstraction-erc4337.md` | 2 | Protocol implements ERC-4337 or handles UserOperations | You found `validateUserOp`, `IEntryPoint`, `UserOperation` struct, paymaster logic, or bundler interaction |

## Code evidence for domain module triggers

The Solidity code evidence (Krait's "Select If..." column) for each trigger in `domains/defi/triggers.md`.

| Module | Select If... |
|---|---|
| `domains/defi/modules/access-control-state.md` | Always selected — every protocol has access control |
| `domains/defi/modules/oracle-analysis.md` | You found oracle imports, `latestRoundData`, `getPrice`, TWAP calls, or price-dependent logic |
| `domains/defi/modules/vault-share-accounting.md` | You found ERC4626 inheritance, `convertToShares`, `convertToAssets`, share-based deposit/withdraw |
| `domains/defi/modules/lending-liquidation-deep.md` | You found `borrow`, `repay`, `liquidate`, health factor checks, or interest accrual |
| `domains/defi/modules/amm-mev-deep.md` | You found swap functions, liquidity provision, tick math, or pool interaction |
| `domains/defi/modules/economic-design.md` | You found fee calculations, reward distributions, liquidation logic, or tokenomics |
| `domains/defi/modules/governance-voting.md` | You found governance contracts, voting functions, delegation, or quorum logic |
| `domains/defi/modules/flash-loan-interaction.md` | You found `balanceOf(address(this))`, spot price reads, or deposit+withdraw in same-tx-capable flows |
| `domains/defi/modules/token-flow-tracing.md` | You found token transfers (virtually always selected for DeFi) |
| `domains/defi/modules/external-protocol-integration.md` | You found external protocol imports or interface calls to known DeFi protocols |
| `domains/defi/modules/cross-chain-bridge.md` | You found LayerZero, CCIP, Wormhole, Axelar, Hyperlane, or custom bridge/relayer code |
| `domains/defi/modules/multi-tx-attack.md` | You found operations that can be called in sequence within the same block |
