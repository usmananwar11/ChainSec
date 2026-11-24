# Cairo module triggers

Triggers for the modules in `chains/cairo/modules/`. Tier hierarchy and selection rules: `domains/defi/triggers.md`.

| Module File | Tier | Trigger Condition | Select If... |
|---|---|---|---|
| `chains/cairo/modules/starknet-access-and-upgrades.md` | 0 | Always active | Always selected — every Starknet contract has entry-point access control, and most are upgradeable through `replace_class_syscall` |
| `chains/cairo/modules/component-storage.md` | 2 | Contract embeds components or customizes storage layout | You found `component!(`, `#[substorage(v0)]`, `#[abi(embed_v0)]` component impls, `#[starknet::storage_node]`, a custom `impl ... of Store<`, or `storage_address_from_base` |
| `chains/cairo/modules/felt252-arithmetic.md` | 2 | Value or index math on `felt252`, narrowing conversions, or packing | You found `felt252` arithmetic (`felt_arith` counter > 0), `felt252_div`, `try_into().unwrap()` / `.expect(` on amounts, manual `u256 { low, high }`, or bit-packing into `felt252` |
| `chains/cairo/modules/l1-l2-messaging.md` | 2 | Protocol sends or receives L1↔L2 messages | You found `#[l1_handler]`, `send_message_to_l1_syscall`, `from_address`, an L1 bridge/messaging address in storage, or `EthAddress` |
| `chains/cairo/modules/account-abstraction.md` | 2 | Protocol implements an account or delegated execution | You found `__validate__`, `__execute__`, `__validate_declare__`, `__validate_deploy__`, `is_valid_signature`, `execute_from_outside`, session keys, `AccountComponent`, or paymaster logic |
| `chains/cairo/modules/signatures-and-replay.md` | 2 | Protocol verifies off-chain signatures or uses nonces | You found `check_ecdsa_signature`, `is_valid_signature` calls into other accounts, `OffchainMessageHash` / SNIP-12 `StructHash`, `NoncesComponent`, permit flows, or signed oracle prices |

## Code evidence for domain module triggers

The Cairo code evidence for each trigger in `domains/defi/triggers.md`.

| Module | Select If... |
|---|---|
| `domains/defi/modules/access-control-state.md` | Always selected — every protocol has access control |
| `domains/defi/modules/oracle-analysis.md` | You found Pragma (`IPragmaABIDispatcher`, `get_data_median`, `DataType::SpotEntry`), Ekubo TWAP/oracle extension reads, a signed-price `set_prices` path, or price-dependent logic |
| `domains/defi/modules/vault-share-accounting.md` | You found `ERC4626Component`, `convert_to_shares` / `convert_to_assets`, `preview_deposit`, or share-based `deposit`/`withdraw`/`redeem` |
| `domains/defi/modules/lending-liquidation-deep.md` | You found `borrow`, `repay`, `liquidate`, health-factor or LTV checks, or interest accrual (Vesu, Nostra, zkLend-style code) |
| `domains/defi/modules/amm-mev-deep.md` | You found `swap`, liquidity provision, tick or sqrt-price math, or Ekubo/JediSwap/AVNU router calls |
| `domains/defi/modules/economic-design.md` | You found fee calculations (bps constants, `fee_recipient`), reward distributions, liquidation logic, or tokenomics |
| `domains/defi/modules/governance-voting.md` | You found `GovernorComponent`, `VotesComponent`, `TimelockControllerComponent`, `MultisigComponent`, voting functions, delegation, or quorum logic |
| `domains/defi/modules/flash-loan-interaction.md` | You found `balance_of(get_contract_address())`, spot price reads, flash-loan callbacks (`on_flash_loan`, Ekubo `locked`), or deposit+withdraw in same-transaction-capable flows (multicall from an account) |
| `domains/defi/modules/token-flow-tracing.md` | You found ERC20 dispatcher `transfer` / `transfer_from`, `mint`, `burn`, or own-balance reads (virtually always selected for DeFi) |
| `domains/defi/modules/external-protocol-integration.md` | You found dispatchers into known Starknet protocols (Ekubo, Vesu, Nostra, AVNU, JediSwap, Pragma, StarkGate) or their interface imports |
| `domains/defi/modules/cross-chain-bridge.md` | You found `#[l1_handler]`, `send_message_to_l1_syscall`, StarkGate, LayerZero or Hyperlane endpoints, or custom relayer code |
| `domains/defi/modules/multi-tx-attack.md` | You found operations that can be called in sequence within one transaction (account multicall) or one block |
