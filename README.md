# AuditAI — Smart Contract Security, Reimagined

> 5-layer AI agent that detects, verifies, patches, and attests — all on-chain.

🌐 **Live Demo**: [audit-ai.tech](https://audit-ai.tech) (English | 中文)

## ✨ Highlights

- **Dual-engine detection** — Slither + Aderyn static analysis with LLM consensus scoring
- **2,450-chunk RAG knowledge base** — 477 real Solodit audit reports + 303 vulnerability reference docs, embedded with all-MiniLM-L6-v2 via ChromaDB
- **Foundry invariant fuzzing + exploit PoC generation** — auto-generates self-contained Foundry test contracts to verify vulnerabilities
- **EAS Sepolia on-chain attestation** — verifiable audit credentials posted to Ethereum Attestation Service
- **5-agent pipeline** — Auditor → Architect → Code Generator → Refiner → Validator, coordinated by a central orchestrator
- **MCP server** — expose audit tools to external agents and IDE integrations via Model Context Protocol

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI / MCP Server                            │
│  audit · detect · patch · exploit · attest · serve · evaluate   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │   Orchestrator   │
                  └───┬──┬──┬──┬──┬┘
                      │  │  │  │  │
         ┌────────────┘  │  │  │  └────────────┐
         ▼               ▼  │  ▼               ▼
    ┌─────────┐   ┌─────────┐ ┌─────────┐  ┌─────────┐
    │Auditor  │   │Architect│ │Refiner  │  │Validator│
    │detect   │   │design   │ │improve  │  │verify   │
    └────┬────┘   └────┬────┘ └────┬────┘  └────┬────┘
         │             │           │             │
         ▼             ▼           │             ▼
    ┌─────────┐  ┌──────────┐     │     ┌──────────────┐
    │Slither  │  │  Code    │     │     │  Concrete    │
    │Aderyn   │  │Generator │─────┘     │  Execution   │
    │RAG KB   │  │  patch   │           │  (Foundry)   │
    └─────────┘  └──────────┘           └──────────────┘
                                                │
                                         ┌──────▼──────┐
                                         │ EAS Sepolia  │
                                         │ On-Chain     │
                                         │ Attestation  │
                                         └─────────────┘
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and fill in MIMO_API_KEY

# 3. Run a full audit
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode all

# 4. Detect only (fastest)
python3 -m src.main detect data/contracts/VulnerableBank.sol

# 5. Audit + on-chain attestation
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0x...

# 6. Start MCP server (for IDE / agent integration)
python3 -m src.main serve
```

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Model** | MiMo V2.5 Pro |
| **Static Analysis** | Slither + Aderyn (dual-engine consensus) |
| **Knowledge Base** | ChromaDB + sentence-transformers (all-MiniLM-L6-v2) |
| **On-Chain** | EAS (Ethereum Attestation Service) Sepolia |
| **Fuzzing** | Foundry (invariant tests + exploit PoC) |
| **Multi-Agent** | 5-agent pipeline (Auditor / Architect / CodeGen / Refiner / Validator) |
| **MCP** | Python SDK — exposes audit tools to external consumers |

## 📂 Project Structure

```
src/
├── agents/             # 5-agent pipeline
│   ├── auditor.py      # Vulnerability detection (Slither + LLM + RAG)
│   ├── architect.py    # Repair strategy design
│   ├── code_generator.py   # Patch generation
│   ├── refiner.py      # Iterative code improvement
│   ├── validator.py    # Verification + exploit execution
│   └── orchestrator.py # Pipeline coordination
├── tools/              # Domain-specific tools
│   ├── slither_tool.py # Slither static analysis wrapper
│   ├── aderyn_tool.py  # Aderyn static analysis wrapper
│   ├── exploit_gen.py  # Foundry PoC generation
│   ├── concrete_execution.py  # Foundry test runner
│   ├── source_fetcher.py      # Contract source retrieval
│   ├── state_reader.py        # On-chain state reading
│   └── solodit_fetcher.py     # Solodit report ingestion
├── knowledge/          # RAG knowledge base
│   └── knowledge_base.py      # ChromaDB + vector search
├── chain/              # On-chain integration
│   ├── eas_attest.py   # EAS Sepolia attestation
│   └── chain_verifier.py      # Chain verification
├── mcp/                # MCP server
│   └── mcp_server.py   # Model Context Protocol server
├── evaluation/         # Evaluation framework
│   └── evaluation_engine.py
└── utils/
    ├── mimo_llm.py     # MiMo V2.5 Pro API client
    └── logger.py       # Structured logging

data/
├── contracts/          # Test contracts
├── knowledge/          # RAG docs (finding-format, solidity-checks, multi-expert)
│   └── reference/      # 303 vulnerability reference docs
├── solodit/            # 477 real Solodit audit reports
└── vulnerabilities/    # Vulnerability patterns

demo/
└── index.html          # Interactive demo page
```

## 🎮 Demo

The `demo/` directory contains an interactive web demo:

```bash
# Serve the demo locally
cd demo && python3 -m http.server 8080
# Open http://localhost:8080
```

## 🎯 Track Fit

### AI Agent 主赛道

AuditAI is a **multi-agent system**, not a single LLM call. Five specialized agents (Auditor, Architect, Code Generator, Refiner, Validator) coordinate through a central orchestrator, each with domain-specific tools — static analyzers (Slither, Aderyn), a RAG knowledge base, Foundry fuzzing, and on-chain attestation. The pipeline is fully autonomous: input a `.sol` file, get a verified audit report with patches and on-chain proof.

### BGA Track — AI for Transparency

Every audit result can be attested on-chain via **EAS Sepolia**, producing a verifiable credential that anyone can independently verify. The attestation includes audit score, vulnerability count, audit mode, and timestamp — all immutably recorded on Ethereum. This makes audit results **publicly verifiable** rather than trusting a PDF report.

## ⚡ EAS Sepolia Attestation

Audit results can be posted to Ethereum Attestation Service (EAS) on Sepolia. The `--attest` flag opts in; without it, no network requests are made.

```bash
# Standalone attestation
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol

# Attest after audit
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0xYourContract
```

**Required environment variables:**

```dotenv
SEPOLIA_RPC_URL=https://sepolia.drpc.org
WALLET_PRIVATE_KEY=0x...          # Sepolia test wallet, never commit
EAS_CONTRACT_ADDRESS=0xC2679fBD37d54388Ce493F1DB75320D236e1815e
SCHEMA_UID=0x...                  # bytes32 UID from EAS schema registration
```

**Schema fields:** `uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress`

If `WALLET_PRIVATE_KEY`, `SCHEMA_UID`, or RPC access is missing, the CLI returns a mock hash with a warning instead of crashing. Successful transactions link to: `https://sepolia.etherscan.io/tx/<tx_hash>`
