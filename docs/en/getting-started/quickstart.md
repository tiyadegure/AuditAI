# Quickstart

> Run your first smart contract audit in under 5 minutes.

## 1. Detect Vulnerabilities (Fastest)

```bash
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

This runs Slither + Aderyn + LLM analysis and outputs a table:

```
┌─────────────────────────────────────────┐
│       Vulnerabilities Found             │
├──────┬──────────────┬──────────┬────────┤
│ ID   │ Type         │ Severity │ Source │
├──────┼──────────────┼──────────┼────────┤
│ slither-0 │ reentrancy │ High     │ slither│
│ mimo-0    │ access_ctrl│ Critical │ mimo   │
└──────┴──────────────┴──────────┴────────┘
```

## 2. Full Audit (Detect + Patch + Verify)

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode all
```

This runs the full 5-agent pipeline:

1. **Detect** — Slither + Aderyn + LLM + RAG find vulnerabilities
2. **Patch** — Architect designs strategy, Code Generator produces patches, Refiner iterates
3. **Verify** — Validator runs Foundry tests to confirm fixes

Output is a markdown audit report with findings, patches, and verification status.

### Limit Patches

```bash
# Patch only the 2 most severe vulnerabilities (default)
python3 -m src.main audit data/contracts/VulnerableBank.sol

# Patch all vulnerabilities
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches -1

# Patch top 5
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches 5
```

### Save Report to File

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol -o report.json
```

## 3. Audit with On-Chain Attestation

```bash
python3 -m src.main audit data/contracts/VulnerableBank.sol \
  --attest \
  --contract-address 0xYourContract
```

This audits the contract AND posts the result to EAS Sepolia. See [EAS Attestation Guide](../user-guide/attestation.md).

## 4. Multi-Expert Analysis

For deeper analysis using the forefy/.context multi-expert framework:

```bash
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert
```

This runs three parallel LLM "experts" — a systematic auditor, a fresh-perspective auditor, and a triager that validates findings.

## Understanding the Output

Each vulnerability includes:

| Field | Meaning |
|-------|---------|
| `id` | Unique identifier (e.g., `slither-0`, `mimo-1`) |
| `type` | Vulnerability class (e.g., `reentrancy`, `access_control`) |
| `severity` | `critical` / `high` / `medium` / `low` / `informational` |
| `confidence` | Consensus score [0–1] — how many detector families agreed |
| `source` | Detection engine (`slither`, `aderyn`, `mimo`, `ba`, `ta`, etc.) |
| `verified` | Whether the Verificator confirmed it as a true positive |

## Next Steps

- [CLI Reference](../user-guide/cli.md) — all commands and flags
- [MCP Integration](../user-guide/mcp.md) — expose tools to Cursor / Claude
- [Architecture Overview](../architecture/overview.md) — understand the pipeline

## See Also

- [Installation](installation.md) — if you haven't set up yet
- [CLI Flags Reference](../reference/cli-flags.md) — every flag with defaults
