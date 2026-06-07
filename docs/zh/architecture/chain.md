# 链层 — EAS 证明

> AuditAI 如何将审计结果发布到 Sepolia 上的 Ethereum Attestation Service。

## 概述

链层（`src/chain/eas_attest.py`）通过 [Ethereum Attestation Service (EAS)](https://attest.org/) 在 Sepolia 测试网上处理链上证明。它 ABI 编码审计数据，构建 EIP-1559 交易，签名并提交到 EAS 合约。

## 合约地址（Sepolia）

| 合约 | 地址 |
|------|------|
| **EAS** | `0xC2679fBD37d54388Ce493F1DB75320D236e1815e` |
| **Schema Registry** | `0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0` |

## Schema 结构

证明 schema（已预注册）：

```
uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress
```

使用 `eth_abi.encode()` 进行 ABI 编码：

```python
def _encode_audit_data(contract_address, audit_score, vulnerabilities_found, audit_mode, timestamp):
    return eth_abi.encode(
        ["uint8", "uint16", "string", "uint64", "address"],
        [audit_score, vulnerabilities_found, audit_mode, timestamp, contract_address],
    )
```

## 评分计算

```python
_SEV_TO_SCORE = {
    "critical": 1, "high": 3, "medium": 5,
    "low": 7, "informational": 9, "info": 9,
}

def compute_audit_score(vulnerabilities):
    if not vulnerabilities:
        return 10  # 满分
    worst = 10
    for v in vulnerabilities:
        sev = v.get("severity", "medium").lower()
        worst = min(worst, _SEV_TO_SCORE.get(sev, 5))
    return worst
```

## 交易构建

模块支持 EIP-1559 交易，自动回退到传统 gas 定价：

```python
# EIP-1559（首选）
tx_params = {
    "chainId": 11155111,
    "from": account.address,
    "nonce": nonce,
    "gas": 300_000,
    "maxFeePerGas": base_fee * 2 + max_priority,
    "maxPriorityFeePerGas": max_priority,
}

# 回退：传统 gasPrice
legacy_params = {
    "chainId": 11155111,
    "from": account.address,
    "nonce": nonce,
    "gas": 300_000,
    "gasPrice": w3.eth.gas_price,
}
```

## RPC 连接

模块尝试多个 Sepolia RPC 端点并回退：

```python
fallbacks = [
    rpc_url,                                           # 来自 .env
    "https://sepolia.drpc.org",
    "https://rpc.sepolia.org",
    "https://ethereum-sepolia-rpc.publicnode.com",
]
```

每个端点有 10 秒超时。如果全部失败，证明降级为模拟模式。

## 5 个降级门

模块有 5 个顺序门。每个门失败时返回带警告的模拟哈希：

### 门 1：WALLET_PRIVATE_KEY (ISC-7)

```python
private_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()
if not private_key:
    return {"success": False, "tx_hash": _mock_tx_hash("no-key"), "message": "...", "mock": True}
```

### 门 2：SCHEMA_UID (ISC-11)

```python
schema_uid = os.getenv("SCHEMA_UID", "").strip()
if not schema_uid.startswith("0x") or len(schema_uid) != 66:
    return {"success": False, "tx_hash": _mock_tx_hash("bad-schema"), "message": "...", "mock": True}
```

### 门 3：RPC 连接 (ISC-8)

```python
try:
    w3 = _get_web3()
except ConnectionError:
    return {"success": False, "tx_hash": _mock_tx_hash("rpc-fail"), "message": "...", "mock": True}
```

### 门 4a：TX 构建 (ISC-9)

```python
try:
    tx = eas.functions.attest(...).build_transaction(tx_params)
except Exception:
    # 尝试传统 gasPrice
    tx = eas.functions.attest(...).build_transaction(legacy_params)
```

### 门 4b/c：TX 发送/回执 (ISC-10)

```python
signed = w3.eth.account.sign_transaction(tx, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

if receipt.status == 1:
    return {"success": True, "tx_hash": tx_hex, "mock": False}
else:
    return {"success": False, "tx_hash": f"error-revert-{tx_hash.hex()[:16]}", "mock": False}
```

## 模拟哈希

模拟哈希是确定性 SHA-256 摘要，前缀为 `mock-`：

```python
def _mock_tx_hash(label: str) -> str:
    digest = hashlib.sha256(f"mock-eas-{label}-{time.time()}".encode()).hexdigest()
    return f"mock-0x{digest[:64]}"
```

## 另请参阅

- [EAS 证明指南](../user-guide/attestation.md) — 使用和配置
- [架构概述](overview.md) — 完整流水线
- [配置参考](../reference/config.md) — EAS 环境变量
