# Installation

> Install AuditAI, configure your environment, and verify everything works.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Use `python3 --version` to check |
| Foundry | Latest | Install via `curl -L https://foundry.paradigm.xyz \| bash` |
| Slither | Latest | `pip install slither-analyzer` |
| Solidity compiler | 0.8.x | Foundry includes `solc` by default |

## Step 1: Clone and Install

```bash
git clone https://github.com/your-org/eth-beijing-2026.git
cd eth-beijing-2026
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```dotenv
# Required — MiMo API key (get one at https://platform.xiaomimimo.com/console/plan-manage)
MIMO_API_KEY=your-mimo-api-key

# Optional — EAS on-chain attestation (Sepolia testnet)
SEPOLIA_RPC_URL=https://sepolia.drpc.org
WALLET_PRIVATE_KEY=0x...          # Sepolia test wallet, NEVER commit
EAS_CONTRACT_ADDRESS=0xC2679fBD37d54388Ce493F1DB75320D236e1815e
SCHEMA_UID=0x...                  # bytes32 UID from EAS schema registration

# Optional — HuggingFace mirror (default for China)
HF_ENDPOINT=https://hf-mirror.com
```

See [Configuration Reference](../reference/config.md) for all variables.

## Step 3: Verify Installation

```bash
# Check the CLI is available
python3 -m src.main --help

# Run a quick detection-only scan
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

If you see a table of vulnerabilities, you're ready.

## Troubleshooting

### `ModuleNotFoundError: No module named 'src'`

Run from the project root:
```bash
cd /path/to/eth-beijing-2026
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

### Slither not found

```bash
pip install slither-analyzer
# or
pipx install slither-analyzer
```

### HuggingFace download fails (China network)

The project sets `HF_ENDPOINT=https://hf-mirror.com` automatically. If it still fails:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### ChromaDB / sentence-transformers not installed

The knowledge base falls back to keyword search. For full vector RAG:

```bash
pip install chromadb sentence-transformers
```

## See Also

- [Quickstart](quickstart.md) — run your first audit
- [Configuration Reference](../reference/config.md) — all `.env` and `settings.yaml` options
