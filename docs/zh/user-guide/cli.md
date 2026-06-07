# CLI 参考

> AuditAI CLI 的完整命令参考。

## 概述

所有命令通过 `python3 -m src.main <command>` 访问：

```bash
python3 -m src.main [OPTIONS] COMMAND [ARGS]
```

## 命令

### `audit`

运行完整智能合约审计（检测 → 修补 → 验证）。

```bash
python3 -m src.main audit CONTRACT_PATH [OPTIONS]
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_PATH` | 路径（必填） | `.sol` 合约文件路径 |

**选项：**

| 标志 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--mode`, `-m` | 选项：`detect`、`patch`、`exploit`、`all` | `all` | 流水线运行深度 |
| `--output`, `-o` | 路径 | `None` | 保存 JSON 结果到文件 |
| `--max-patches` | 整数 | `2` | 最大补丁漏洞数（按严重性排序）。使用 `-1` 补丁所有 |
| `--attest` | 标志 | `False` | 完成后将结果链上证明（EAS Sepolia） |
| `--contract-address` | 字符串 | `None` | 证明的合约地址（`--attest` 必填） |
| `--resume` | 标志 | `False` | 从上次检查点恢复 |

**示例：**

```bash
# 完整审计，修补前 2 个漏洞
python3 -m src.main audit data/contracts/VulnerableBank.sol

# 仅检测
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode detect

# 完整审计 + 链上证明
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0x1234...

# 修补所有漏洞
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches -1

# 保存到文件
python3 -m src.main audit data/contracts/VulnerableBank.sol -o results.json

# 恢复中断的审计
python3 -m src.main audit data/contracts/VulnerableBank.sol --resume
```

---

### `detect`

仅检测漏洞（无修补或验证）。

```bash
python3 -m src.main detect CONTRACT_PATH [OPTIONS]
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_PATH` | 路径（必填） | `.sol` 合约文件路径 |

**选项：**

| 标志 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--multi-expert`, `-me` | 标志 | `False` | 使用多专家分析（来自 forefy/.context 的 3 个并行 LLM 专家） |
| `--strategy`, `-s` | 选项：`ba`、`ta`、`all` | `all` | 检测策略：`ba` = 广泛分析，`ta` = 定向分析，`all` = 两者（LLM-SmartAudit §3.2） |

**示例：**

```bash
# 标准检测
python3 -m src.main detect data/contracts/VulnerableBank.sol

# 多专家模式
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert

# 仅定向分析（更快，检查已知漏洞类型）
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ta

# 仅广泛分析
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ba
```

---

### `patch`

为特定漏洞生成补丁。

```bash
python3 -m src.main patch CONTRACT_PATH VULNERABILITY_ID
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_PATH` | 路径（必填） | `.sol` 合约文件路径 |
| `VULNERABILITY_ID` | 字符串（必填） | 检测输出中的 ID（如 `slither-0`、`mimo-1`） |

**示例：**

```bash
# 先检测获取漏洞 ID
python3 -m src.main detect data/contracts/VulnerableBank.sol

# 然后修补特定漏洞
python3 -m src.main patch data/contracts/VulnerableBank.sol slither-0
```

---

### `exploit`

对已部署合约执行漏洞利用。

```bash
python3 -m src.main exploit CONTRACT_ADDRESS EXPLOIT_CODE_PATH
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_ADDRESS` | 字符串（必填） | 链上合约地址 |
| `EXPLOIT_CODE_PATH` | 路径（必填） | Foundry 漏洞利用测试文件路径 |

**示例：**

```bash
python3 -m src.main exploit 0x1234... tests/exploits/VulnerableBank_exploit.t.sol
```

---

### `attest`

在 EAS（Sepolia 测试网）上证明审计结果。

```bash
python3 -m src.main attest CONTRACT_ADDRESS [OPTIONS]
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_ADDRESS` | 字符串（必填） | 证明的合约地址 |

**选项：**

| 标志 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--contract-path` | 路径 | `None` | 合约源码路径（省略则自动从审计历史检测） |

**示例：**

```bash
# 独立证明（score=10，无漏洞）
python3 -m src.main attest 0xYourContract

# 指定合约源码
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol
```

如果提供 `--contract-path`，会先运行快速检测填充漏洞数据。

---

### `serve`

启动 MCP 服务器用于 IDE 和代理集成。

```bash
python3 -m src.main serve
```

通过 stdio 运行 MCP 服务器（生产传输）。详见 [MCP 集成](mcp.md)。

---

### `evaluate`

对测试用例运行评估框架。

```bash
python3 -m src.main evaluate
```

执行 `data/vulnerabilities/` 中的所有测试用例并生成摘要报告。

---

## 另请参阅

- [CLI 标志参考](../reference/cli-flags.md) — 每个标志的默认值
- [配置参考](../reference/config.md) — `.env` 和 `settings.yaml`
- [快速开始](../getting-started/quickstart.md) — 常见工作流
