# 知识层

> AuditAI 的 RAG 知识库如何工作 — 2,450 块漏洞知识嵌入 ChromaDB。

## 概述

知识层提供上下文感知的漏洞模式、审计报告和安全文档检索。使用 **ChromaDB** 作为向量存储，**all-MiniLM-L6-v2** 嵌入模型，如果嵌入模型不可用则回退到关键词搜索。

## 数据源

### 1. 漏洞参考文档（303 个文件）

位于 `data/knowledge/reference/`（或 `data/knowledge/reference/`）。包含按语言和类别组织的漏洞模式：

```
data/knowledge/reference/
├── solidity/
│   ├── fv-sol-1-reentrancy/
│   ├── fv-sol-2-access-control/
│   └── ...
```

### 2. 顶层知识文件

位于 `data/knowledge/`：

| 文件 | 类型 | 用途 |
|------|------|------|
| `finding-format.md` | `finding_format` | forefy/.context 报告模板 |
| `solidity-checks.md` | `solidity_checks` | Solidity 审计检查清单 |
| `multi-expert.md` | `multi_expert` | 多专家分析框架 |

### 3. Solodit 审计报告（477 个文件）

位于 `data/solodit/`。为 RAG 检索索引的真实审计报告。

## 分块策略

文档按 Markdown 标题（`##`、`###`、`####`）分割，最大块大小 **1,500 字符**。长段落进一步按段落分割。

```python
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 80
```

此粒度类似于 SmartLLM 论文 §4.2 中描述的方法。

## 嵌入模型

**模型：** `all-MiniLM-L6-v2`（sentence-transformers）

- 384 维嵌入
- 推理速度快，语义相似度好
- 从 HuggingFace 下载（中国使用 `HF_ENDPOINT` 镜像）

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
```

## ChromaDB 存储

块存储在持久化 ChromaDB 集合中：

```python
persist_dir = "data/knowledge/chromadb"
client = chromadb.PersistentClient(path=persist_dir)
collection = client.get_or_create_collection(
    name="smart_contract_security",
    metadata={"hnsw:space": "cosine"},
)
```

- **余弦相似度**用于向量搜索
- **增量索引** — 后续运行仅索引缺失的文档
- **批处理大小：** 每批 128 块

## 查询流程

```python
results = await knowledge.query(query_text, top_k=5)
```

1. 使用 `all-MiniLM-L6-v2` 编码查询
2. 在 ChromaDB 中搜索 top-k 相似块
3. 返回包含 `content`、`metadata` 和 `score` 的结果

### 向量搜索（默认）

```python
results = collection.query(
    query_embeddings=[embedding],
    n_results=top_k,
    where={"type": filter_type} if filter_type else None,
)
```

### 关键词回退

如果 ChromaDB 或嵌入模型不可用，回退到关键词匹配：

```python
query_words = set(query_text.lower().split())
for doc in documents:
    hits = sum(1 for w in query_words if w in doc["content"].lower())
    results.append({"score": hits / len(query_words)})
```

## 运行时添加文档

```python
await knowledge.add_document({
    "id": "custom-1",
    "content": "Reentrancy occurs when...",
    "metadata": {"type": "vulnerability_reference", "language": "solidity"},
})
```

文档会立即嵌入并添加到 ChromaDB。

## 配置

在 `config/settings.yaml` 中：

```yaml
knowledge:
  vector_store: "chromadb"
  embedding_model: "all-MiniLM-L6-v2"
  collection_name: "smart_contract_security"
  chunk_size: 1000
  chunk_overlap: 200
```

## 另请参阅

- [检测层](detection.md) — RAG 上下文在检测中的使用
- [架构概述](overview.md) — 完整流水线
- [配置参考](../reference/config.md) — 知识库设置
