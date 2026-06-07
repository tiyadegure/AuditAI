# CLI Reference

> Complete command reference for the AuditAI CLI.

## Overview

All commands are accessed via `python3 -m src.main <command>`:

```bash
python3 -m src.main [OPTIONS] COMMAND [ARGS]
```

## Commands

### `audit`

Run a full smart contract audit (detect → patch → verify).

```bash
python3 -m src.main audit CONTRACT_PATH [OPTIONS]
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_PATH` | Path (required) | Path to the `.sol` contract file |

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--mode`, `-m` | Choice: `detect`, `patch`, `exploit`, `all` | `all` | How far to run the pipeline |
| `--output`, `-o` | Path | `None` | Save JSON results to file |
| `--max-patches` | Integer | `2` | Max vulnerabilities to patch (highest-severity first). Use `-1` for all |
| `--attest` | Flag | `False` | Attest results on-chain (EAS Sepolia) after completion |
| `--contract-address` | String | `None` | Contract address for attestation (required with `--attest`) |
| `--resume` | Flag | `False` | Resume from last checkpoint |

**Examples:**

```bash
# Full audit, patch top 2 vulns
python3 -m src.main audit data/contracts/VulnerableBank.sol

# Detection only
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode detect

# Full audit + on-chain attestation
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0x1234...

# Patch all vulnerabilities
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches -1

# Save to file
python3 -m src.main audit data/contracts/VulnerableBank.sol -o results.json

# Resume interrupted audit
python3 -m src.main audit data/contracts/VulnerableBank.sol --resume
```

---

### `detect`

Detect vulnerabilities only (no patching or verification).

```bash
python3 -m src.main detect CONTRACT_PATH [OPTIONS]
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_PATH` | Path (required) | Path to the `.sol` contract file |

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--multi-expert`, `-me` | Flag | `False` | Use multi-expert analysis (3 parallel LLM experts from forefy/.context) |
| `--strategy`, `-s` | Choice: `ba`, `ta`, `all` | `all` | Detection strategy: `ba` = broad analysis, `ta` = targeted analysis, `all` = both (LLM-SmartAudit §3.2) |

**Examples:**

```bash
# Standard detection
python3 -m src.main detect data/contracts/VulnerableBank.sol

# Multi-expert mode
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert

# Targeted analysis only (faster, checks known vuln types)
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ta

# Broad analysis only
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ba
```

---

### `patch`

Generate a patch for a specific vulnerability.

```bash
python3 -m src.main patch CONTRACT_PATH VULNERABILITY_ID
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_PATH` | Path (required) | Path to the `.sol` contract file |
| `VULNERABILITY_ID` | String (required) | ID from detect output (e.g., `slither-0`, `mimo-1`) |

**Example:**

```bash
# First detect to get vulnerability IDs
python3 -m src.main detect data/contracts/VulnerableBank.sol

# Then patch a specific one
python3 -m src.main patch data/contracts/VulnerableBank.sol slither-0
```

---

### `exploit`

Execute an exploit against a deployed contract.

```bash
python3 -m src.main exploit CONTRACT_ADDRESS EXPLOIT_CODE_PATH
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_ADDRESS` | String (required) | On-chain contract address |
| `EXPLOIT_CODE_PATH` | Path (required) | Path to Foundry exploit test file |

**Example:**

```bash
python3 -m src.main exploit 0x1234... tests/exploits/VulnerableBank_exploit.t.sol
```

---

### `attest`

Attest audit results on EAS (Sepolia testnet).

```bash
python3 -m src.main attest CONTRACT_ADDRESS [OPTIONS]
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_ADDRESS` | String (required) | Contract address for the attestation |

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--contract-path` | Path | `None` | Path to contract source (auto-detects from audit history if omitted) |

**Examples:**

```bash
# Standalone attestation (attests with score=10, no vulns)
python3 -m src.main attest 0xYourContract

# Attest with a specific contract
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol
```

If `--contract-path` is provided, a quick detect-only audit runs first to populate vulnerability data.

---

### `serve`

Start the MCP server for IDE and agent integration.

```bash
python3 -m src.main serve
```

Runs the MCP server over stdio (production transport). See [MCP Integration](mcp.md) for details.

---

### `evaluate`

Run the evaluation framework against test cases.

```bash
python3 -m src.main evaluate
```

Executes all test cases in `data/vulnerabilities/` and produces a summary report.

---

## See Also

- [CLI Flags Reference](../reference/cli-flags.md) — every flag with defaults
- [Configuration Reference](../reference/config.md) — `.env` and `settings.yaml`
- [Quickstart](../getting-started/quickstart.md) — common workflows
