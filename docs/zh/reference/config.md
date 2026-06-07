# 配置参考

> AuditAI 的所有配置选项 — `.env` 变量和 `settings.yaml`。

## 环境变量 (`.env`)

将 `.env.example` 复制为 `.env` 并填写值：

```bash
cp .env.example .env
```

### MiMo LLM（必填）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `MIMO_API_KEY` | **是** | — | MiMo API 密钥。在 [platform.xiaomimimo.com](https://platform.xiaomimimo.com/console/plan-manage) 获取 |
| `MIMO_TOKEN_PLAN_BASE` | 否 | `https://token-plan-cn.xiaomimimo.com/v1` | MiMo API 基础 URL |

### 外部工具

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `CYFRIN_API_KEY` | 否 | — | Cyfrin API 密钥（可选） |
| `ETHERSCAN_API_KEY` | 否 | — | Etherscan API 密钥，用于源码获取 |
| `ETH_RPC_URL` | 否 | — | 以太坊主网 RPC URL |
| `COINGECKO_API_KEY` | 否 | — | CoinGecko API 密钥，用于收入标准化 |

### HuggingFace

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `HF_ENDPOINT` | 否 | `https://hf-mirror.com` | HuggingFace 镜像 URL（中国自动设置） |

### EAS 证明（Sepolia）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `SEPOLIA_RPC_URL` | 否 | `https://sepolia.drpc.org` | Sepolia RPC 端点 |
| `WALLET_PRIVATE_KEY` | 否 | — | Sepolia 测试钱包私钥。**切勿提交。** |
| `EAS_CONTRACT_ADDRESS` | 否 | `0xC2679fBD37d54388Ce493F1DB75320D236e1815e` | Sepolia 上的 EAS 合约 |
| `SCHEMA_UID` | 否 | — | EAS schema 注册的 bytes32 UID |

### Schema 详情

- **Schema Registry (Sepolia):** `0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0`
- **Schema:** `uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress`

## Settings YAML (`config/settings.yaml`)

### 模型配置

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

### 代理配置

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

### 工具配置

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

### 知识库配置

```yaml
knowledge:
  vector_store: "chromadb"
  embedding_model: "all-MiniLM-L6-v2"
  collection_name: "smart_contract_security"
  chunk_size: 1000
  chunk_overlap: 200
```

### 评估配置

```yaml
evaluation:
  modes:
    - detect
    - patch
    - exploit
  test_cases: "data/vulnerabilities/"
  timeout: 300
```

### 链配置

```yaml
chain:
  network: "ethereum"
  rpc_url: "${ETH_RPC_URL}"
  chain_id: 1
  gas_limit: 3000000
```

### MCP 配置

```yaml
mcp:
  server_name: "smart-contract-auditor"
  version: "1.0.0"
  port: 8080
```

## ChromaDB 配置

ChromaDB 将数据存储在 `data/knowledge/chromadb/` 中。集合使用余弦相似度：

```python
collection = client.get_or_create_collection(
    name="smart_contract_security",
    metadata={"hnsw:space": "cosine"},
)
```

要重置知识库，删除 `data/knowledge/chromadb/` 目录。

## 另请参阅

- [CLI 标志参考](cli-flags.md) — 命令行标志
- [安装指南](../getting-started/installation.md) — 安装说明
- [EAS 证明](../user-guide/attestation.md) — 证明配置
