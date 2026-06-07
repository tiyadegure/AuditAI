# ◆ AuditAI — Smart Contract Security, Reimagined

> A 5-layer AI agent that detects, verifies, patches, and attests smart contract vulnerabilities — all on-chain.

## Quick Links

| | |
|---|---|
| **[🚀 Getting Started](getting-started/installation.md)** | Install AuditAI and run your first audit |
| **[📖 CLI Reference](user-guide/cli.md)** | Full command and flag documentation |
| **[🏗️ Architecture](architecture/overview.md)** | How the 5-agent pipeline works |
| **[🔌 MCP Integration](user-guide/mcp.md)** | Expose audit tools to IDEs and agents |
| **[🔗 EAS Attestation](user-guide/attestation.md)** | On-chain verifiable audit credentials |
| **[🤝 Contributing](developer-guide/contributing.md)** | Help build AuditAI |

## ✨ Core Features

- **🔍 Dual-engine detection** — Slither + Aderyn static analysis with LLM consensus scoring
- **📚 2,450-chunk RAG knowledge base** — 477 real Solodit audit reports + 303 vulnerability reference docs, embedded with all-MiniLM-L6-v2 via ChromaDB
- **🔬 Foundry invariant fuzzing + exploit PoC generation** — auto-generates self-contained Foundry test contracts to verify vulnerabilities
- **🔗 EAS Sepolia on-chain attestation** — verifiable audit credentials posted to Ethereum Attestation Service
- **🧠 5-agent pipeline** — Auditor → Architect → Code Generator → Refiner → Validator, coordinated by a central orchestrator
- **🔌 MCP server** — expose audit tools to external agents and IDE integrations via Model Context Protocol
- **🛡️ Crash recovery** — checkpoint after each step, resume with `--resume` flag, never lose progress

## 🚀 Install in One Line

```bash
pip install -r requirements.txt
```

## 🎯 Run Your First Audit

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode all
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **🧠 AI Model** | MiMo V2.5 Pro |
| **🔍 Static Analysis** | Slither + Aderyn (dual-engine consensus) |
| **📚 Knowledge Base** | ChromaDB + sentence-transformers (all-MiniLM-L6-v2) |
| **🔗 On-Chain** | EAS (Ethereum Attestation Service) Sepolia |
| **🔬 Fuzzing** | Foundry (invariant tests + exploit PoC) |
| **🧠 Multi-Agent** | 5-agent pipeline (Auditor / Architect / CodeGen / Refiner / Validator) |
| **🔌 MCP** | Python SDK — exposes audit tools to external consumers |

## 📂 Project Structure

```
src/
├── agents/             # 5-agent pipeline
│   ├── auditor.py      # Vulnerability detection (Slither + LLM + RAG)
│   ├── architect.py    # Repair strategy design
│   ├── code_generator.py   # Patch generation
│   ├── refiner.py      # Iterative code improvement
│   ├── validator.py    # Verification + exploit execution
│   └── orchestrator.py # Pipeline coordination + checkpoint recovery
├── tools/              # Domain-specific tools
│   ├── slither_tool.py # Slither static analysis wrapper
│   ├── aderyn_tool.py  # Aderyn static analysis wrapper
│   ├── exploit_gen.py  # Foundry PoC generation
│   └── concrete_execution.py  # Foundry test runner
├── knowledge/          # RAG knowledge base
│   └── knowledge_base.py      # ChromaDB + vector search
├── chain/              # On-chain integration
│   ├── eas_attest.py   # EAS Sepolia attestation
│   └── chain_verifier.py      # Chain verification
├── mcp/                # MCP server
│   └── mcp_server.py   # Model Context Protocol server
└── utils/
    ├── mimo_llm.py     # MiMo V2.5 Pro API client
    └── checkpoint.py   # Crash recovery checkpoint manager
```

## 🎮 Demo

Visit our live demo: [audit-ai.tech](https://audit-ai.tech)

- **English**: [audit-ai.tech](https://audit-ai.tech)
- **中文**: [audit-ai.tech/index-zh.html](https://audit-ai.tech/index-zh.html)

## 📚 Documentation

- **English**: [docs/en/](en/)
- **中文**: [docs/zh/](zh/)
- **LLM Index**: [llms.txt](llms.txt)

## See Also

- [Getting Started](getting-started/installation.md) — Installation and setup
- [Architecture Overview](architecture/overview.md) — How the 5-agent pipeline works
- [CLI Reference](user-guide/cli.md) — All commands and flags
