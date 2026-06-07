"""
Knowledge Base with RAG Integration
Integrates forefy/.context knowledge for smart contract auditing
"""

import os
# Set HF mirror BEFORE any sentence_transformers import (huggingface.co is blocked in CN)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import re
from pathlib import Path
from typing import List, Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Maximum chunk size in characters (before splitting further)
MAX_CHUNK_CHARS = 1500
# Minimum chunk size to keep (skip tiny fragments)
MIN_CHUNK_CHARS = 80


class KnowledgeBase:
    """
    Knowledge Base: RAG-based knowledge retrieval for smart contract security.
    
    Loads vulnerability knowledge from forefy/.context reference docs,
    chunks them by heading/paragraph, embeds with all-MiniLM-L6-v2,
    and stores in ChromaDB for vector retrieval.
    
    Falls back to keyword search if chromadb/sentence-transformers unavailable.
    """

    def __init__(self, context_repo_path: str = ".context-repo", knowledge_path: str = "data/knowledge"):
        self.context_repo_path = Path(context_repo_path)
        self.knowledge_path = Path(knowledge_path)
        self.documents: List[Dict] = []       # all chunks with metadata
        self._embedding_model = None
        self._collection = None
        self._chroma_client = None
        self.using_vector_search = False

    # ------------------------------------------------------------------ init
    async def initialize(self):
        """Initialize the knowledge base: load docs → embed → index."""
        logger.info("Initializing knowledge base from forefy/.context")

        await self._load_context_repo()

        # Also load top-level knowledge files (finding-format.md, solidity-checks.md)
        await self._load_knowledge_dir()

        # Load Solodit reports if present
        await self._load_solodit_reports()

        await self._initialize_embeddings()
        await self._create_collection()

        logger.info(f"Knowledge base initialized with {len(self.documents)} chunks")

    # ------------------------------------------------------------------ loading
    async def _load_context_repo(self):
        """Load and chunk documents from data/knowledge/reference/."""
        ref_dir = self.knowledge_path / "reference"
        if not ref_dir.exists():
            # Fallback to .context-repo
            ref_dir = self.context_repo_path / "skills" / "smart-contract-audit" / "reference"
        if not ref_dir.exists():
            logger.warning(f"Reference directory not found: {ref_dir}")
            return

        md_files = sorted(ref_dir.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files in {ref_dir}")

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                if len(content.strip()) < 20:
                    continue

                relative_path = md_file.relative_to(ref_dir)
                parts = relative_path.parts  # e.g. ('solidity', 'fv-sol-1-reentrancy', 'file.md')

                language = parts[0] if len(parts) > 0 else "unknown"
                vuln_category = parts[1] if len(parts) > 1 else "general"

                chunks = self._chunk_markdown(content)
                for i, chunk_text in enumerate(chunks):
                    if len(chunk_text.strip()) < MIN_CHUNK_CHARS:
                        continue
                    chunk_id = f"ref-{relative_path}-{i}"
                    self.documents.append({
                        "id": chunk_id,
                        "content": chunk_text,
                        "metadata": {
                            "source_path": str(relative_path),
                            "language": language,
                            "vuln_category": vuln_category,
                            "type": "vulnerability_reference",
                            "chunk_index": i,
                        },
                    })
            except Exception as e:
                logger.warning(f"Failed to load {md_file}: {e}")

        logger.info(f"Loaded {len(self.documents)} chunks from reference directory")

    async def _load_knowledge_dir(self):
        """Load top-level knowledge files (finding-format, solidity-checks, multi-expert)."""
        if not self.knowledge_path.exists():
            logger.warning(f"Knowledge directory not found: {self.knowledge_path}")
            return

        # Only load .md files directly in knowledge_path (not in reference/ which is already loaded)
        for md_file in sorted(self.knowledge_path.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                if len(content.strip()) < 20:
                    continue

                chunks = self._chunk_markdown(content)
                for i, chunk_text in enumerate(chunks):
                    if len(chunk_text.strip()) < MIN_CHUNK_CHARS:
                        continue
                    chunk_id = f"knowledge-{md_file.stem}-{i}"
                    self.documents.append({
                        "id": chunk_id,
                        "content": chunk_text,
                        "metadata": {
                            "source_path": md_file.name,
                            "language": "general",
                            "vuln_category": md_file.stem,
                            "type": self._determine_doc_type(md_file.name),
                            "chunk_index": i,
                        },
                    })
            except Exception as e:
                logger.warning(f"Failed to load {md_file}: {e}")

        logger.info(f"Total chunks after knowledge dir: {len(self.documents)}")

    # ------------------------------------------------------------------ chunking
    def _chunk_markdown(self, content: str) -> List[str]:
        """
        Split markdown into chunks by headings (## / ### / ####).
        Falls back to paragraph splitting for long sections.
        Similar to the chunk granularity described in SmartLLM paper §4.2.
        """
        # Split on markdown headings (## or deeper)
        heading_pattern = re.compile(r"^(#{2,4}\s+.+)$", re.MULTILINE)
        parts = heading_pattern.split(content)

        # parts alternates: [preamble, heading1, body1, heading2, body2, ...]
        chunks = []
        current = ""
        for part in parts:
            candidate = (current + "\n" + part).strip() if current else part.strip()
            if len(candidate) > MAX_CHUNK_CHARS and current:
                # Flush current chunk before adding more
                chunks.append(current.strip())
                current = part.strip()
            else:
                current = candidate

        if current.strip():
            # If still too long, split by paragraphs
            if len(current) > MAX_CHUNK_CHARS:
                chunks.extend(self._split_by_paragraph(current))
            else:
                chunks.append(current.strip())

        return [c for c in chunks if c]

    def _split_by_paragraph(self, text: str) -> List[str]:
        """Split long text by double newlines (paragraphs)."""
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            candidate = (current + "\n\n" + para).strip() if current else para
            if len(candidate) > MAX_CHUNK_CHARS and current:
                chunks.append(current.strip())
                current = para
            else:
                current = candidate
        if current.strip():
            chunks.append(current.strip())
        return chunks

    # ------------------------------------------------------------------ embeddings
    async def _initialize_embeddings(self):
        """Initialize sentence-transformers embedding model."""
        self.using_vector_search = False
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model all-MiniLM-L6-v2 via %s ...",
                        os.environ.get("HF_ENDPOINT", "huggingface.co"))
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.using_vector_search = True
            logger.info("Embedding model loaded — VECTOR SEARCH ACTIVE")
        except (ImportError, OSError, RuntimeError, Exception) as e:
            logger.warning("=" * 60)
            logger.warning("EMBEDDING MODEL FAILED TO LOAD: %s", e)
            logger.warning("FALLING BACK TO KEYWORD SEARCH — vector RAG is OFF")
            logger.warning("=" * 60)
            self._embedding_model = None

    # ------------------------------------------------------------------ chromadb
    async def _create_collection(self):
        """Create (or get) ChromaDB persistent collection and index all chunks."""
        if not self._embedding_model:
            logger.warning("No embedding model; skipping ChromaDB collection")
            return

        try:
            import chromadb

            persist_dir = str(self.knowledge_path / "chromadb")
            self._chroma_client = chromadb.PersistentClient(path=persist_dir)
            self._collection = self._chroma_client.get_or_create_collection(
                name="smart_contract_security",
                metadata={"description": "Smart contract security knowledge base", "hnsw:space": "cosine"},
            )

            existing = self._collection.count()
            if existing > 0:
                logger.info(f"ChromaDB collection has {existing} entries; indexing only missing docs")
                await self._index_missing_documents()
            else:
                await self._index_documents()
        except ImportError:
            logger.warning("chromadb not installed; falling back to keyword search")
            self._collection = None
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            self._collection = None

    async def _index_documents(self):
        """Embed all chunks and add to ChromaDB collection."""
        if not self._collection or not self._embedding_model:
            return

        batch_size = 128
        total = len(self.documents)
        logger.info(f"Indexing {total} chunks into ChromaDB (batch={batch_size}) ...")

        for start in range(0, total, batch_size):
            batch = self.documents[start : start + batch_size]
            ids = [d["id"] for d in batch]
            texts = [d["content"] for d in batch]
            metadatas = [d["metadata"] for d in batch]

            embeddings = self._embedding_model.encode(texts, show_progress_bar=False).tolist()

            self._collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
            if (start // batch_size) % 5 == 0:
                logger.info(f"  indexed {min(start + batch_size, total)}/{total}")

        logger.info(f"Indexed {total} chunks into ChromaDB")

    async def _index_missing_documents(self):
        """Index only documents not yet in the ChromaDB collection."""
        if not self._collection or not self._embedding_model:
            return

        existing_ids = set(self._collection.get(include=["documents"])["ids"])
        missing = [d for d in self.documents if d["id"] not in existing_ids]

        if not missing:
            logger.info("No missing documents — ChromaDB is up to date")
            return

        batch_size = 128
        total = len(missing)
        logger.info(f"Indexing {total} missing chunks into ChromaDB (batch={batch_size}) ...")

        for start in range(0, total, batch_size):
            batch = missing[start : start + batch_size]
            ids = [d["id"] for d in batch]
            texts = [d["content"] for d in batch]
            metadatas = [d["metadata"] for d in batch]

            embeddings = self._embedding_model.encode(texts, show_progress_bar=False).tolist()
            self._collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

        logger.info(f"Indexed {total} missing chunks into ChromaDB")

    # ------------------------------------------------------------------ query
    async def query(self, query_text: str, filter_type: str = None, top_k: int = 5) -> list:
        """
        Vector retrieval over the knowledge base.

        Args:
            query_text: natural-language query
            filter_type: optional metadata filter (e.g. "vulnerability_reference")
            top_k: number of results

        Returns:
            List of dicts with keys: content, metadata, score
        """
        logger.info(f"Querying: {query_text[:80]}...")

        if self._collection and self._embedding_model:
            return self._vector_query(query_text, filter_type, top_k)
        else:
            return self._simple_search(query_text, filter_type, top_k)

    def _vector_query(self, query_text: str, filter_type: Optional[str], top_k: int) -> list:
        """ChromaDB vector search."""
        try:
            where = {"type": filter_type} if filter_type else None
            results = self._collection.query(
                query_embeddings=[self._embedding_model.encode(query_text).tolist()],
                n_results=top_k,
                where=where,
            )
            formatted = []
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1.0 - results["distances"][0][i] if results["distances"] else 0,
                })
            return formatted
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return self._simple_search(query_text, filter_type, top_k)

    def _simple_search(self, query_text: str, filter_type: Optional[str], top_k: int) -> list:
        """Keyword-based fallback search."""
        logger.info("Using simple keyword search fallback")
        results = []
        query_words = set(query_text.lower().split())

        for doc in self.documents:
            if filter_type and doc["metadata"].get("type") != filter_type:
                continue
            content_lower = doc["content"].lower()
            hits = sum(1 for w in query_words if w in content_lower)
            if hits > 0:
                results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": hits / max(len(query_words), 1),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------ helpers
    def _determine_doc_type(self, filename: str) -> str:
        name = filename.lower()
        if "finding" in name:
            return "finding_format"
        elif "solidity-check" in name:
            return "solidity_checks"
        elif "multi-expert" in name:
            return "multi_expert"
        return "general"

    async def add_document(self, document: dict):
        """Add a single document at runtime."""
        self.documents.append(document)
        if self._collection and self._embedding_model:
            emb = self._embedding_model.encode(document["content"]).tolist()
            self._collection.add(
                ids=[document["id"]],
                documents=[document["content"]],
                metadatas=[document.get("metadata", {})],
                embeddings=[emb],
            )

    async def _load_solodit_reports(self):
        """Load Solodit audit reports from data/solodit/ if present."""
        solodit_dir = Path("data/solodit")
        if not solodit_dir.exists():
            logger.info("No data/solodit/ directory — skipping Solodit reports")
            return

        md_files = sorted(solodit_dir.rglob("*.md"))
        logger.info(f"Found {len(md_files)} Solodit report files in {solodit_dir}")

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                if len(content.strip()) < 20:
                    continue

                chunks = self._chunk_markdown(content)
                for i, chunk_text in enumerate(chunks):
                    if len(chunk_text.strip()) < MIN_CHUNK_CHARS:
                        continue
                    chunk_id = f"solodit-{md_file.stem}-{i}"
                    self.documents.append({
                        "id": chunk_id,
                        "content": chunk_text,
                        "metadata": {
                            "source_path": str(md_file),
                            "language": "solidity",
                            "vuln_category": "solodit",
                            "type": "solodit",
                            "chunk_index": i,
                        },
                    })
            except Exception as e:
                logger.warning(f"Failed to load Solodit report {md_file}: {e}")

        logger.info(f"Loaded {len(md_files)} Solodit reports, total chunks now: {len(self.documents)}")

    # Keep legacy loaders as no-ops (already handled in _load_context_repo / _load_knowledge_dir)
    async def load_vulnerability_patterns(self):
        pass

    async def load_repair_strategies(self):
        pass

    async def load_code_patterns(self):
        pass

    async def load_audit_guides(self):
        pass

    async def load_all_knowledge(self):
        pass
