# 架构概述

> 5 层、5 代理流水线，实现自主智能合约安全审计。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI / MCP Server                            │
│  audit · detect · patch · exploit · attest · serve · evaluate   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │   Orchestrator   │
                  │  (coordinates    │
                  │   all agents)    │
                  └───┬──┬──┬──┬──┬┘
                      │  │  │  │  │
         ┌────────────┘  │  │  └────────────┐
         ▼               ▼  │               ▼
    ┌─────────┐   ┌─────────┐        ┌─────────┐
    │Auditor  │   │Architect│        │Validator│
    │detect   │   │design   │        │verify   │
    └────┬────┘   └────┬────┘        └────┬────┘
         │             │                   │
         ▼             ▼                   ▼
    ┌─────────┐  ┌──────────┐      ┌──────────────┐
    │Slither  │  │  Code    │      │  Concrete    │
    │Aderyn   │  │Generator │      │  Execution   │
    │RAG KB   │  │  patch   │      │  (Foundry)   │
    │MiMo BA  │  └────┬─────┘      └──────┬───────┘
    │MiMo TA  │       ▼                   │
    └─────────┘  ┌─────────┐              ▼
                 │Refiner  │       ┌──────────────┐
                 │improve  │       │ EAS Sepolia  │
                 └─────────┘       │ On-Chain     │
                                   │ Attestation  │
                                   └──────────────┘
```

## 五层架构

### 第 1 层：检测

**代理：** Auditor
**工具：** Slither、Aderyn、MiMo LLM、RAG 知识库

并行运行多个检测引擎：
- **Slither** — Solidity 静态分析
- **Aderyn** — Rust 静态分析
- **MiMo LLM** — AI 代码分析（广泛分析 + 定向分析）
- **RAG** — 2,450 个知识块的向量搜索

结果合并、去重，并通过共识评分（多少引擎同意）。

### 第 2 层：策略

**代理：** Architect
**输入：** 漏洞 + 合约代码
**输出：** 修补策略

为每个漏洞设计修补方案 — 应用什么模式、修改什么、保留什么不变式。

### 第 3 层：生成

**代理：** Code Generator、Refiner
**输入：** 策略 + 合约代码
**输出：** 修补后的 Solidity 代码

Code Generator 生成初始补丁。Refiner 迭代优化质量和正确性。

### 第 4 层：验证

**代理：** Validator
**工具：** Foundry（具体执行）

通过 Foundry 不变式测试和漏洞 PoC 运行修补后的代码，验证修复有效且不引入新问题。

### 第 5 层：证明

**工具：** EAS Sepolia
**输入：** 审计评分、漏洞数量、合约地址
**输出：** 链上证明交易

将审计结果发布到 Ethereum Attestation Service，生成公开可验证的凭证。

## 数据流

```
.sol 文件
   │
   ▼
[检测] ─── Slither ──┐
             Aderyn ────┤
             MiMo BA ───┼──► 合并 ──► 共识评分
             MiMo TA ───┤
             RAG KB ────┘
              │
              ▼
       vulnerabilities (list[dict])
              │
              ▼
[策略] ── Architect ──► 修补策略
              │
              ▼
[生成] ── CodeGen ──► Refiner ──► 补丁
              │
              ▼
[验证] ── Validator (Foundry) ──► 通过/失败
              │
              ▼
[证明] ── EAS Sepolia ──► 交易哈希
              │
              ▼
       AuditResult (JSON + 控制台)
```

## 检查点与恢复

长时间运行的审计可以中断并恢复：

```bash
# 首次运行（被中断）
python3 -m src.main audit data/contracts/VulnerableBank.sol

# 从上次检查点恢复
python3 -m src.main audit data/contracts/VulnerableBank.sol --resume
```

编排器在每个阶段（`detect`、`patch`、`verify`）后保存检查点，可以从最后完成的步骤恢复。

## 另请参阅

- [检测层](detection.md) — Slither、Aderyn、LLM、RAG 详情
- [知识层](knowledge.md) — ChromaDB 和 RAG 流水线
- [模糊测试与 PoC](fuzzing.md) — Foundry 不变式测试
- [链层](chain.md) — EAS 证明内部原理
