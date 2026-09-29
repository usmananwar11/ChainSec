# Solidity fuzz guide (Foundry invariants)

Follow engine/fuzz.md for invariant extraction; this file supplies the Foundry test patterns.

## Require/assert mining examples

For `engine/fuzz.md` Step 2 (verbatim from Krait's fuzzer):

```solidity
require(balances[msg.sender] >= amount, "insufficient");  // INV: balance >= withdrawal
assert(totalSupply == _computeTotal());                     // INV: supply consistency
```

## Test Generation Patterns

### Basic Invariant Test

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import {Vault} from "../src/Vault.sol";

contract InvariantTest_Vault is Test {
    Vault vault;

    function setUp() public {
        vault = new Vault();
        targetContract(address(vault));
    }

    function invariant_totalDepositsSolvent() public view {
        assertGe(
            address(vault).balance,
            vault.totalDeposits(),
            "INV-001: vault balance must cover total deposits"
        );
    }
}
```

### Handler Pattern (for bounded inputs)

```solidity
contract VaultHandler is Test {
    Vault vault;
    IERC20 token;

    constructor(Vault _vault, IERC20 _token) {
        vault = _vault;
        token = _token;
    }

    function deposit(uint256 amount) public {
        amount = bound(amount, 1, 1e24);
        deal(address(token), address(this), amount);
        token.approve(address(vault), amount);
        vault.deposit(amount);
    }

    function withdraw(uint256 amount) public {
        uint256 max = vault.balanceOf(address(this));
        if (max == 0) return;
        amount = bound(amount, 1, max);
        vault.withdraw(amount);
    }
}

contract InvariantTest_Vault is Test {
    Vault vault;
    VaultHandler handler;

    function setUp() public {
        vault = new Vault(address(token));
        handler = new VaultHandler(vault, token);
        targetContract(address(handler));
    }

    function invariant_conservesTokens() public view {
        assertEq(
            token.balanceOf(address(vault)),
            vault.totalDeposits(),
            "INV-002: vault token balance == totalDeposits"
        );
    }
}
```

### Multi-Contract Invariant Test

```solidity
contract InvariantTest_Protocol is Test {
    Router router;
    Vault vault;
    Oracle oracle;

    function setUp() public {
        oracle = new Oracle();
        vault = new Vault(address(oracle));
        router = new Router(address(vault));
        targetContract(address(router));
    }

    function invariant_debtBelowCollateral() public view {
        for (uint i = 0; i < vault.userCount(); i++) {
            address user = vault.userAt(i);
            uint256 debt = vault.debt(user);
            uint256 collateral = vault.collateral(user);
            uint256 price = oracle.getPrice();
            assertLe(
                debt,
                collateral * price / 1e18,
                "INV-003: debt must not exceed collateral value"
            );
        }
    }
}
```

## Iterative Fix Loop

When a test fails, follow this decision tree:

1. **Compilation error?**
   - Check import paths against `remappings.txt`
   - Check constructor arguments match source
   - Check Solidity version compatibility
   - Fix and re-run

2. **setUp() reverts?**
   - Check deployment order (deploy dependencies first)
   - Check constructor arguments
   - Check initialization calls (e.g., `initialize()` for proxies)
   - Check permissions (does setUp need to grant roles?)
   - Fix and re-run

3. **Invariant assertion fails?**
   - Read the counterexample/call sequence
   - Ask: "Is this call sequence possible in production?"
   - If the fuzzer is calling functions in impossible combinations → add `targetSelector()` restrictions or handler bounds
   - If the call sequence is legitimate → **REAL VIOLATION** — report it

4. **Max iterations reached?**
   - Mark as INCONCLUSIVE
   - Document what went wrong
   - The user may need to manually inspect

## Forge pipeline steps

From Krait's fuzz command: the Foundry-specific steps of each phase.

### Phase 0: RECON (Foundry steps)

**Key steps**:
1. Create `.audit/` and `.audit/solidity/fuzz/tests/` directories
5. Identify the Foundry setup: `foundry.toml`, `remappings.txt`, compiler version

### Phase 2: TEST GENERATION

**Goal**: Generate Foundry invariant test contracts.

Use Foundry's invariant testing pattern:
- `function invariant_xxx() public view` — checked after random call sequences
- `setUp()` — deploy and initialize all contracts
- `targetContract()` / `targetSelector()` — configure what Foundry calls randomly
- Handler pattern for complex protocols

**Rules**:
- Use correct import paths from the project's `remappings.txt` / `foundry.toml`
- Deploy dependencies in the right order in setUp()
- Use `bound()` not `vm.assume()` for input constraints
- Use `deal()` for initial token balances
- Include the invariant ID in assertion messages

**Output**: Write `.t.sol` files to `.audit/solidity/fuzz/tests/`

### Phase 3: RUN & FIX LOOP

**Goal**: Run the tests and iteratively fix issues.

For each test file:
1. Run `forge test --match-path <file> --fuzz-runs 1000 -vvv`
2. If all tests pass → invariants HOLD
3. If tests fail, classify the failure:
   - **Compile error**: Fix syntax/imports/types
   - **Import error**: Fix import paths using project remappings
   - **setUp() bug**: Fix deployment/initialization sequence
   - **Assertion bug**: Fix the assertion to match the invariant
   - **Real violation**: The invariant is truly broken — this is a finding
4. If test bug: fix and re-run (up to 3 iterations)
5. If real violation: record as VIOLATED with counterexample
6. If can't resolve: record as INCONCLUSIVE

### Phase 4: REPORT

**Goal**: Generate the invariant fuzzing report.

**Output**: `.audit/solidity/fuzz/report.md`
