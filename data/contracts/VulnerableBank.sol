// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title VulnerableBank
 * @notice Example contract with intentional vulnerabilities for testing
 * @dev DO NOT use in production - for AuditAI testing only
 */
contract VulnerableBank {
    mapping(address => uint256) public balances;
    address public owner;
    bool private initialized;

    // Vulnerability: No constructor access control
    function initialize() external {
        if (!initialized) {
            owner = msg.sender;
            initialized = true;
        }
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerability: Reentrancy
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Bug: State update after external call
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        balances[msg.sender] -= amount;
    }

    // Vulnerability: Integer overflow (in older Solidity)
    function transfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }

    // Vulnerability: Unchecked return value
    function unsafeTransfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        // Ignoring return value
        payable(to).transfer(amount);
    }

    // Vulnerability: tx.origin authentication
    function setOwner(address newOwner) external {
        require(tx.origin == owner, "Not owner");
        owner = newOwner;
    }

    // Vulnerability: Denial of Service with unbounded loop
    function airdrop(address[] calldata recipients, uint256 amount) external {
        for (uint256 i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += amount;
        }
    }

    // Vulnerability: Front-running susceptible
    function claimReward(uint256 amount) external {
        require(balances[msg.sender] > 0, "No balance");
        // Attacker can see this and front-run
        balances[msg.sender] += amount;
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
