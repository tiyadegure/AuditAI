# Knowledge Layer

> How AuditAI's RAG knowledge base works — 2,450 chunks of vulnerability knowledge embedded in ChromaDB.

## Overview

The knowledge layer provides context-aware retrieval of vulnerability patterns, audit reports, and security documentation. It uses **ChromaDB** as a vector store with **all-MiniLM-L6-v2** embeddings, falling back to keyword search if the embedding model is unavailable.

## Data Sources

### 1. Vulnerability Reference Docs (303 files)

Located in `data/knowledge/reference/` (or `data/knowledge/reference/`). Contains vulnerability patterns organized by language and category:

```
data/knowledge/reference/
├── solidity/
│   ├── fv-sol-1-reentrancy/
│   ├── fv-sol-2-access-control/
│   └── ...
```

### 2. Top-Level Knowledge Files

Located in `data/knowledge/`:

| File | Type | Purpose |
|------|------|---------|
| `finding-format.md` | `finding_format` | Report template from forefy/.context |
| `solidity-checks.md` | `solidity_checks` | Solidity audit checklist |
| `multi-expert.md` | `multi_expert` | Multi-expert analysis framework |

### 3. Solodit Audit Reports (477 files)

Located in `data/solodit/`. Real-world audit reports indexed for RAG retrieval.

## Chunking Strategy

Documents are split by markdown headings (`##`, `###`, `####`), with a maximum chunk size of **1,500 characters**. Long sections are further split by paragraphs.

```python
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 80
```

This granularity is similar to the approach described in the SmartLLM paper §4.2.

## Embedding Model

**Model:** `all-MiniLM-L6-v2` from sentence-transformers

- 384-dimensional embeddings
- Fast inference, good semantic similarity
- Downloads from HuggingFace (uses `HF_ENDPOINT` mirror for China)

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
```

## ChromaDB Storage

Chunks are stored in a persistent ChromaDB collection:

```python
persist_dir = "data/knowledge/chromadb"
client = chromadb.PersistentClient(path=persist_dir)
collection = client.get_or_create_collection(
    name="smart_contract_security",
    metadata={"hnsw:space": "cosine"},
)
```

- **Cosine similarity** for vector search
- **Incremental indexing** — only missing documents are indexed on subsequent runs
- **Batch size:** 128 chunks per batch

## Query Flow

```python
results = await knowledge.query(query_text, top_k=5)
```

1. Encode query with `all-MiniLM-L6-v2`
2. Search ChromaDB for top-k similar chunks
3. Return results with `content`, `metadata`, and `score`

### Vector Search (default)

```python
results = collection.query(
    query_embeddings=[embedding],
    n_results=top_k,
    where={"type": filter_type} if filter_type else None,
)
```

### Keyword Fallback

If ChromaDB or the embedding model is unavailable, falls back to keyword matching:

```python
query_words = set(query_text.lower().split())
for doc in documents:
    hits = sum(1 for w in query_words if w in doc["content"].lower())
    results.append({"score": hits / len(query_words)})
```

## Adding Documents at Runtime

```python
await knowledge.add_document({
    "id": "custom-1",
    "content": "Reentrancy occurs when...",
    "metadata": {"type": "vulnerability_reference", "language": "solidity"},
})
```

The document is immediately embedded and added to ChromaDB.

## Configuration

In `config/settings.yaml`:

```yaml
knowledge:
  vector_store: "chromadb"
  embedding_model: "all-MiniLM-L6-v2"
  collection_name: "smart_contract_security"
  chunk_size: 1000
  chunk_overlap: 200
```

## See Also

- [Detection Layer](detection.md) — how RAG context is used in detection
- [Architecture Overview](overview.md) — full pipeline
- [Configuration Reference](../reference/config.md) — knowledge base settings
