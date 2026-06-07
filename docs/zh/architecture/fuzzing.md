# 模糊测试与 PoC 验证

> AuditAI 如何使用 Foundry 通过不变式测试和漏洞概念验证来验证漏洞。

## 概述

检测漏洞后，AuditAI 可以使用 [Foundry](https://book.getfoundry.sh/) 进行**具体执行**验证。这产生漏洞真实可利用的硬证据，而非仅仅是理论发现。

## Foundry 集成

AuditAI 使用 Foundry 的 `forge` 进行：

1. **不变式测试** — 检查合约不变式在随机输入下是否成立
2. **漏洞 PoC 生成** — 自动生成演示漏洞的 Foundry 测试合约
3. **补丁验证** — 确认修复确实有效

## 漏洞 PoC 生成

`exploit_gen` 工具生成独立的 Foundry 测试合约：

```python
# src/tools/exploit_gen.py
exploit_code = tools.exploit_gen.generate(vulnerability, contract_code)
```

每个生成的 PoC 是一个完整的 Foundry 测试文件：

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

## 具体执行

`validator` 代理通过 Foundry 运行 PoC 测试：

```python
# src/tools/concrete_execution.py
result = tools.concrete_execution.run_test(exploit_code_path)
```

执行流程：

1. 将漏洞利用测试写入临时文件
2. 运行 `forge test --match-contract <test_name>`
3. 解析输出判断通过/失败
4. 返回结构化结果

## 流水线集成

在完整审计流水线中，验证发生在修补之后：

```
[检测] ──► 漏洞
              │
              ▼
[修补] ──► 修补后的代码
              │
              ▼
[验证] ──► Validator 运行 Foundry 测试
              │
              ├── 通过 ──► 修复确认
              └── 失败 ──► 修复被拒，重试
```

## LLM 生成的不变式

对于没有现有测试的合约，LLM 可以生成不变式测试合约：

1. 分析合约预期行为
2. 生成检查不变式的 `forge test` 合约
3. 对原始（有漏洞的）代码运行以确认 bug
4. 对修补后的代码运行以确认修复

## 独立漏洞利用执行

可以直接运行漏洞利用：

```bash
# 对已部署合约执行漏洞利用
python3 -m src.main exploit 0xContractAddress tests/exploits/VulnerableBank_exploit.t.sol
```

## 前置要求

必须安装 Foundry：

```bash
# 安装 Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# 验证
forge --version
```

## 另请参阅

- [检测层](detection.md) — 漏洞发现方式
- [架构概述](overview.md) — 完整流水线
- [CLI 参考](../user-guide/cli.md) — `exploit` 命令
