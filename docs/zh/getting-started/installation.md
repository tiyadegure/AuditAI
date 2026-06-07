# 安装指南

> 安装 AuditAI，配置环境，并验证一切正常运行。

## 前置要求

| 要求 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 使用 `python3 --version` 检查 |
| Foundry | 最新版 | 通过 `curl -L https://foundry.paradigm.xyz \| bash` 安装 |
| Slither | 最新版 | `pip install slither-analyzer` |
| Solidity 编译器 | 0.8.x | Foundry 默认包含 `solc` |

## 步骤 1：克隆并安装

```bash
git clone https://github.com/your-org/eth-beijing-2026.git
cd eth-beijing-2026
pip install -r requirements.txt
```

## 步骤 2：配置环境

```bash
cp .env.example .env
```

编辑 `.env` 并填写所需值：

```dotenv
# 必填 — MiMo API 密钥（在 https://platform.xiaomimimo.com/console/plan-manage 获取）
MIMO_API_KEY=your-mimo-api-key

# 可选 — EAS 链上证明（Sepolia 测试网）
SEPOLIA_RPC_URL=https://sepolia.drpc.org
WALLET_PRIVATE_KEY=0x...          # Sepolia 测试钱包，切勿提交
EAS_CONTRACT_ADDRESS=0xC2679fBD37d54388Ce493F1DB75320D236e1815e
SCHEMA_UID=0x...                  # EAS schema 注册的 bytes32 UID

# 可选 — HuggingFace 镜像（中国默认）
HF_ENDPOINT=https://hf-mirror.com
```

完整变量列表请参阅 [配置参考](../reference/config.md)。

## 步骤 3：验证安装

```bash
# 检查 CLI 是否可用
python3 -m src.main --help

# 运行快速检测扫描
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

如果看到漏洞表格，则说明安装成功。

## 故障排除

### `ModuleNotFoundError: No module named 'src'`

从项目根目录运行：
```bash
cd /path/to/eth-beijing-2026
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

### Slither 未找到

```bash
pip install slither-analyzer
# 或
pipx install slither-analyzer
```

### HuggingFace 下载失败（中国网络）

项目会自动设置 `HF_ENDPOINT=https://hf-mirror.com`。如果仍然失败：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### ChromaDB / sentence-transformers 未安装

知识库会回退到关键词搜索。如需完整向量 RAG：

```bash
pip install chromadb sentence-transformers
```

## 另请参阅

- [快速开始](quickstart.md) — 运行首次审计
- [配置参考](../reference/config.md) — 所有 `.env` 和 `settings.yaml` 选项
