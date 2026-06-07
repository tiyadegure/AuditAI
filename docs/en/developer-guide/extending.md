# Extending AuditAI

> Add new detectors, tools, MCP tools, and knowledge to AuditAI.

## Adding a New Detector

### 1. Create the Tool

Create a new file in `src/tools/`:

```python
# src/tools/my_detector.py
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MyDetector:
    def __init__(self):
        pass

    def analyze(self, contract_path: str) -> list[dict]:
        """Analyze a contract and return findings."""
        # Your detection logic here
        return [
            {
                "check": "my-finding-type",
                "impact": "High",
                "location": "function:line",
                "description": "Description of the finding",
            }
        ]
```

### 2. Register in ToolKit

Add to `src/tools/__init__.py`:

```python
from .my_detector import MyDetector

class ToolKit:
    def __init__(self):
        # ... existing tools ...
        self.my_detector = MyDetector()
```

### 3. Use in Auditor

Add a new method to `src/agents/auditor.py`:

```python
async def _run_my_detector(self, contract_path: str) -> list[dict]:
    logger.info("Running MyDetector analysis")
    results = self.tools.my_detector.analyze(contract_path)
    return [
        {
            "id": f"my-detector-{i}",
            "type": r["check"],
            "severity": r["impact"],
            "location": r["location"],
            "description": r["description"],
            "source": "my-detector",
        }
        for i, r in enumerate(results)
    ]
```

### 4. Add to Parallel Detection

In `detect()`, add your detector to the `asyncio.gather()`:

```python
slither_results, aderyn_results, llm_results, my_results = await asyncio.gather(
    self._run_slither(contract_path),
    self._run_aderyn(contract_path),
    self._run_llm_analysis(sanitized_code),
    self._run_my_detector(contract_path),
)
```

### 5. Register in Detector Families

Add to `_DETECTOR_FAMILIES` for consensus scoring:

```python
_DETECTOR_FAMILIES = ("slither", "aderyn", "mimo", "ba", "ta", "expert1", "expert2", "triager", "my-detector")
```

## Adding a New Tool to Toolkit

### 1. Create the Tool

```python
# src/tools/my_tool.py
class MyTool:
    def run(self, **kwargs):
        # Your tool logic
        return {"result": "..."}
```

### 2. Register

```python
# src/tools/__init__.py
from .my_tool import MyTool

class ToolKit:
    def __init__(self):
        self.my_tool = MyTool()
```

## Adding a New MCP Tool

### 1. Define the Tool

In `src/mcp/mcp_server.py`, add to `_register_default_tools()`:

```python
self.tools["my_tool"] = {
    "name": "my_tool",
    "description": "Description of what my_tool does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "input_param": {
                "type": "string",
                "description": "Description of input_param",
            },
        },
        "required": ["input_param"],
    },
}
```

### 2. Add the Handler

```python
async def _handle_my_tool(self, arguments: dict) -> dict:
    input_param = arguments.get("input_param")
    # Your logic here
    return {"result": f"Processed {input_param}"}
```

### 3. Register in Dispatch

In `_dispatch_tool()`:

```python
async def _dispatch_tool(self, tool_name: str, arguments: dict) -> dict:
    if tool_name == "analyze_contract":
        return await self._handle_analyze_contract(arguments)
    elif tool_name == "my_tool":
        return await self._handle_my_tool(arguments)
    # ... etc
```

## Extending the Knowledge Base

### Adding New Documents

```python
from src.knowledge import KnowledgeBase

kb = KnowledgeBase()
await kb.initialize()

await kb.add_document({
    "id": "my-doc-1",
    "content": "Reentrancy occurs when an external call...",
    "metadata": {
        "type": "vulnerability_reference",
        "language": "solidity",
        "vuln_category": "reentrancy",
    },
})
```

### Adding a New Data Source

Create a loader method in `src/knowledge/knowledge_base.py`:

```python
async def _load_my_source(self):
    """Load documents from my custom source."""
    source_dir = Path("data/my-source")
    if not source_dir.exists():
        return

    for md_file in source_dir.rglob("*.md"):
        content = md_file.read_text()
        chunks = self._chunk_markdown(content)
        for i, chunk in enumerate(chunks):
            self.documents.append({
                "id": f"my-source-{md_file.stem}-{i}",
                "content": chunk,
                "metadata": {"type": "my_source", "source_path": str(md_file)},
            })
```

Call it from `initialize()`:

```python
async def initialize(self):
    await self._load_context_repo()
    await self._load_knowledge_dir()
    await self._load_solodit_reports()
    await self._load_my_source()  # <-- add this
    await self._initialize_embeddings()
    await self._create_collection()
```

## See Also

- [Contributing Guide](contributing.md) — development workflow
- [Architecture Overview](../architecture/overview.md) — system design
- [MCP Integration](../user-guide/mcp.md) — MCP server details
