# Detection Layer

> How AuditAI finds vulnerabilities using dual static analysis, LLM reasoning, and RAG knowledge.

## Overview

The detection layer runs multiple analysis engines in parallel, merges their results, and scores each finding by consensus. This produces high-confidence vulnerability reports with minimal false positives.

## Detection Engines

### Slither

[Slither](https://github.com/crytic/slither) is a Solidity static analysis framework by Trail of Bits. AuditAI wraps it via `src/tools/slither_tool.py`.

```python
results = self.tools.slither.analyze(contract_path)
```

**Output:** List of findings with `check`, `impact`, `location`, `description`.

### Aderyn

[Aderyn](https://github.com/Cyfrin/aderyn) is a Rust-based Solidity static analyzer. AuditAI wraps it via `src/tools/aderyn_tool.py`.

```python
results = self.tools.aderyn.analyze(contract_path)
```

**Output:** Same format as Slither — merged into the static analysis bucket.

### MiMo LLM Analysis

The primary AI engine uses **MiMo V2.5 Pro** for code analysis:

```python
result = await self.llm.analyze_code(contract_code)
```

The LLM receives the contract source and returns a JSON list of vulnerabilities.

### Broad Analysis (BA)

A ReAct-style prompt that asks the LLM to reason step-by-step through the entire contract:

```
You are a Smart Contract Auditor performing Broad Analysis (BA).
Use thought-reasoning: analyse the code step-by-step, identify potential issues,
cross-check with known vulnerability patterns, and verify your reasoning.
```

Checks for **general vulnerabilities** — reentrancy, access control, arithmetic issues, etc.

### Targeted Analysis (TA)

Sends **one prompt per known vulnerability type** in parallel:

```python
_TA_VULN_TYPES = [
    "reentrancy",
    "access_control",
    "integer_overflow",
    "front_running",
    "oracle_manipulation",
    "flash_loan_attack",
]
```

Each prompt checks specifically for one vulnerability class. If the contract is not vulnerable, it returns an empty list.

### Multi-Expert Analysis

Three parallel LLM "experts" from the forefy/.context framework:

1. **Expert 1** — Systematic, methodical, focused on core vulnerabilities (reentrancy, access control, arithmetic)
2. **Expert 2** — Fresh perspective, economic focus (flash loans, composability, oracle manipulation)
3. **Triager** — Validates and challenges findings, filters false positives

```bash
python3 -m src.main detect data/contracts/VulnerableBank.sol --multi-expert
```

## RAG Knowledge Retrieval

The Auditor queries the knowledge base for each contract to find relevant vulnerability patterns:

```python
rag_context = await self.knowledge.query(contract_code)
```

RAG context is used in:
- **Merging** — enriches findings with known patterns
- **Verificator** — fact-checks findings against known vulnerability documentation
- **Report** — tags each finding with the RAG sources that were consulted

## Result Merging

Findings from all engines are merged by `(type, location)` key:

```python
def _merge_results(self, slither_results, llm_results, rag_context):
    merged = {}
    for vuln in slither_results:
        key = f"{vuln['type']}-{vuln['location']}"
        if key not in merged:
            merged[key] = vuln
    for vuln in llm_results:
        key = f"{vuln['type']}-{vuln['location']}"
        merged[key] = vuln  # LLM overrides static analysis
    return list(merged.values())
```

LLM results take priority over static analysis results for the same key.

## Consensus Scoring

Each finding is scored by how many independent detector families flagged it:

```python
_DETECTOR_FAMILIES = ("slither", "aderyn", "mimo", "ba", "ta", "expert1", "expert2", "triager")

# confidence = number_of_agreeing_families / total_families
v["confidence"] = round(len(agree) / len(self._DETECTOR_FAMILIES), 3)
```

A finding flagged by 3 out of 8 families gets `confidence = 0.375`.

## Verificator (False Positive Reduction)

A final LLM pass fact-checks each finding against RAG knowledge:

```
You are a Smart Contract Vulnerability Verificator.
Your job is to fact-check a reported vulnerability finding against known vulnerability patterns
and the actual contract code.
```

- Only marks findings as `verified: False` on explicit "false positive" verdict
- Conservative: ambiguous responses keep findings as verified
- Runs with concurrency limit of 5 to avoid overwhelming the LLM

## Pipeline Summary

```
contract.sol
    │
    ├──► Slither ──────────────┐
    ├──► Aderyn ───────────────┤
    ├──► MiMo LLM ────────────┼──► Merge ──► Consensus Score ──► Verificator
    ├──► Broad Analysis (BA) ──┤
    ├──► Targeted Analysis ────┤
    └──► RAG Knowledge ────────┘
                                  │
                                  ▼
                          vulnerabilities[]
```

## See Also

- [Knowledge Layer](knowledge.md) — RAG pipeline details
- [Architecture Overview](overview.md) — full pipeline
- [CLI Reference](../user-guide/cli.md) — `detect` and `--strategy` flags
