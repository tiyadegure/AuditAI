# CLI Flags Reference

> Every flag for every command, with types, defaults, and examples.

## Global

```bash
python3 -m src.main [OPTIONS] COMMAND [ARGS]
```

No global flags.

---

## `audit`

```bash
python3 -m src.main audit CONTRACT_PATH [OPTIONS]
```

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `CONTRACT_PATH` | — | Path (required) | — | Path to the `.sol` contract file |
| `--mode` | `-m` | Choice: `detect`, `patch`, `exploit`, `all` | `all` | How far to run the pipeline |
| `--output` | `-o` | Path | `None` | Save JSON results to file |
| `--max-patches` | — | Integer | `2` | Max vulnerabilities to patch (highest-severity first). Use `-1` for all |
| `--attest` | — | Flag | `False` | Attest results on-chain (EAS Sepolia) after completion |
| `--contract-address` | — | String | `None` | Contract address for on-chain attestation (required with `--attest`) |
| `--resume` | — | Flag | `False` | Resume from last checkpoint |

**Examples:**

```bash
# Full audit with defaults (patch top 2, no attestation)
python3 -m src.main audit data/contracts/VulnerableBank.sol

# Detection only
python3 -m src.main audit data/contracts/VulnerableBank.sol --mode detect

# Patch all vulnerabilities
python3 -m src.main audit data/contracts/VulnerableBank.sol --max-patches -1

# Audit + attestation
python3 -m src.main audit data/contracts/VulnerableBank.sol --attest --contract-address 0x1234...

# Save results
python3 -m src.main audit data/contracts/VulnerableBank.sol -o report.json

# Resume interrupted audit
python3 -m src.main audit data/contracts/VulnerableBank.sol --resume
```

---

## `detect`

```bash
python3 -m src.main detect CONTRACT_PATH [OPTIONS]
```

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `CONTRACT_PATH` | — | Path (required) | — | Path to the `.sol` contract file |
| `--multi-expert` | `-me` | Flag | `False` | Use multi-expert analysis (3 parallel LLM experts) |
| `--strategy` | `-s` | Choice: `ba`, `ta`, `all` | `all` | Detection strategy (LLM-SmartAudit §3.2) |

**Strategy values:**

| Value | Description |
|-------|-------------|
| `ba` | Broad Analysis — general vulnerability scan using ReAct prompting |
| `ta` | Targeted Analysis — checks specific vulnerability types in parallel |
| `all` | Both BA and TA (default) |

**Examples:**

```bash
# Standard detection
python3 -m src.main detect data/contracts/VulnerableBank.sol

# Multi-expert mode
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert

# Targeted only
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ta

# Broad only
python3 -m src.main detect data/contracts/VulnerableBank.sol --strategy ba
```

---

## `patch`

```bash
python3 -m src.main patch CONTRACT_PATH VULNERABILITY_ID
```

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_PATH` | Path (required) | Path to the `.sol` contract file |
| `VULNERABILITY_ID` | String (required) | ID from detect output (e.g., `slither-0`, `mimo-1`) |

**Example:**

```bash
python3 -m src.main patch data/contracts/VulnerableBank.sol slither-0
```

---

## `exploit`

```bash
python3 -m src.main exploit CONTRACT_ADDRESS EXPLOIT_CODE_PATH
```

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_ADDRESS` | String (required) | On-chain contract address |
| `EXPLOIT_CODE_PATH` | Path (required) | Path to Foundry exploit test file |

**Example:**

```bash
python3 -m src.main exploit 0x1234... tests/exploits/VulnerableBank_exploit.t.sol
```

---

## `attest`

```bash
python3 -m src.main attest CONTRACT_ADDRESS [OPTIONS]
```

| Argument | Type | Description |
|----------|------|-------------|
| `CONTRACT_ADDRESS` | String (required) | Contract address for the attestation |
| `--contract-path` | Path | Path to contract source (auto-detects from audit history if omitted) |

**Examples:**

```bash
# Standalone (score=10, no vulns)
python3 -m src.main attest 0xYourContract

# With contract source (runs detect first)
python3 -m src.main attest 0xYourContract --contract-path data/contracts/VulnerableBank.sol
```

---

## `serve`

```bash
python3 -m src.main serve
```

No flags. Starts the MCP server over stdio.

---

## `evaluate`

```bash
python3 -m src.main evaluate
```

No flags. Runs evaluation on test cases in `data/vulnerabilities/`.

---

## See Also

- [CLI Reference](../user-guide/cli.md) — command descriptions and workflows
- [Configuration Reference](config.md) — `.env` and `settings.yaml`
- [Quickstart](../getting-started/quickstart.md) — common usage patterns
