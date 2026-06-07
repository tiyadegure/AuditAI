# 🚀 Quick Start

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in MIMO_API_KEY
```

## 3. Available Commands

### Audit a contract (full analysis)
```bash
python3 -m src.main audit <contract_path> --mode all
```

### Detect only (fastest)
```bash
python3 -m src.main detect <contract_path>
```

### Audit + on-chain attestation (Sepolia)
```bash
python3 -m src.main audit <contract_path> --attest --contract-address 0x...
```

### Generate exploit PoC
```bash
python3 -m src.main exploit <contract_path> --vuln-type reentrancy
```

### Patch a vulnerability
```bash
python3 -m src.main patch <contract_path> --vuln-id 1
```

### Evaluate on test cases
```bash
python3 -m src.main evaluate --dataset data/evaluation/
```

### Start MCP server (for IDE / agent integration)
```bash
python3 -m src.main serve
```

## 4. Example Usage

```bash
# Analyze a local contract
python3 -m src.main detect ./my-contract.sol

# Full audit with report
python3 -m src.main audit ./my-contract.sol --mode all --output report.md

# Audit and attest on Sepolia
python3 -m src.main audit ./my-contract.sol --attest
```

## 5. MCP Server Integration

The MCP server allows integration with AI coding assistants:

```bash
# Start the server
python3 -m src.main serve

# The server will be available at http://localhost:3000
# Configure your IDE to connect to this endpoint
```

---

For more details, see the [full documentation](README.md).
