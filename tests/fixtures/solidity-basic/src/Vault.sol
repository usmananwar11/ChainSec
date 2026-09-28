// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Owned} from "./Base.sol";

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract Vault is Owned {
    IERC20 public immutable token;
    mapping(address => uint256) public balances;
    uint256 public totalDeposits;
    uint256 public constant FEE_BPS = 30;

    constructor(IERC20 token_) {
        token = token_;
    }

    function deposit(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        balances[msg.sender] += amount;
        totalDeposits += amount;
    }

    function depositEth() external payable {
        balances[msg.sender] += msg.value;
    }

    // BUG (planted for smoke tests): no access control, anyone can drain the native balance.
    function sweep(address payable to) external {
        to.transfer(address(this).balance);
    }

    function withdraw(uint256 amount) external {
        balances[msg.sender] -= amount;
        unchecked {
            totalDeposits -= amount;
        }
        token.transfer(msg.sender, amount);
    }

    function setFee(uint256) external onlyOwner {}

    function balanceOf(address who) external view returns (uint256) {
        return balances[who];
    }

    function _selfBalance() internal view returns (uint256 b) {
        assembly {
            b := selfbalance()
        }
    }
}
