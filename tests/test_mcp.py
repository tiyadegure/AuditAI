"""
End-to-end test for the MCP server.

Tests both transports:
1. Manual JSON-RPC dispatch (handle_request) — no API key needed
2. Official MCP SDK stdio transport — spawns the server as a subprocess
   and connects with a real MCP client.

Run: python3 tests/test_mcp.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mcp import MCPServer


# --------------------------------------------------------------------------- #
# 1. JSON-RPC layer (in-process, no subprocess, no API key)
# --------------------------------------------------------------------------- #
async def test_jsonrpc_layer():
    print("=== Test 1: JSON-RPC layer ===")
    server = MCPServer()

    # initialize
    resp = await server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert resp["result"]["serverInfo"]["name"] == "smart-contract-audit"
    print("  [OK] initialize")

    # tools/list
    resp = await server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in resp["result"]["tools"]]
    assert names == ["analyze_contract", "get_vulnerability_details", "generate_report"], names
    print(f"  [OK] tools/list -> {names}")

    # tools/call generate_report (markdown)
    resp = await server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "generate_report",
            "arguments": {
                "audit_result": {
                    "contract_path": "VulnerableBank.sol",
                    "vulnerabilities": [
                        {"type": "reentrancy", "severity": "High",
                         "description": "External call before state update"},
                    ],
                },
                "format": "markdown",
            },
        },
    })
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert "Smart Contract Audit Report" in payload["report"]
    assert "reentrancy" in payload["report"]
    print("  [OK] tools/call generate_report")

    # unknown method
    resp = await server.handle_request({"jsonrpc": "2.0", "id": 4, "method": "does/not/exist"})
    assert resp["error"]["code"] == -32601
    print("  [OK] unknown method -> -32601")

    # unknown tool
    resp = await server.handle_request({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "nope", "arguments": {}},
    })
    assert resp["error"]["code"] == -32602
    print("  [OK] unknown tool -> -32602")


# --------------------------------------------------------------------------- #
# 2. get_vulnerability_details — exercises RAG knowledge base (no API key)
# --------------------------------------------------------------------------- #
async def test_vulnerability_details():
    print("\n=== Test 2: get_vulnerability_details (RAG) ===")
    server = MCPServer()
    resp = await server.handle_request({
        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
        "params": {
            "name": "get_vulnerability_details",
            "arguments": {"vulnerability_type": "reentrancy"},
        },
    })
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["vulnerability_type"] == "reentrancy"
    assert isinstance(payload["details"], list)
    print(f"  [OK] get_vulnerability_details -> {len(payload['details'])} docs retrieved")


# --------------------------------------------------------------------------- #
# 3. Real stdio transport via the official MCP SDK client
# --------------------------------------------------------------------------- #
async def test_stdio_transport():
    print("\n=== Test 3: stdio transport (official MCP client) ===")
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        print(f"  [SKIP] MCP client SDK unavailable: {e}")
        return

    repo_root = Path(__file__).resolve().parent.parent
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tests.mcp_stdio_entry"],
        cwd=str(repo_root),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  [OK] client initialize handshake")

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            assert "generate_report" in names, names
            print(f"  [OK] list_tools -> {names}")

            result = await session.call_tool("generate_report", {
                "audit_result": {
                    "contract_path": "X.sol",
                    "vulnerabilities": [{"type": "overflow", "severity": "Medium"}],
                },
                "format": "markdown",
            })
            text = result.content[0].text
            payload = json.loads(text)
            assert "overflow" in payload["report"]
            print("  [OK] call_tool generate_report over stdio")


async def test_stdio_analyze():
    """Full audit via stdio transport — requires MIMO_API_KEY env var."""
    import os
    api_key = os.environ.get("MIMO_API_KEY")
    if not api_key:
        print("\n=== Test 4: stdio analyze_contract (skipped, no MIMO_API_KEY) ===")
        return

    print("\n=== Test 4: stdio analyze_contract (full audit) ===")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    repo_root = Path(__file__).resolve().parent.parent
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tests.mcp_stdio_entry"],
        cwd=str(repo_root),
        env={"MIMO_API_KEY": api_key, "PATH": os.environ.get("PATH", "")},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("analyze_contract", {
                "contract_path": "data/contracts/VulnerableBank.sol",
                "mode": "detect",
            })
            payload = json.loads(result.content[0].text)
            vulns = payload.get("vulnerabilities", [])
            assert len(vulns) > 0, "Expected at least 1 vulnerability"
            print(f"  [OK] {len(vulns)} vulnerabilities via stdio transport")


async def main():
    await test_jsonrpc_layer()
    await test_vulnerability_details()
    await test_stdio_transport()
    await test_stdio_analyze()
    print("\nAll MCP server tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
