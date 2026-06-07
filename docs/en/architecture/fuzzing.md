# Fuzzing & PoC Verification

> How AuditAI uses Foundry to verify vulnerabilities with invariant tests and exploit proof-of-concepts.

## Overview

After detecting vulnerabilities, AuditAI can verify them with **concrete execution** using [Foundry](https://book.getfoundry.sh/). This produces hard evidence that a vulnerability is real and exploitable, not just a theoretical finding.

## Foundry Integration

AuditAI uses Foundry's `forge` for:

1. **Invariant testing** — check that contract invariants hold under random inputs
2. **Exploit PoC generation** — auto-generate Foundry test contracts that demonstrate the vulnerability
3. **Patch verification** — confirm that fixes actually work

## Exploit PoC Generation

The `exploit_gen` tool generates self-contained Foundry test contracts:

```python
# src/tools/exploit_gen.py
exploit_code = tools.exploit_gen.generate(vulnerability, contract_code)
```

Each generated PoC is a complete Foundry test file:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Test.sol";
import "../src/VulnerableBank.sol";

contract VulnerableBankExploitTest is Test {
    VulnerableBank bank;
    address attacker = address(0xBEEF);

    function setUp() public {
        bank = new VulnerableBank();
        // fund the bank
        vm.deal(address(this), 10 ether);
        bank.deposit{value: 1 ether}();
    }

    function testReentrancy() public {
        vm.startPrank(attacker);
        vm.deal(attacker, 1 ether);
        // exploit: deposit and re-enter via fallback
        bank.deposit{value: 1 ether}();
        // verify: attacker drained the bank
        assertGt(attacker.balance, 1 ether);
        vm.stopPrank();
    }
}
```

## Concrete Execution

The `validator` agent runs PoC tests via Foundry:

```python
# src/tools/concrete_execution.py
result = tools.concrete_execution.run_test(exploit_code_path)
```

Execution flow:

1. Write the exploit test to a temporary file
2. Run `forge test --match-contract <test_name>`
3. Parse the output for pass/fail
4. Return structured result

## Pipeline Integration

In the full audit pipeline, verification happens after patching:

```
[Detect] ──► vulnerabilities
                │
                ▼
[Patch] ──► patched code
                │
                ▼
[Verify] ──► Validator runs Foundry tests
                │
                ├── PASS ──► fix confirmed
                └── FAIL ──► fix rejected, try again
```

## LLM-Generated Invariants

For contracts without existing tests, the LLM can generate invariant test contracts:

1. Analyze the contract's intended behavior
2. Generate `forge test` contracts that check invariants
3. Run them against the original (vulnerable) code to confirm the bug
4. Run against the patched code to confirm the fix

## Standalone Exploit Execution

You can run exploits directly:

```bash
# Execute an exploit against a deployed contract
python3 -m src.main exploit 0xContractAddress tests/exploits/VulnerableBank_exploit.t.sol
```

## Prerequisites

Foundry must be installed:

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Verify
forge --version
```

## See Also

- [Detection Layer](detection.md) — how vulnerabilities are found
- [Architecture Overview](overview.md) — full pipeline
- [CLI Reference](../user-guide/cli.md) — `exploit` command
