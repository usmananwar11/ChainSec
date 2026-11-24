# ChainSec Detection Primer: Starknet for EVM-Trained Auditors

> Where EVM intuition gives the wrong answer on Starknet. Each item names the heuristic in
> [heuristics.md](../heuristics.md) that holds the check.

| EVM assumption | Starknet reality | Check |
|---|---|---|
| `uint256` is the native word; checked math since 0.8 | The native type is `felt252`, which wraps modulo P with no panic and divides by modular inverse. `u8`…`u256` panic on overflow | FELT-01 to FELT-04, INT-01 |
| Explicit downcasts truncate silently | Narrowing is `try_into()` → `Option`: panic on `unwrap`, or a silent default | INT-03 |
| `uint256` is one value | `u256` is two `u128` limbs, serialized low then high, stored in two slots | U256-01, U256-02 |
| EOAs vs contracts | Every account is a contract with `__validate__`/`__execute__`; signature schemes, nonces and multicall live in account code | AA-01 to AA-04 |
| `msg.sender` / `tx.origin` | `get_caller_address()` is the immediate caller; `get_tx_info().account_contract_address` is the transaction account; protocol-invoked account entry points see caller zero | CALLER-01, CALLER-02 |
| `msg.value`, `payable`, native ETH transfers | No native value: STRK and ETH are ERC20 contracts, all value moves through dispatcher calls | DISP-01, DISP-02 |
| `try/catch`, low-level `call` returning `false` | A failing dispatcher call reverts the whole transaction; safe dispatchers return `Result`, but some failures still revert | DISP-01 |
| Proxies + `delegatecall`, ERC-1967 slots | Upgrades replace the contract's class in place (`replace_class_syscall`); `library_call` is the `delegatecall` equivalent | UPG-01 to UPG-03, LIBC-01 |
| Storage slots by declaration order; storage gaps | Slots derived from variable names; renaming moves data; no gaps needed, but names must stay stable | UPG-02, COMP-01 |
| Inheritance and modifiers | Components embedded with `component!`; guards are explicit calls (`assert_only_owner()`); embedded impls add public entry points | COMP-02, GUARD-01 |
| Missing mapping key reverts or is obviously zero | Same zero default, but Cairo code often treats it as "registered" | MAP-01 |
| `view` functions use STATICCALL | `self: @ContractState` only blocks writes through `self`; syscalls and calls out still run | fp-patterns.md FP-8 |
| EIP-712, `ecrecover` | SNIP-12 typed data (Pedersen/Poseidon, revisions); STARK-curve ECDSA via `check_ecdsa_signature` returning `bool` | SIGN-01 to SIGN-03 |
| Bridges are third-party contracts | Native L1↔L2 messaging: `#[l1_handler]` with `from_address`, `send_message_to_l1_syscall` | L1H-01, L1H-02, MSG-01 to MSG-03 |
| `CREATE2` address = deployer, salt, init code | Address = deployer (or zero), salt, class hash, constructor calldata | DEPLOY-01 |
| ~12s blocks, public mempool | ~6s blocks since v0.14.0, mempool with several sequencers; only V3 transactions | TIME-01 |
| Gas limit bounds loops | Per-transaction step limits bound loops; unbounded iteration bricks the function | UNBOUNDED-LOOP pattern |

Vulnerability classes specific to this toolchain are in [patterns/README.md](../patterns/README.md).
