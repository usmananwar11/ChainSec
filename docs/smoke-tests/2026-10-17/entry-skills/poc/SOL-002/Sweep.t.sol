// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import {SOL002Test} from "./SOL002.t.sol";

contract SweepTest is SOL002Test {
    // For each ETH deposit size around the boundary, an ETH-only depositor must never extract tokens.
    function testSweepFixed() public {
        uint256[7] memory a = [uint256(0), 1, 2, 999_999, 1_000_000, 1_000_001, 5_000_000];
        for (uint256 i; i < a.length; i++) {
            address who = address(uint160(0x1000 + i));
            vm.deal(who, a[i]);
            vm.prank(who); vault.depositEth{value: a[i]}();
            for (uint256 j; j < a.length; j++) {
                if (a[j] == 0) continue;
                vm.prank(who);
                try vault.withdraw(a[j]) { revert("token extracted by ETH-only depositor"); } catch {}
            }
            require(token.balanceOf(who) == 0, "gained tokens");
        }
        require(token.balanceOf(address(vault)) == DEPOSIT, "vault token balance changed");
    }
}
