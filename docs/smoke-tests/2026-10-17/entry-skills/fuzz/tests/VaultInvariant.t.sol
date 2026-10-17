// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Vault, IERC20} from "src/Vault.sol";

interface Vm {
    function prank(address) external;
    function deal(address, uint256) external;
    function expectRevert() external;
}

contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 a) external { balanceOf[to] += a; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s] = a; return true; }
    function transfer(address to, uint256 a) external returns (bool) {
        balanceOf[msg.sender] -= a; balanceOf[to] += a; return true;
    }
    function transferFrom(address f, address t, uint256 a) external returns (bool) {
        allowance[f][msg.sender] -= a; balanceOf[f] -= a; balanceOf[t] += a; return true;
    }
}

contract VaultHandler {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    Vault public vault;
    MockERC20 public token;

    address[3] public actors = [address(0xA11CE), address(0xB0B), address(0xCA401)];
    address public ghostOwner;
    uint256 public ghostTokenDeposited;
    uint256 public ghostEthCredited;

    constructor(Vault v, MockERC20 t) {
        vault = v;
        token = t;
        ghostOwner = v.owner();
        for (uint256 i; i < 3; i++) {
            vm.prank(actors[i]);
            t.approve(address(v), type(uint256).max);
        }
    }

    function _actor(uint256 s) internal view returns (address) { return actors[s % 3]; }
    function _bound(uint256 x, uint256 lo, uint256 hi) internal pure returns (uint256) {
        return lo + (x % (hi - lo + 1));
    }
    function actorsLength() external pure returns (uint256) { return 3; }

    function deposit(uint256 seed, uint256 amount) external {
        address a = _actor(seed);
        amount = _bound(amount, 1, 1e24);
        token.mint(a, amount);
        vm.prank(a);
        vault.deposit(amount);
        ghostTokenDeposited += amount;
    }

    function depositEth(uint256 seed, uint256 amount) external {
        address a = _actor(seed);
        amount = _bound(amount, 1, 1e21);
        vm.deal(a, amount);
        vm.prank(a);
        vault.depositEth{value: amount}();
        ghostEthCredited += amount;
    }

    function withdraw(uint256 seed, uint256 amount) external {
        address a = _actor(seed);
        uint256 max = vault.balances(a);
        if (max == 0) return;
        amount = _bound(amount, 1, max);
        if (token.balanceOf(address(vault)) < amount) return; // would revert in token; not a ledger issue
        vm.prank(a);
        vault.withdraw(amount);
    }

    function sweep(uint256 seed, uint256 toSeed) external {
        address a = _actor(seed);
        address payable to = payable(address(uint160(0xDEAD0000 + (toSeed % 5))));
        vm.prank(a);
        vault.sweep(to);
    }

    function transferOwnership(uint256 seed, address next) external {
        address a = _actor(seed);
        vm.prank(a);
        try vault.transferOwnership(next) { ghostOwner = next; } catch {}
    }
}

contract InvariantTest_Vault {
    Vault vault;
    MockERC20 token;
    VaultHandler handler;

    // Foundry invariant config hooks
    function setUp() public {
        token = new MockERC20();
        vault = new Vault(IERC20(address(token)));
        handler = new VaultHandler(vault, token);
    }

    function targetContracts() public view returns (address[] memory a) {
        a = new address[](1);
        a[0] = address(handler);
    }

    function _sumBalances() internal view returns (uint256 s) {
        for (uint256 i; i < 3; i++) s += vault.balances(handler.actors(i));
    }

    function invariant_INV001_tokenBalanceCoversTotalDeposits() public view {
        require(token.balanceOf(address(vault)) >= vault.totalDeposits(), "INV-001: token balance < totalDeposits");
    }

    function invariant_INV002_totalDepositsNoWrap() public view {
        require(vault.totalDeposits() <= handler.ghostTokenDeposited(), "INV-002: totalDeposits wrapped/exceeds deposits");
    }

    function invariant_INV003_ledgerBackedByAssets() public view {
        require(
            _sumBalances() <= token.balanceOf(address(vault)) + address(vault).balance,
            "INV-003: ledger exceeds assets held"
        );
    }

    function invariant_INV004_ledgerMatchesDeposits() public view {
        require(
            _sumBalances() <= vault.totalDeposits() + handler.ghostEthCredited(),
            "INV-004: ledger exceeds totalDeposits + ETH credited"
        );
    }

    function invariant_INV005_ethBalanceCoversCredits() public view {
        require(address(vault).balance >= handler.ghostEthCredited(), "INV-005: ETH balance < ETH credited (sweep)");
    }

    function invariant_INV006_ownerOnlyViaOwner() public view {
        require(vault.owner() == handler.ghostOwner(), "INV-006: owner changed without owner call");
    }

    function invariant_INV009_balanceRedeemableInTokens() public view {
        for (uint256 i; i < 3; i++) {
            require(
                vault.balances(handler.actors(i)) <= token.balanceOf(address(vault)),
                "INV-009: user ledger balance not redeemable (token balance too low)"
            );
        }
    }

    function invariant_INV010_feeBound() public view {
        require(vault.FEE_BPS() <= 10_000, "INV-010: fee > 100%");
    }
}
