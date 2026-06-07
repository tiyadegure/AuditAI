# 检测层

> AuditAI 如何通过双静态分析、LLM 推理和 RAG 知识发现漏洞。

## 概述

检测层并行运行多个分析引擎，合并结果，并通过共识对每个发现评分。这产生高置信度、低误报的漏洞报告。

## 检测引擎

### Slither

[Slither](https://github.com/crytic/slither) 是 Trail of Bits 的 Solidity 静态分析框架。AuditAI 通过 `src/tools/slither_tool.py` 封装。

```python
results = self.tools.slither.analyze(contract_path)
```

**输出：** 包含 `check`、`impact`、`location`、`description` 的发现列表。

### Aderyn

[Aderyn](https://github.com/Cyfrin/aderyn) 是基于 Rust 的 Solidity 静态分析器。AuditAI 通过 `src/tools/aderyn_tool.py` 封装。

```python
results = self.tools.aderyn.analyze(contract_path)
```

**输出：** 与 Slither 格式相同 — 合并到静态分析桶中。

### MiMo LLM 分析

主 AI 引擎使用 **MiMo V2.5 Pro** 进行代码分析：

```python
result = await self.llm.analyze_code(contract_code)
```

LLM 接收合约源码，返回 JSON 漏洞列表。

### 广泛分析 (BA)

ReAct 风格提示，要求 LLM 逐步推理整个合约：

```
You are a Smart Contract Auditor performing Broad Analysis (BA).
Use thought-reasoning: analyse the code step-by-step, identify potential issues,
cross-check with known vulnerability patterns, and verify your reasoning.
```

检查**通用漏洞** — 重入、访问控制、算术问题等。

### 定向分析 (TA)

对每个已知漏洞类型**并行发送一个提示**：

```python
_TA_VULN_TYPES = [
    "reentrancy",
    "access_control",
    "integer_overflow",
    "front_running",
    "oracle_manipulation",
    "flash_loan_attack",
]
```

每个提示专门检查一个漏洞类别。如果合约不受影响，返回空列表。

### 多专家分析

来自 forefy/.context 框架的 3 个并行 LLM "专家"：

1. **专家 1** — 系统、方法论，专注核心漏洞（重入、访问控制、算术）
2. **专家 2** — 新视角，经济视角（闪电贷、可组合性、预言机操纵）
3. **分诊师** — 验证和挑战发现，过滤误报

```bash
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert
```

## RAG 知识检索

Auditor 为每个合约查询知识库，查找相关漏洞模式：

```python
rag_context = await self.knowledge.query(contract_code)
```

RAG 上下文用于：
- **合并** — 用已知模式丰富发现
- **Verificator** — 根据已知漏洞文档核实发现
- **报告** — 为每个发现标记参考的 RAG 来源

## 结果合并

来自所有引擎的发现按 `(type, location)` 键合并：

```python
def _merge_results(self, slither_results, llm_results, rag_context):
    merged = {}
    for vuln in slither_results:
        key = f"{vuln['type']}-{vuln['location']}"
        if key not in merged:
            merged[key] = vuln
    for vuln in llm_results:
        key = f"{vuln['type']}-{vuln['location']}"
        merged[key] = vuln  # LLM 优先于静态分析
    return list(merged.values())
```

对于相同键，LLM 结果优先于静态分析结果。

## 共识评分

每个发现根据有多少独立检测器家族标记它来评分：

```python
_DETECTOR_FAMILIES = ("slither", "aderyn", "mimo", "ba", "ta", "expert1", "expert2", "triager")

# confidence = 同意的家族数 / 总家族数
v["confidence"] = round(len(agree) / len(self._DETECTOR_FAMILIES), 3)
```

被 8 个家族中 3 个标记的发现，`confidence = 0.375`。

## Verificator（误报消除）

最终 LLM 通道根据 RAG 知识核实每个发现：

```
You are a Smart Contract Vulnerability Verificator.
Your job is to fact-check a reported vulnerability finding against known vulnerability patterns
and the actual contract code.
```

- 仅在明确 "false positive" 判定时将发现标记为 `verified: False`
- 保守策略：模糊响应保持发现为已验证
- 并发限制为 5，避免压垮 LLM

## 流水线摘要

```
contract.sol
    │
    ├──► Slither ──────────────┐
    ├──► Aderyn ───────────────┤
    ├──► MiMo LLM ────────────┼──► 合并 ──► 共识评分 ──► Verificator
    ├──► 广泛分析 (BA) ─────────┤
    ├──► 定向分析 ──────────────┤
    └──► RAG 知识库 ────────────┘
                                  │
                                  ▼
                          vulnerabilities[]
```

## 另请参阅

- [知识层](knowledge.md) — RAG 流水线详情
- [架构概述](overview.md) — 完整流水线
- [CLI 参考](../user-guide/cli.md) — `detect` 和 `--strategy` 标志
