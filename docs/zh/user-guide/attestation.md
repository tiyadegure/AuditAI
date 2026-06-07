# EAS 链上证明

> 将审计结果发布到 Sepolia 上的 Ethereum Attestation Service (EAS) — 公开可验证的审计凭证。

## 什么是 EAS？

[Ethereum Attestation Service (EAS)](https://attest.org/) 是一个链上证明协议 — 在以太坊上记录的签名、不可变声明。AuditAI 使用 EAS 在 Sepolia 测试网发布审计结果，生成任何人都可以独立验证的可验证凭证。

## Schema

证明 schema（已在 Sepolia 预注册）：

```
uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `auditScore` | `uint8` | 0–10 安全评分（10 = 无漏洞） |
| `vulnerabilitiesFound` | `uint16` | 漏洞总数 |
| `auditMode` | `string` | 使用的流水线模式（`detect`、`patch`、`exploit`、`all`） |
| `timestamp` | `uint64` | 证明的 Unix 时间戳 |
| `contractAddress` | `address` | 被审计合约地址 |

### 评分计算

```
Score = 所有发现中最差的严重性分数
  critical → 1
  high     → 3
  medium   → 5
  low      → 7
  info     → 9
  无漏洞   → 10
```

## 配置

在 `.env` 中添加：

```dotenv
# 真实证明必填
SEPOLIA_RPC_URL=https://sepolia.drpc.org
WALLET_PRIVATE_KEY=0x...                    # Sepolia 测试钱包（切勿提交）
EAS_CONTRACT_ADDRESS=0xC2679fBD37d54388Ce493F1DB75320D236e1815e
SCHEMA_UID=0x...                            # EAS schema 注册的 bytes32 UID
```

**Schema Registry (Sepolia):** `0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0`

### 获取钱包

1. 在 MetaMask 或任何钱包中创建 Sepolia 钱包
2. 从 [水龙头](https://sepoliafaucet.com) 获取 Sepolia ETH
3. 导出私钥并添加到 `.env`

### 注册 Schema

如果需要新的 schema UID：

1. 前往 [Sepolia 上的 EAS Schema Registry](https://sepolia.easscan.com/schema/create)
2. 注册 schema：`uint8 auditScore,uint16 vulnerabilitiesFound,string auditMode,uint64 timestamp,address contractAddress`
3. 将 schema UID 复制到 `.env`

## 使用方式

### 审计时证明

运行完整审计并将结果链上证明：

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol \
  --attest \
  --contract-address 0xYourContract
```

`--attest` 标志需要 `--contract-address`。

### 独立证明

不运行完整审计进行证明：

```bash
# 空漏洞列表证明（score=10）
python3 -m src.main attest 0xYourContract

# 指定合约源码（先运行 detect）
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol
```

## 降级行为

证明模块有 **5 个降级门**。如果任何门失败，返回带警告的模拟哈希，而不是崩溃：

| 门 | 条件 | 行为 |
|----|------|------|
| 1. `WALLET_PRIVATE_KEY` 缺失 | `.env` 中无密钥 | 模拟哈希 + 警告 |
| 2. `SCHEMA_UID` 无效 | 非 `0x` + 64 个十六进制字符 | 模拟哈希 + 警告 |
| 3. RPC 不可达 | 所有 Sepolia RPC 失败 | 模拟哈希 + 警告 |
| 4. TX 构建失败 | 合约调用错误 | `error-` 前缀哈希 |
| 5. TX 回退 | `receipt.status == 0` | `error-revert-` 前缀哈希 |

**模拟哈希** 以 `mock-0x...` 开头 — 未发送真实交易。

**成功交易** 返回真实 `0x...` 哈希和 Sepolia Etherscan 链接：

```
Sepolia tx: https://sepolia.etherscan.io/tx/0xabc123...
```

## 验证证明

验证他人的证明：

1. 获取交易哈希（如 `0xabc123...`）
2. 前往 `https://sepolia.etherscan.io/tx/0xabc123...`
3. 使用 EAS schema 解码输入数据

## 另请参阅

- [CLI 参考](cli.md) — `audit` 和 `attest` 命令
- [配置参考](../reference/config.md) — 所有 `.env` 变量
- [架构：链层](../architecture/chain.md) — 证明内部工作原理
