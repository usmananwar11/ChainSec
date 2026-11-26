# Soroban module triggers

Triggers for the modules in `chains/soroban/modules/`. Tier hierarchy and selection rules: `domains/defi/triggers.md`.

| Module File | Tier | Trigger Condition | Select If... |
|---|---|---|---|
| `chains/soroban/modules/soroban-auth.md` | 0 | Always active | Always selected — every contract has `require_auth` decisions |
| `chains/soroban/modules/storage-and-ttl.md` | 0 | Always active | Always selected — every contract stores data with a TTL |
| `chains/soroban/modules/upgrades-and-init.md` | 2 | Contract can replace its code or has an init path | You found `update_current_contract_wasm` (counter `upgrades` > 0) or `update_current_contract`, `initialize`, `__constructor`, or migration functions (`migrate`, `upgrade`, a stored schema version) |
| `chains/soroban/modules/token-integration.md` | 2 | Contract moves or accepts tokens | You found `token::Client`, `TokenClient`, `StellarAssetClient`, SEP-41 implementations, `transfer_from`, or counter `token_transfers` > 0 |
| `chains/soroban/modules/cross-contract-calls.md` | 2 | Contract calls other contracts | You found `*Client::new` on non-token contracts, `invoke_contract`, `try_invoke_contract`, or `contractimport!` |
| `chains/soroban/modules/resource-limits.md` | 2 | Loops or batches over growable data | You found loops over storage `Vec` / `Map`, per-user lists in one entry, or batch entry points taking a `Vec` argument |

## Code evidence for domain module triggers

The Soroban code evidence for each trigger in `domains/defi/triggers.md`.

| Module | Select If... |
|---|---|
| `domains/defi/modules/access-control-state.md` | Always selected — every protocol has access control |
| `domains/defi/modules/oracle-analysis.md` | You found Reflector oracle reads (`lastprice`, `price`, SEP-40 client or `contractimport!` of an oracle), a stored oracle address, or price-dependent logic |
| `domains/defi/modules/vault-share-accounting.md` | You found share-based `deposit` / `withdraw` / `redeem` with `total_shares` and `total_assets` accounting, or `convert_to_shares` / `convert_to_assets` style math |
| `domains/defi/modules/lending-liquidation-deep.md` | You found borrow, repay, liquidate, health-factor or collateral-factor checks, interest accrual, or Blend-style `submit` with a list of requests |
| `domains/defi/modules/amm-mev-deep.md` | You found swap, liquidity provision, reserves or constant-product math, or Soroswap router and pair calls |
| `domains/defi/modules/economic-design.md` | You found fee calculations (bps constants, a fee recipient), reward distributions, liquidation logic, or tokenomics |
| `domains/defi/modules/governance-voting.md` | You found proposals, voting, delegation, quorum, or timelock logic |
| `domains/defi/modules/flash-loan-interaction.md` | You found the contract reading its own token balance (`balance(&env.current_contract_address())`), spot-reserve prices, flash-loan callbacks, or deposit and withdraw in the same invocation |
| `domains/defi/modules/token-flow-tracing.md` | You found token `transfer` / `transfer_from`, `mint`, `burn`, or own-balance reads (virtually always selected for DeFi) |
| `domains/defi/modules/external-protocol-integration.md` | You found clients or `contractimport!` of known Stellar protocols (Blend, Soroswap, Reflector, Aquarius, Phoenix, Allbridge) or their interface crates |
| `domains/defi/modules/cross-chain-bridge.md` | You found Allbridge or LayerZero endpoint calls, bridged-asset mint and burn paths, or custom relayer code with signature verification |
| `domains/defi/modules/multi-tx-attack.md` | You found operations that can be called in sequence within one transaction (several invocations in one transaction, a contract account batching calls) or one ledger |
