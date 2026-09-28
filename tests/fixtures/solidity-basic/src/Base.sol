// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

abstract contract Owned {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address next) external onlyOwner {
        owner = next;
    }
}
