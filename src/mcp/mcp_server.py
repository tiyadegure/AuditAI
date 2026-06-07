"""
MCP Server
Expose audit tools via MCP protocol.

Two transports are supported:
1. Official MCP SDK stdio transport (production) — `start()` / `start_stdio()`
2. Manual JSON-RPC dispatch (`handle_request`) — used for HTTP/SSE and tests

Reference: MCP Python SDK (modelcontextprotocol/python-sdk)
"""

import json
import asyncio
from typing import Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MCPServer:
    """
    MCP Server: Expose audit tools via MCP protocol.

    Tools:
    1. analyze_contract        - run full audit (detect/patch/exploit/all)
    2. get_vulnerability_details - RAG lookup of a vulnerability class
    3. generate_report         - render an audit result as markdown/json
    """

    def __init__(self, name: str = "smart-contract-audit", version: str = "1.0.0",
                 context_repo_path: str = ".context-repo"):
        self.name = name
        self.version = version
        self.context_repo_path = context_repo_path
        self.tools = {}
        self._knowledge = None  # lazily initialised KnowledgeBase
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default audit tools"""
        self.tools = {
            "analyze_contract": {
                "name": "analyze_contract",
                "description": "Analyze a smart contract for vulnerabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "contract_path": {
                            "type": "string",
                            "description": "Path to the Solidity contract file",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["detect", "patch", "exploit", "all"],
                            "description": "Analysis mode",
                            "default": "all",
                        },
                    },
                    "required": ["contract_path"],
                },
            },
            "get_vulnerability_details": {
                "name": "get_vulnerability_details",
                "description": "Get details of a specific vulnerability type",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vulnerability_type": {
                            "type": "string",
                            "description": "Vulnerability type (e.g., reentrancy, overflow)",
                        },
                    },
                    "required": ["vulnerability_type"],
                },
            },
            "generate_report": {
                "name": "generate_report",
                "description": "Generate an audit report",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "audit_result": {
                            "type": "object",
                            "description": "Audit result to generate report from",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "markdown", "html"],
                            "description": "Report format",
                            "default": "markdown",
                        },
                    },
                    "required": ["audit_result"],
                },
            },
        }

    async def _get_knowledge(self):
        """Lazily build and initialise the knowledge base (loads forefy/.context)."""
        if self._knowledge is None:
            from ..knowledge import KnowledgeBase
            kb = KnowledgeBase(context_repo_path=self.context_repo_path)
            await kb.initialize()
            self._knowledge = kb
        return self._knowledge

    # ------------------------------------------------------------------ #
    # Manual JSON-RPC dispatch (used for HTTP/SSE and tests)
    # ------------------------------------------------------------------ #
    async def handle_request(self, request: dict) -> dict:
        """Handle a single MCP JSON-RPC request and return the response dict."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._handle_initialize(request_id)
            elif method == "tools/list":
                return self._handle_list_tools(request_id)
            elif method == "tools/call":
                return await self._handle_call_tool(request_id, params)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            return self._error_response(request_id, -32603, str(e))

    def _handle_initialize(self, request_id: Any) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.name, "version": self.version},
            },
        }

    def _handle_list_tools(self, request_id: Any) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": list(self.tools.values())},
        }

    async def _handle_call_tool(self, request_id: Any, params: dict) -> dict:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._error_response(request_id, -32602, f"Unknown tool: {tool_name}")

        result = await self._dispatch_tool(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}],
            },
        }

    async def _dispatch_tool(self, tool_name: str, arguments: dict) -> dict:
        """Shared tool dispatch used by both transports."""
        if tool_name == "analyze_contract":
            return await self._handle_analyze_contract(arguments)
        elif tool_name == "get_vulnerability_details":
            return await self._handle_get_vulnerability_details(arguments)
        elif tool_name == "generate_report":
            return await self._handle_generate_report(arguments)
        raise ValueError(f"Handler not implemented: {tool_name}")

    async def _handle_analyze_contract(self, arguments: dict) -> dict:
        from ..agents import AgentOrchestrator

        contract_path = arguments.get("contract_path")
        mode = arguments.get("mode", "all")

        orchestrator = AgentOrchestrator(context_repo_path=self.context_repo_path)
        await orchestrator.initialize()
        result = await orchestrator.audit(contract_path, mode)

        return result.to_dict() if hasattr(result, "to_dict") else json.loads(result.to_json())

    async def _handle_get_vulnerability_details(self, arguments: dict) -> dict:
        vuln_type = arguments.get("vulnerability_type")

        kb = await self._get_knowledge()
        results = await kb.query(f"vulnerability {vuln_type}")

        return {
            "vulnerability_type": vuln_type,
            "details": results,
        }

    async def _handle_generate_report(self, arguments: dict) -> dict:
        audit_result = arguments.get("audit_result", {})
        format_type = arguments.get("format", "markdown")

        if format_type == "markdown":
            return self._generate_markdown_report(audit_result)
        return audit_result

    def _generate_markdown_report(self, audit_result: dict) -> dict:
        report = "# Smart Contract Audit Report\n\n"

        contract = audit_result.get("contract_path", "Unknown")
        report += f"## Contract: {contract}\n\n"

        vulns = audit_result.get("vulnerabilities", [])
        report += f"## Vulnerabilities Found: {len(vulns)}\n\n"

        for i, vuln in enumerate(vulns, 1):
            report += f"### {i}. {vuln.get('type', 'Unknown')}\n"
            report += f"- **Severity**: {vuln.get('severity', 'Medium')}\n"
            report += f"- **Description**: {vuln.get('description', 'N/A')}\n\n"

        return {"report": report, "format": "markdown"}

    def _error_response(self, request_id: Any, code: int, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    # ------------------------------------------------------------------ #
    # Official MCP SDK stdio transport (production)
    # ------------------------------------------------------------------ #
    def _build_sdk_server(self):
        """Build a low-level MCP SDK Server wired to our tool handlers."""
        from mcp.server.lowlevel import Server
        import mcp.types as types

        server = Server(self.name)

        @server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"],
                )
                for t in self.tools.values()
            ]

        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name not in self.tools:
                raise ValueError(f"Unknown tool: {name}")
            result = await self._dispatch_tool(name, arguments or {})
            return [types.TextContent(type="text", text=json.dumps(result))]

        return server

    async def start_stdio(self):
        """Run the MCP server over stdio using the official SDK."""
        from mcp.server.lowlevel import NotificationOptions
        from mcp.server.models import InitializationOptions
        from mcp.server.stdio import stdio_server

        server = self._build_sdk_server()

        init_options = InitializationOptions(
            server_name=self.name,
            server_version=self.version,
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )

        logger.info(f"Starting MCP server '{self.name}' v{self.version} over stdio")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, init_options)

    async def start(self, transport: str = "stdio", host: str = "0.0.0.0", port: int = 8080):
        """
        Start the MCP server.

        Args:
            transport: "stdio" (default, production) — connects to MCP clients
                       over stdin/stdout via the official SDK.
        """
        if transport == "stdio":
            await self.start_stdio()
        else:
            raise ValueError(f"Unsupported transport: {transport}")
