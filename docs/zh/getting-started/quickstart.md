# 快速开始

> 5 分钟内运行首次智能合约审计。

## 1. 检测漏洞（最快）

```bash
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

运行 Slither + Aderyn + LLM 分析，输出漏洞表格：

```
┌─────────────────────────────────────────┐
│       Vulnerabilities Found             │
├──────┬──────────────┬──────────┬────────┤
│ ID   │ Type         │ Severity │ Source │
├──────┼──────────────┼──────────┼────────┤
│ slither-0 │ reentrancy │ High     │ slither│
│ mimo-0    │ access_ctrl│ Critical │ mimo   │
└──────┴──────────────┴──────────┴────────┘
```

## 2. 完整审计（检测 + 修补 + 验证）

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode all
```

运行完整 5 代理流水线：

1. **检测** — Slither + Aderyn + LLM + RAG 发现漏洞
2. **修补** — Architect 设计策略，Code Generator 生成补丁，Refiner 迭代优化
3. **验证** — Validator 运行 Foundry 测试确认修复

输出为 Markdown 审计报告，包含发现、补丁和验证状态。

### 限制补丁数量

```bash
# 仅修补最严重的 2 个漏洞（默认）
python3 -m src.main audit data/contracts/VulnerableBank.sol

# 修补所有漏洞
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches -1

# 修补前 5 个
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches 5
```

### 保存报告到文件

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol -o report.json
```

## 3. 带链上证明的审计

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol \
  --attest \
  --contract-address 0xYourContract
```

审计合约并将结果发布到 EAS Sepolia。详见 [EAS 证明指南](../user-guide/attestation.md)。

## 4. 多专家分析

使用 forefy/.context 多专家框架进行更深入的分析：

```bash
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert
```

运行 3 个并行 LLM "专家" — 系统审计师、新视角审计师和分诊师验证发现。

## 理解输出

每个漏洞包含以下字段：

| 字段 | 含义 |
|------|------|
| `id` | 唯一标识符（如 `slither-0`、`mimo-1`） |
| `type` | 漏洞类别（如 `reentrancy`、`access_control`） |
| `severity` | `critical` / `high` / `medium` / `low` / `informational` |
| `confidence` | 共识分数 [0–1] — 有多少检测器家族同意 |
| `source` | 检测引擎（`slither`、`aderyn`、`mimo`、`ba`、`ta` 等） |
| `verified` | Verificator 是否确认为真阳性 |

## 下一步

- [CLI 参考](../user-guide/cli.md) — 所有命令和标志
- [MCP 集成](../user-guide/mcp.md) — 将工具暴露给 Cursor / Claude
- [架构概述](../architecture/overview.md) — 了解流水线

## 另请参阅

- [安装指南](installation.md) — 如果尚未安装
- [CLI 标志参考](../reference/cli-flags.md) — 每个标志的默认值
