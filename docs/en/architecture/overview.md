# Architecture Overview

> A 5-layer, 5-agent pipeline for autonomous smart contract security auditing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI / MCP Server                            │
│  audit · detect · patch · exploit · attest · serve · evaluate   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │   Orchestrator   │
                  │  (coordinates    │
                  │   all agents)    │
                  └───┬──┬──┬──┬──┬┘
                      │  │  │  │  │
         ┌────────────┘  │  │  └────────────┐
         ▼               ▼  │               ▼
    ┌─────────┐   ┌─────────┐        ┌─────────┐
    │Auditor  │   │Architect│        │Validator│
    │detect   │   │design   │        │verify   │
    └────┬────┘   └────┬────┘        └────┬────┘
         │             │                   │
         ▼             ▼                   ▼
    ┌─────────┐  ┌──────────┐      ┌──────────────┐
    │Slither  │  │  Code    │      │  Concrete    │
    │Aderyn   │  │Generator │      │  Execution   │
    │RAG KB   │  │  patch   │      │  (Foundry)   │
    │MiMo BA  │  └────┬─────┘      └──────┬───────┘
    │MiMo TA  │       ▼                   │
    └─────────┘  ┌─────────┐              ▼
                 │Refiner  │       ┌──────────────┐
                 │improve  │       │ EAS Sepolia  │
                 └─────────┘       │ On-Chain     │
                                   │ Attestation  │
                                   └──────────────┘
```

## The Five Layers

### Layer 1: Detection

**Agents:** Auditor  
**Tools:** Slither, Aderyn, MiMo LLM, RAG Knowledge Base

Runs multiple detection engines in parallel:
- **Slither** — Solidity static analysis
- **Aderyn** — Rust-based static analysis
- **MiMo LLM** — AI-based code analysis (Broad Analysis + Targeted Analysis)
- **RAG** — vector search over 2,450 knowledge chunks

Results are merged, deduplicated, and scored by consensus (how many engines agree).

### Layer 2: Strategy

**Agent:** Architect  
**Input:** Vulnerability + contract code  
**Output:** Repair strategy

Designs a repair approach for each vulnerability — what pattern to apply, what to change, and what invariants to preserve.

### Layer 3: Generation

**Agents:** Code Generator, Refiner  
**Input:** Strategy + contract code  
**Output:** Patched Solidity code

Code Generator produces an initial patch. Refiner iterates to improve quality and ensure correctness.

### Layer 4: Verification

**Agent:** Validator  
**Tool:** Foundry (concrete execution)

Runs the patched code through Foundry invariant tests and exploit PoCs to verify the fix works and doesn't introduce new issues.

### Layer 5: Attestation

**Tool:** EAS Sepolia  
**Input:** Audit score, vulnerability count, contract address  
**Output:** On-chain attestation transaction

Posts audit results to Ethereum Attestation Service, producing a publicly verifiable credential.

## Data Flow

```
.sol file
   │
   ▼
[Detection] ─── Slither ──┐
               Aderyn ────┤
               MiMo BA ───┼──► Merge ──► Consensus Score
               MiMo TA ───┤
               RAG KB ────┘
                │
                ▼
         vulnerabilities (list[dict])
                │
                ▼
[Strategy] ── Architect ──► repair strategy
                │
                ▼
[Generation] ── CodeGen ──► Refiner ──► patch
                │
                ▼
[Verification] ─ Validator (Foundry) ──► pass/fail
                │
                ▼
[Attestation] ─ EAS Sepolia ──► tx hash
                │
                ▼
         AuditResult (JSON + console)
```

## Checkpoint & Resume

Long-running audits can be interrupted and resumed:

```bash
# First run (interrupted)
python3 -m src.main audit data/contracts/VulnerableBank.sol

# Resume from last checkpoint
python3 -m src.main audit data/contracts/VulnerableBank.sol --resume
```

The orchestrator saves checkpoints after each phase (`detect`, `patch`, `verify`) and can resume from the last completed step.

## See Also

- [Detection Layer](detection.md) — Slither, Aderyn, LLM, RAG details
- [Knowledge Layer](knowledge.md) — ChromaDB and RAG pipeline
- [Fuzzing & PoC](fuzzing.md) — Foundry invariant tests
- [Chain Layer](chain.md) — EAS attestation internals
