# CLI 标志参考

> 每个命令的每个标志，含类型、默认值和示例。

## 全局

```bash
python3 -m src.main [OPTIONS] COMMAND [ARGS]
```

无全局标志。

---

## `audit`

```bash
python3 -m src.main audit CONTRACT_PATH [OPTIONS]
```

| 标志 | 短写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `CONTRACT_PATH` | — | 路径（必填） | — | `.sol` 合约文件路径 |
| `--mode` | `-m` | 选项：`detect`、`patch`、`exploit`、`all` | `all` | 流水线运行深度 |
| `--output` | `-o` | 路径 | `None` | 保存 JSON 结果到文件 |
| `--max-patches` | — | 整数 | `2` | 最大补丁漏洞数（按严重性排序）。使用 `-1` 补丁所有 |
| `--attest` | — | 标志 | `False` | 完成后将结果链上证明（EAS Sepolia） |
| `--contract-address` | — | 字符串 | `None` | 链上证明的合约地址（`--attest` 必填） |
| `--resume` | — | 标志 | `False` | 从上次检查点恢复 |

**示例：**

```bash
# 完整审计默认（补丁前 2 个，无证明）
python3 -m src.main audit data/contracts/VulnerableBank.sol

# 仅检测
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode detect

# 修补所有漏洞
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches -1

# 审计 + 证明
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0x1234...

# 保存结果
python3 -m src.main audit data/contracts/VulnerableBank.sol -o report.json

# 恢复中断的审计
python3 -m src.main audit data/contracts/VulnerableBank.sol --resume
```

---

## `detect`

```bash
python3 -m src.main detect CONTRACT_PATH [OPTIONS]
```

| 标志 | 短写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `CONTRACT_PATH` | — | 路径（必填） | — | `.sol` 合约文件路径 |
| `--multi-expert` | `-me` | 标志 | `False` | 使用多专家分析（3 个并行 LLM 专家） |
| `--strategy` | `-s` | 选项：`ba`、`ta`、`all` | `all` | 检测策略（LLM-SmartAudit §3.2） |

**策略值：**

| 值 | 说明 |
|----|------|
| `ba` | 广泛分析 — 使用 ReAct 提示的通用漏洞扫描 |
| `ta` | 定向分析 — 并行检查特定漏洞类型 |
| `all` | BA 和 TA 均执行（默认） |

**示例：**

```bash
# 标准检测
python3 -m src.main detect data/contracts/VulnerableBank.sol

# 多专家模式
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert

# 仅定向分析
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ta

# 仅广泛分析
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ba
```

---

## `patch`

```bash
python3 -m src.main patch CONTRACT_PATH VULNERABILITY_ID
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_PATH` | 路径（必填） | `.sol` 合约文件路径 |
| `VULNERABILITY_ID` | 字符串（必填） | 检测输出中的 ID（如 `slither-0`、`mimo-1`） |

**示例：**

```bash
python3 -m src.main patch data/contracts/VulnerableBank.sol slither-0
```

---

## `exploit`

```bash
python3 -m src.main exploit CONTRACT_ADDRESS EXPLOIT_CODE_PATH
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_ADDRESS` | 字符串（必填） | 链上合约地址 |
| `EXPLOIT_CODE_PATH` | 路径（必填） | Foundry 漏洞利用测试文件路径 |

**示例：**

```bash
python3 -m src.main exploit 0x1234... tests/exploits/VulnerableBank_exploit.t.sol
```

---

## `attest`

```bash
python3 -m src.main attest CONTRACT_ADDRESS [OPTIONS]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `CONTRACT_ADDRESS` | 字符串（必填） | 证明的合约地址 |
| `--contract-path` | 路径 | 合约源码路径（省略则自动从审计历史检测） |

**示例：**

```bash
# 独立（score=10，无漏洞）
python3 -m src.main attest 0xYourContract

# 指定合约源码（先运行 detect）
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol
```

---

## `serve`

```bash
python3 -m src.main serve
```

无标志。通过 stdio 启动 MCP 服务器。

---

## `evaluate`

```bash
python3 -m src.main evaluate
```

无标志。对 `data/vulnerabilities/` 中的测试用例运行评估。

---

## 另请参阅

- [CLI 参考](../user-guide/cli.md) — 命令描述和工作流
- [配置参考](config.md) — `.env` 和 `settings.yaml`
- [快速开始](../getting-started/quickstart.md) — 常见使用模式
