# Cairo PoC guide (Starknet Foundry)

Pack half of `engine/poc/workflow.md` for Cairo. Framework: Starknet Foundry (`snforge`), version
0.61+. Verified on `tests/fixtures/cairo-basic` with scarb 2.18 / snforge 0.61.

## snforge workflow steps

### 1. Recon the PoC environment (MANDATORY)

- `Scarb.toml` must have `snforge_std` (matching the installed `snforge --version`) and
  `assert_macros` (matching the Cairo version) under `[dev-dependencies]`. If they are missing,
  add them in a **scratch copy** of the project, never in the user's tree:

  ```toml
  [dev-dependencies]
  snforge_std = "0.61.0"
  assert_macros = "2.18.0"

  [tool.scarb]
  allow-prebuilt-plugins = ["snforge_std"]
  ```

- The package needs `[[target.starknet-contract]]` so `declare("<ContractName>")` can find the class.
- Note the package name in `[package] name`: integration tests import the crate by that name.
- A project with existing tests: run `snforge test` once first to confirm the toolchain works.

### 2. Choose the harness: local or fork

- **Local (default):** `declare` + `deploy` the in-scope contracts with constructor calldata.
- **Fork:** for contracts already deployed, add `#[fork(url: "<rpc>", block_number: <n>)]` to the test
  and use the live address. Pin the block. Without an RPC URL, stay local.

### 3. Write the test

Tests live in `.audit/cairo/poc/<ID>/chainsec_poc_<id>.cairo` (lower-case id). The pack's
`poc.run` copies the file into the project's `tests/` folder, runs `snforge test chainsec_poc_<id>`
and removes it again. Each test function name starts with `chainsec_poc_<id>`.

Verified skeleton (planted bug: an `l1_handler` that does not check `from_address`):

```cairo
use cairo_basic::bridge::{IBridgeDispatcher, IBridgeDispatcherTrait};
use snforge_std::{ContractClassTrait, DeclareResultTrait, L1HandlerTrait, declare};
use starknet::ContractAddress;

const TRUSTED_L1_BRIDGE: felt252 = 0x1111;
const ATTACKER_L1: felt252 = 0xbad;

#[test]
fn chainsec_poc_cairo_001() {
    let owner: ContractAddress = 0x123.try_into().unwrap();
    let user: ContractAddress = 0x456.try_into().unwrap();
    let class = declare("Bridge").unwrap().contract_class();
    let (bridge, _) = class.deploy(@array![owner.into(), TRUSTED_L1_BRIDGE]).unwrap();
    let d = IBridgeDispatcher { contract_address: bridge };

    let amount: u256 = 1_000_000_000_000_000_000_000;
    let payload = array![user.into(), amount.low.into(), amount.high.into()];
    L1HandlerTrait::new(bridge, selector!("deposit_from_l1")).execute(ATTACKER_L1, payload.span()).unwrap();

    // HARM: unbacked balance minted from an untrusted L1 sender.
    assert(d.balance_of(user) == amount, 'unbacked balance not minted');
}
```

### 4. Cheatcodes real PoCs use

| Need | snforge_std |
|---|---|
| Call as another account | `start_cheat_caller_address(target, addr)` / `stop_cheat_caller_address(target)` |
| Move time / blocks | `start_cheat_block_timestamp(target, ts)`, `start_cheat_block_number(target, n)` |
| Deliver an L1 message | `L1HandlerTrait::new(addr, selector!("fn")).execute(from_address, payload)` |
| Expect a revert | `#[should_panic(expected: 'msg')]` on the test, or a `Safe` dispatcher returning `Result` |
| Read/write raw storage | `load(target, selector!("var"), size)` / `store(target, selector!("var"), values)` |
| Spy on events | `spy_events()` + `assert_emitted` |
| Mock an external call | `start_mock_call(target, selector!("fn"), ret)` |
| Signatures | `snforge_std::signature::{KeyPairTrait, stark_curve::StarkCurveKeyPairImpl}` |

`u256` calldata is two felts (`low`, `high`); `ContractAddress` and `ClassHash` convert with
`.into()` / `.try_into().unwrap()`.

### 5. Assert the HARM, not the mechanism

Follow `engine/poc/assertion-protocol.md`: assert balances moved, supply inflated, a call that must
succeed now panics, or an invariant broken. "The function did not revert" is not harm.

### 6. Compile → run → fix

| Error | Fix |
|---|---|
| `Identifier not found` on `snforge_std` items | dev-dependency missing or version differs from `snforge --version` |
| `Contract not found` from `declare` | missing `[[target.starknet-contract]]`, or wrong contract module name |
| Plugin / macro errors on `#[test]` | `assert_macros` or `allow-prebuilt-plugins` missing; versions must match the toolchain |
| `ENTRYPOINT_NOT_FOUND` | wrong selector name, or the function is not in an `#[abi(embed_v0)]` impl |
| `Option::unwrap failed` on address | literal too large for `ContractAddress`; use a smaller felt |
| Panic data shown as hex | decode short strings: the hex is ASCII of the panic message |

After 5 failed compiles, stop and keep the finding at `[CODE-TRACE]` (see `engine/poc/workflow.md`).
