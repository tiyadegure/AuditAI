# Configuration Reference

> All configuration options for AuditAI — `.env` variables and `settings.yaml`.

## Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

### MiMo LLM (Required)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MIMO_API_KEY` | **Yes** | — | MiMo API key. Get one at [platform.xiaomimimo.com](https://platform.xiaomimimo.com/console/plan-manage) |
| `MIMO_TOKEN_PLAN_BASE` | No | `https://token-plan-cn.xiaomimimo.com/v1` | MiMo API base URL |

### External Tools

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CYFRIN_API_KEY` | No | — | Cyfrin API key (optional) |
| `ETHERSCAN_API_KEY` | No | — | Etherscan API key for source fetching |
| `ETH_RPC_URL` | No | — | Ethereum mainnet RPC URL |
| `COINGECKO_API_KEY` | No | — | CoinGecko API key for revenue normalization |

### HuggingFace

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HF_ENDPOINT` | No | `https://hf-mirror.com` | HuggingFace mirror URL (auto-set for China) |

### EAS Attestation (Sepolia)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SEPOLIA_RPC_URL` | No | `https://sepolia.drpc.org` | Sepolia RPC endpoint |
| `WALLET_PRIVATE_KEY` | No | — | Sepolia test wallet private key. **NEVER commit this.** |
| `EAS_CONTRACT_ADDRESS` | No | `0xC2679fBD37d54388Ce493F1DB75320D236e1815e` | EAS contract on Sepolia |
| `SCHEMA_UID` | No | — | bytes32 UID from EAS schema registration |

### Schema Details

- **Schema Registry (Sepolia):** `0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0`
- **Schema:** `uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress`

## Settings YAML (`config/settings.yaml`)

### Model Configuration

```yaml
model:
  default: "mimo"
  audit: "mimo"
  code_generation: "mimo"
  verification: "mimo"

  mimo:
    api_base: "https://api.xiaomimimo.com/v1"
    api_key: "${MIMO_API_KEY}"
    model: "mimo-v2.5-pro"
    temperature: 0.7
    max_tokens: 4096
```

### Agent Configuration

```yaml
agents:
  auditor:
    role: "Smart Contract Security Auditor"
    goal: "Analyze smart contracts for security vulnerabilities"

  architect:
    role: "Security Architecture Strategist"
    goal: "Design repair strategies for identified vulnerabilities"

  code_generator:
    role: "Secure Code Generator"
    goal: "Generate secure code patches for vulnerabilities"

  refiner:
    role: "Code Refinement Specialist"
    goal: "Iteratively improve code patches for quality and security"

  validator:
    role: "Security Validator"
    goal: "Verify that patches fix vulnerabilities without introducing new issues"
```

### Tools Configuration

```yaml
tools:
  slither:
    enabled: true
    detectors: "all"
    exclude: []

  source_fetcher:
    enabled: true
    etherscan_api: "${ETHERSCAN_API_KEY}"

  state_reader:
    enabled: true
    rpc_url: "${ETH_RPC_URL}"

  code_sanitizer:
    enabled: true
    remove_comments: true
    remove_unused: true

  concrete_execution:
    enabled: true
    framework: "foundry"

  revenue_normalizer:
    enabled: true
    coingecko_api: "${COINGECKO_API_KEY}"
```

### Knowledge Base Configuration

```yaml
knowledge:
  vector_store: "chromadb"
  embedding_model: "all-MiniLM-L6-v2"
  collection_name: "smart_contract_security"
  chunk_size: 1000
  chunk_overlap: 200
```

### Evaluation Configuration

```yaml
evaluation:
  modes:
    - detect
    - patch
    - exploit
  test_cases: "data/vulnerabilities/"
  timeout: 300
```

### Chain Configuration

```yaml
chain:
  network: "ethereum"
  rpc_url: "${ETH_RPC_URL}"
  chain_id: 1
  gas_limit: 3000000
```

### MCP Configuration

```yaml
mcp:
  server_name: "smart-contract-auditor"
  version: "1.0.0"
  port: 8080
```

## ChromaDB Configuration

ChromaDB stores its data in `data/knowledge/chromadb/`. The collection uses cosine similarity:

```python
collection = client.get_or_create_collection(
    name="smart_contract_security",
    metadata={"hnsw:space": "cosine"},
)
```

To reset the knowledge base, delete the `data/knowledge/chromadb/` directory.

## See Also

- [CLI Flags Reference](cli-flags.md) — command-line flags
- [Installation Guide](../getting-started/installation.md) — setup instructions
- [EAS Attestation](../user-guide/attestation.md) — attestation configuration
