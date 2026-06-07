# EAS On-Chain Attestation

> Post audit results to Ethereum Attestation Service (EAS) on Sepolia — publicly verifiable audit credentials.

## What is EAS?

[Ethereum Attestation Service (EAS)](https://attest.org/) is an on-chain protocol for making attestations — signed, immutable claims recorded on Ethereum. AuditAI uses EAS to post audit results on Sepolia testnet, producing a verifiable credential that anyone can independently verify.

## Schema

The attestation schema (pre-registered on Sepolia):

```
uint8 auditScore, uint16 vulnerabilitiesFound, string auditMode, uint64 timestamp, address contractAddress
```

| Field | Type | Description |
|-------|------|-------------|
| `auditScore` | `uint8` | 0–10 security score (10 = no vulns) |
| `vulnerabilitiesFound` | `uint16` | Total vulnerability count |
| `auditMode` | `string` | Pipeline mode used (`detect`, `patch`, `exploit`, `all`) |
| `timestamp` | `uint64` | Unix timestamp of attestation |
| `contractAddress` | `address` | Audited contract address |

### Score Calculation

```
Score = worst severity score across all findings
  critical → 1
  high     → 3
  medium   → 5
  low      → 7
  info     → 9
  no vulns → 10
```

## Configuration

Add these to your `.env`:

```dotenv
# Required for real attestations
SEPOLIA_RPC_URL=https://sepolia.drpc.org
WALLET_PRIVATE_KEY=0x...                    # Sepolia test wallet (NEVER commit)
EAS_CONTRACT_ADDRESS=0xC2679fBD37d54388Ce493F1DB75320D236e1815e
SCHEMA_UID=0x...                            # bytes32 UID from EAS schema registration
```

**Schema Registry (Sepolia):** `0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0`

### Getting a Wallet

1. Create a Sepolia wallet in MetaMask or any wallet
2. Get Sepolia ETH from a [faucet](https://sepoliafaucet.com)
3. Export the private key and add it to `.env`

### Registering a Schema

If you need a new schema UID:

1. Go to [EAS Schema Registry on Sepolia](https://sepolia.easscan.com/schema/create)
2. Register the schema: `uint8 auditScore,uint16 vulnerabilitiesFound,string auditMode,uint64 timestamp,address contractAddress`
3. Copy the schema UID to `.env`

## Usage

### Attest with Audit

Run a full audit and attest the results on-chain:

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol \
  --attest \
  --contract-address 0xYourContract
```

The `--attest` flag requires `--contract-address`.

### Standalone Attestation

Attest without running a full audit:

```bash
# Attest with empty vulnerability list (score=10)
python3 -m src.main attest 0xYourContract

# Attest with a specific contract (runs detect first)
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol
```

## Degradation Behavior

The attestation module has **5 degradation gates**. If any gate fails, it returns a mock hash with a warning instead of crashing:

| Gate | Condition | Behavior |
|------|-----------|----------|
| 1. `WALLET_PRIVATE_KEY` missing | No key in `.env` | Mock hash + warning |
| 2. `SCHEMA_UID` invalid | Not `0x` + 64 hex chars | Mock hash + warning |
| 3. RPC unreachable | All Sepolia RPCs fail | Mock hash + warning |
| 4. TX build fails | Contract call error | `error-` prefix hash |
| 5. TX reverted | `receipt.status == 0` | `error-revert-` prefix hash |

**Mock hashes** start with `mock-0x...` — no real transaction was sent.

**Successful transactions** return a real `0x...` hash with a Sepolia Etherscan link:

```
Sepolia tx: https://sepolia.etherscan.io/tx/0xabc123...
```

## Verifying an Attestation

To verify someone's attestation:

1. Get the transaction hash (e.g., `0xabc123...`)
2. Go to `https://sepolia.etherscan.io/tx/0xabc123...`
3. Decode the input data using the EAS schema

## See Also

- [CLI Reference](cli.md) — `audit` and `attest` commands
- [Configuration Reference](../reference/config.md) — all `.env` variables
- [Architecture: Chain Layer](../architecture/chain.md) — how attestation works internally
