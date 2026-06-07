# Chain Layer — EAS Attestation

> How AuditAI posts audit results to Ethereum Attestation Service on Sepolia.

## Overview

The chain layer (`src/chain/eas_attest.py`) handles on-chain attestation via [Ethereum Attestation Service (EAS)](https://attest.org/) on Sepolia testnet. It ABI-encodes audit data, builds an EIP-1559 transaction, signs it, and submits it to the EAS contract.

## Contract Addresses (Sepolia)

| Contract | Address |
|----------|---------|
| **EAS** | `0xC2679fBD37d54388Ce493F1DB75320D236e1815e` |
| **Schema Registry** | `0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0` |

## Schema Structure

The attestation schema (pre-registered):

```
uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress
```

ABI-encoded with `eth_abi.encode()`:

```python
def _encode_audit_data(contract_address, audit_score, vulnerabilities_found, audit_mode, timestamp):
    return eth_abi.encode(
        ["uint8", "uint16", "string", "uint64", "address"],
        [audit_score, vulnerabilities_found, audit_mode, timestamp, contract_address],
    )
```

## Score Computation

```python
_SEV_TO_SCORE = {
    "critical": 1, "high": 3, "medium": 5,
    "low": 7, "informational": 9, "info": 9,
}

def compute_audit_score(vulnerabilities):
    if not vulnerabilities:
        return 10  # perfect score
    worst = 10
    for v in vulnerabilities:
        sev = v.get("severity", "medium").lower()
        worst = min(worst, _SEV_TO_SCORE.get(sev, 5))
    return worst
```

## Transaction Building

The module supports EIP-1559 transactions with automatic fallback to legacy gas pricing:

```python
# EIP-1559 (preferred)
tx_params = {
    "chainId": 11155111,
    "from": account.address,
    "nonce": nonce,
    "gas": 300_000,
    "maxFeePerGas": base_fee * 2 + max_priority,
    "maxPriorityFeePerGas": max_priority,
}

# Fallback: legacy gasPrice
legacy_params = {
    "chainId": 11155111,
    "from": account.address,
    "nonce": nonce,
    "gas": 300_000,
    "gasPrice": w3.eth.gas_price,
}
```

## RPC Connection

The module tries multiple Sepolia RPC endpoints with fallback:

```python
fallbacks = [
    rpc_url,                                           # from .env
    "https://sepolia.drpc.org",
    "https://rpc.sepolia.org",
    "https://ethereum-sepolia-rpc.publicnode.com",
]
```

Each endpoint is tested with a 10-second timeout. If all fail, the attestation degrades to mock mode.

## 5 Degradation Gates

The module has 5 sequential gates. Each gate, if failed, returns a mock hash with a warning:

### Gate 1: WALLET_PRIVATE_KEY (ISC-7)

```python
private_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()
if not private_key:
    return {"success": False, "tx_hash": _mock_tx_hash("no-key"), "message": "...", "mock": True}
```

### Gate 2: SCHEMA_UID (ISC-11)

```python
schema_uid = os.getenv("SCHEMA_UID", "").strip()
if not schema_uid.startswith("0x") or len(schema_uid) != 66:
    return {"success": False, "tx_hash": _mock_tx_hash("bad-schema"), "message": "...", "mock": True}
```

### Gate 3: RPC Connection (ISC-8)

```python
try:
    w3 = _get_web3()
except ConnectionError:
    return {"success": False, "tx_hash": _mock_tx_hash("rpc-fail"), "message": "...", "mock": True}
```

### Gate 4a: TX Build (ISC-9)

```python
try:
    tx = eas.functions.attest(...).build_transaction(tx_params)
except Exception:
    # try legacy gasPrice
    tx = eas.functions.attest(...).build_transaction(legacy_params)
```

### Gate 4b/c: TX Send/Receipt (ISC-10)

```python
signed = w3.eth.account.sign_transaction(tx, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

if receipt.status == 1:
    return {"success": True, "tx_hash": tx_hex, "mock": False}
else:
    return {"success": False, "tx_hash": f"error-revert-{tx_hash.hex()[:16]}", "mock": False}
```

## Mock Hashes

Mock hashes are deterministic SHA-256 digests prefixed with `mock-`:

```python
def _mock_tx_hash(label: str) -> str:
    digest = hashlib.sha256(f"mock-eas-{label}-{time.time()}".encode()).hexdigest()
    return f"mock-0x{digest[:64]}"
```

## See Also

- [EAS Attestation Guide](../user-guide/attestation.md) — usage and configuration
- [Architecture Overview](overview.md) — full pipeline
- [Configuration Reference](../reference/config.md) — EAS environment variables
