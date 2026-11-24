# Cairo fuzz guide (Starknet Foundry)

Pack half of `engine/fuzz.md` for Cairo. Verified on `tests/fixtures/cairo-basic` with snforge 0.61.

**Limitation:** snforge fuzzes the arguments of one test function (`#[fuzzer]`). It has no
Foundry-style stateful invariant runner that calls random sequences of functions. Write
invariants as **property tests**: each one sets up state, performs a fixed or argument-driven
sequence of calls, then asserts the invariant. Cover call sequences by writing several tests
(or by branching on a fuzzed `selector_choice: u8`).

## Require/assert mining examples

Mine `assert(...)`, `assert!(...)` and `panic!` conditions, plus implied rules (balances sum to
supply, only the trusted L1 bridge credits balances, an upgrade needs the admin role), as
candidate invariants. Each becomes one property test.

## Test generation patterns

Tests live in `.audit/cairo/fuzz/tests/chainsec_fuzz_<topic>.cairo`. The pack's `fuzz.run` copies
the file into the project's `tests/` folder, runs `snforge test chainsec_fuzz`, and removes it.
Dev-dependencies: see `chains/cairo/poc/guide.md` step 1.

```cairo
use cairo_basic::bridge::{IBridgeDispatcher, IBridgeDispatcherTrait};
use snforge_std::{
    ContractClassTrait, DeclareResultTrait, L1HandlerTrait, declare, start_cheat_caller_address,
};
use starknet::ContractAddress;

const TRUSTED_L1_BRIDGE: felt252 = 0x1111;

fn setup() -> IBridgeDispatcher {
    let owner: ContractAddress = 0x123.try_into().unwrap();
    let class = declare("Bridge").unwrap().contract_class();
    let (bridge, _) = class.deploy(@array![owner.into(), TRUSTED_L1_BRIDGE]).unwrap();
    IBridgeDispatcher { contract_address: bridge }
}

fn deposit(bridge: ContractAddress, from: felt252, user: ContractAddress, amount: u256) {
    let payload = array![user.into(), amount.low.into(), amount.high.into()];
    L1HandlerTrait::new(bridge, selector!("deposit_from_l1")).execute(from, payload.span()).unwrap();
}

// Conservation: deposit(a) then withdraw(b <= a) leaves exactly a - b.
#[test]
#[fuzzer(runs: 64, seed: 7)]
fn chainsec_fuzz_withdraw_conserves(a: u128, b: u128) {
    let d = setup();
    let user: ContractAddress = 0x456.try_into().unwrap();
    let (a, b) = if b <= a { (a, b) } else { (b, a) };
    deposit(d.contract_address, TRUSTED_L1_BRIDGE, user, a.into());
    start_cheat_caller_address(d.contract_address, user);
    d.withdraw_to_l1(0x99, b.into());
    assert(d.balance_of(user) == a.into() - b.into(), 'balance not conserved');
}

// Access: only the trusted L1 sender may credit balances (fails on the planted bug).
#[test]
#[fuzzer(runs: 64, seed: 7)]
fn chainsec_fuzz_only_trusted_sender_credits(from: felt252, amount: u128) {
    let d = setup();
    let user: ContractAddress = 0x456.try_into().unwrap();
    if from == TRUSTED_L1_BRIDGE || amount == 0 {
        return;
    }
    deposit(d.contract_address, from, user, amount.into());
    assert(d.balance_of(user) == 0, 'untrusted L1 sender credited');
}
```

Bound inputs by type (`u128` instead of `u256`) or by early `return` for impossible cases. Do not
use `assume`-style filtering that discards most runs.

## Iterative fix loop

1. Run `fuzz.run`. A `[FAIL]` line prints the failing arguments and the decoded panic message.
2. Decide: **real violation** (the contract breaks the invariant, keep it with the arguments as the
   counterexample), **wrong invariant** (fix the property), or **harness bug** (fix setup).
3. Re-run with the same `seed` to confirm, then with a new seed and `runs: 256` for confidence.

## snforge pipeline steps

- Phase 0, recon: dev-dependencies present (scratch copy if not); `snforge test` runs once.
- Phase 2, generation: one property test per mined invariant, `#[fuzzer(runs: 64, seed: <n>)]`.
- Phase 3, run and fix: the loop above, at most 3 rounds per test.
- Phase 4, report: list each invariant as held / violated (with counterexample arguments) /
  not testable (and why), and state the stateful-sequence limitation above.
