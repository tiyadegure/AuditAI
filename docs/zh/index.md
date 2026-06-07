# ◆ AuditAI — 智能合约安全，重新定义

> 5 层 AI 代理，检测、验证、修补、链上证明 — 全自动完成。

## 快速链接

| | |
|---|---|
| **[🚀 快速开始](getting-started/installation.md)** | 安装 AuditAI 并运行首次审计 |
| **[📖 CLI 参考](user-guide/cli.md)** | 完整的命令和标志文档 |
| **[🏗️ 架构](architecture/overview.md)** | 5 代理流水线如何工作 |
| **[🔌 MCP 集成](user-guide/mcp.md)** | 暴露审计工具给 IDE 和代理 |
| **[🔗 EAS 证明](user-guide/attestation.md)** | 链上可验证审计凭证 |
| **[🤝 贡献](developer-guide/contributing.md)** | 帮助构建 AuditAI |

## ✨ 核心特性

- **🔍 双引擎检测** — Slither + Aderyn 静态分析 + LLM 共识评分
- **📚 2,450 个知识片段** — 477 篇真实 Solodit 审计报告 + 303 个漏洞参考文档，基于 ChromaDB 向量检索
- **🔬 Foundry 模糊测试** — 自动生成不变性测试合约，验证漏洞真实性
- **🔗 EAS 链上证明** — 审计结果发布到 Sepolia 测试网，任何人可独立验证
- **🧠 5 代理流水线** — 审计器 → 架构师 → 代码生成器 → 优化器 → 验证器，协调器统一调度
- **🔌 MCP 服务器** — 暴露审计工具给外部代理和 IDE 集成
- **🛡️ 崩溃恢复** — 每步保存检查点，使用 `--resume` 标志续跑，永不丢失进度

## 🚀 一行命令安装

```bash
pip install -r requirements.txt
```

## 🎯 运行首次审计

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode all
```

## 🛠️ 技术栈

| 层 | 技术 |
|---|------|
| **🧠 AI 模型** | MiMo V2.5 Pro |
| **🔍 静态分析** | Slither + Aderyn（双引擎共识） |
| **📚 知识库** | ChromaDB + sentence-transformers（all-MiniLM-L6-v2） |
| **🔗 链上** | EAS（Ethereum Attestation Service）Sepolia |
| **🔬 模糊测试** | Foundry（不变性测试 + 漏洞 PoC） |
| **🧠 多代理** | 5 代理流水线（审计器 / 架构师 / 代码生成器 / 优化器 / 验证器） |
| **🔌 MCP** | Python SDK — 暴露审计工具给外部消费者 |

## 📂 项目结构

```
src/
├── agents/             # 5 代理流水线
│   ├── auditor.py      # 漏洞检测（Slither + LLM + RAG）
│   ├── architect.py    # 修复策略设计
│   ├── code_generator.py   # 补丁生成
│   ├── refiner.py      # 迭代代码改进
│   ├── validator.py    # 验证 + 漏洞利用执行
│   └── orchestrator.py # 流水线协调 + 检查点恢复
├── tools/              # 领域特定工具
│   ├── slither_tool.py # Slither 静态分析封装
│   ├── aderyn_tool.py  # Aderyn 静态分析封装
│   ├── exploit_gen.py  # Foundry PoC 生成
│   └── concrete_execution.py  # Foundry 测试运行器
├── knowledge/          # RAG 知识库
│   └── knowledge_base.py      # ChromaDB + 向量搜索
├── chain/              # 链上集成
│   ├── eas_attest.py   # EAS Sepolia 证明
│   └── chain_verifier.py      # 链上验证
├── mcp/                # MCP 服务器
│   └── mcp_server.py   # Model Context Protocol 服务器
└── utils/
    ├── mimo_llm.py     # MiMo V2.5 Pro API 客户端
    └── checkpoint.py   # 崩溃恢复检查点管理器
```

## 🎮 演示

访问我们的在线演示：[audit-ai.tech](https://audit-ai.tech)

- **English**: [audit-ai.tech](https://audit-ai.tech)
- **中文**: [audit-ai.tech/index-zh.html](https://audit-ai.tech/index-zh.html)

## 📚 文档

- **English**: [docs/en/](en/)
- **中文**: [docs/zh/](zh/)
- **LLM 索引**: [llms.txt](llms.txt)

## 另请参阅

- [快速开始](getting-started/installation.md) — 安装和设置
- [架构概览](architecture/overview.md) — 5 代理流水线如何工作
- [CLI 参考](user-guide/cli.md) — 所有命令和标志
