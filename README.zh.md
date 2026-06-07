# AuditAI — 智能合约安全，重新定义

> 5 层 AI 代理，检测、验证、修补、链上证明 — 全自动完成。

🌐 **在线演示**: [audit-ai.tech](https://audit-ai.tech) (English | 中文)

## ✨ 核心特性

- **双引擎检测** — Slither + Aderyn 静态分析 + LLM 共识评分（8 个检测器家族）
- **2,450 个知识片段** — 477 篇真实 Solodit 审计报告 + 303 个漏洞参考文档，基于 ChromaDB 向量检索
- **Foundry 模糊测试** — 自动生成不变性测试合约，验证漏洞真实性
- **漏洞 PoC 生成** — 自动生成可执行的漏洞利用代码，双向验证
- **EAS 链上证明** — 审计结果发布到 Sepolia 测试网，任何人可独立验证
- **5 代理流水线** — Auditor → Architect → CodeGenerator → Refiner → Validator，协调器统一调度
- **MCP 服务器** — 暴露审计工具给外部代理和 IDE 集成

## 🏗 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI / MCP 服务器                            │
│  audit · detect · patch · exploit · attest · serve · evaluate   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │    协调器       │
                  └───┬──┬──┬──┬──┬┘
                      │  │  │  │  │
         ┌────────────┘  │  │  │  └────────────┐
         ▼               ▼  │  ▼               ▼
    ┌─────────┐   ┌─────────┐ ┌─────────┐  ┌─────────┐
    │审计器   │   │架构师   │ │优化器   │  │验证器   │
    │检测     │   │设计     │ │改进     │  │验证     │
    └────┬────┘   └────┬────┘ └────┬────┘  └────┬────┘
         │             │           │             │
         ▼             ▼           │             ▼
    ┌─────────┐  ┌──────────┐     │     ┌──────────────┐
    │Slither  │  │  代码    │     │     │  具体执行    │
    │Aderyn   │  │ 生成器   │─────┘     │  (Foundry)   │
    │RAG 知识 │  │  补丁    │           │              │
    └─────────┘  └──────────┘           └──────────────┘
                                                │
                                         ┌──────▼──────┐
                                         │ EAS Sepolia  │
                                         │ 链上证明     │
                                         └─────────────┘
```

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 MIMO_API_KEY

# 3. 运行完整审计
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode all

# 4. 仅检测（最快）
python3 -m src.main detect data/contracts/VulnerableBank.sol

# 5. 审计 + 链上证明
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0x...

# 6. 启动 MCP 服务器（用于 IDE / 代理集成）
python3 -m src.main serve
```

## 🛠 技术栈

| 层 | 技术 |
|---|------|
| **AI 模型** | MiMo V2.5 Pro |
| **静态分析** | Slither + Aderyn (双引擎共识) |
| **知识库** | ChromaDB + sentence-transformers (all-MiniLM-L6-v2) |
| **链上** | EAS (Ethereum Attestation Service) Sepolia |
| **模糊测试** | Foundry (不变性测试 + 漏洞 PoC) |
| **多代理** | 5 代理流水线 (审计器 / 架构师 / 代码生成器 / 优化器 / 验证器) |
| **MCP** | Python SDK — 暴露审计工具给外部消费者 |

## 📂 项目结构

```
src/
├── agents/             # 5 代理流水线
│   ├── auditor.py      # 漏洞检测 (Slither + LLM + RAG)
│   ├── architect.py    # 修复策略设计
│   ├── code_generator.py   # 补丁生成
│   ├── refiner.py      # 迭代代码改进
│   ├── validator.py    # 验证 + 漏洞利用执行
│   └── orchestrator.py # 流水线协调
├── tools/              # 领域特定工具
│   ├── slither_tool.py # Slither 静态分析封装
│   ├── aderyn_tool.py  # Aderyn 静态分析封装
│   ├── exploit_gen.py  # Foundry PoC 生成
│   ├── concrete_execution.py  # Foundry 测试运行器
│   ├── source_fetcher.py      # 合约源码获取
│   ├── state_reader.py        # 链上状态读取
│   └── solodit_fetcher.py     # Solodit 报告导入
├── knowledge/          # RAG 知识库
│   └── knowledge_base.py      # ChromaDB + 向量搜索
├── chain/              # 链上集成
│   ├── eas_attest.py   # EAS Sepolia 证明
│   └── chain_verifier.py      # 链上验证
├── mcp/                # MCP 服务器
│   └── mcp_server.py   # Model Context Protocol 服务器
├── evaluation/         # 评估框架
│   └── evaluation_engine.py
└── utils/
    ├── mimo_llm.py     # MiMo V2.5 Pro API 客户端
    └── logger.py       # 结构化日志

data/
├── contracts/          # 测试合约
├── knowledge/          # RAG 文档 (finding-format, solidity-checks, multi-expert)
│   └── reference/      # 303 个漏洞参考文档
├── solodit/            # 477 篇真实 Solodit 审计报告
└── vulnerabilities/    # 漏洞模式

demo/
├── index.html          # 交互式 demo 页面 (英文)
└── index-zh.html       # 交互式 demo 页面 (中文)

docs/
├── en/                 # 英文文档
├── zh/                 # 中文文档
└── llms.txt            # AI 代理可读的项目概述
```

## 🎮 Demo

`demo/` 目录包含交互式 Web Demo：

```bash
# 本地启动 demo
cd demo && python3 -m http.server 8080
# 打开 http://localhost:8080 (英文)
# 打开 http://localhost:8080/index-zh.html (中文)
```

## 🎯 赛道适配

### AI 智能体主赛道

AuditAI 是一个**多代理系统**，不是单次 LLM 调用。五个专业代理（审计器、架构师、代码生成器、优化器、验证器）通过中央协调器协同工作，每个代理都有领域特定工具 — 静态分析器（Slither、Aderyn）、RAG 知识库、Foundry 模糊测试和链上证明。流水线完全自主：输入 `.sol` 文件，输出带补丁和链上证明的验证审计报告。

### Security / Risk Agent

AuditAI 是一个**安全审计代理**，专注于智能合约漏洞检测和修复。它使用双引擎静态分析（Slither + Aderyn）、LLM 深度分析、RAG 知识增强（477 篇真实审计报告）和 Foundry 模糊测试来发现和验证漏洞。每个发现都经过事实核查（Verificator）以减少误报。

### BGA Track - AI for Transparency

每个审计结果都可以通过 **EAS Sepolia** 发布到链上，产生可验证的凭证，任何人都可以独立验证。证明包含审计评分、漏洞数量、审计模式和时间戳 — 全部不可篡改地记录在以太坊上。这使得审计结果**公开可验证**，而不是依赖 PDF 报告。

### GCC Track - Public Good

AuditAI 是一个**开源安全工具**，旨在提升整个以太坊生态的安全性。它将专业审计工具民主化，让任何开发者都能获得高质量的安全分析，而不需要昂贵的审计公司。知识库包含 477 篇真实审计报告，持续更新。

## ⚡ EAS Sepolia 证明

审计结果可以发布到 Sepolia 测试网的以太坊证明服务（EAS）。`--attest` 标志选择启用；不使用时不会发起网络请求。

```bash
# 独立证明
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol

# 审计后证明
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0xYourContract
```

**必需的环境变量：**

```dotenv
SEPOLIA_RPC_URL=https://sepolia.drpc.org
WALLET_PRIVATE_KEY=0x...          # Sepolia 测试钱包私钥，绝不提交
EAS_CONTRACT_ADDRESS=0xC2679fBD37d54388Ce493F1DB75320D236e1815e
SCHEMA_UID=0x...                  # 来自 EAS schema 注册的 bytes32 UID
```

**Schema 字段：** `uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress`

如果 `WALLET_PRIVATE_KEY`、`SCHEMA_UID` 或 RPC 访问缺失，CLI 会返回模拟哈希和警告，而不是崩溃。成功交易链接到：`https://sepolia.etherscan.io/tx/<tx_hash>`

## 📚 文档

- **英文文档**：`docs/en/`
- **中文文档**：`docs/zh/`
- **AI 代理概述**：`docs/llms.txt`（可直接复制给 AI 代理）

## 🤝 贡献

参见 [贡献指南](docs/en/developer-guide/contributing.md)。

## 📄 许可证

MIT License
