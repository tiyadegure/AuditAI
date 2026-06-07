"""
stdio entry point for the MCP server, used by test_mcp.py's stdio transport test.

Run as: python3 -m tests.mcp_stdio_entry
The official MCP SDK client spawns this as a subprocess and talks JSON-RPC
over stdin/stdout.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mcp import MCPServer


def main():
    server = MCPServer()
    asyncio.run(server.start(transport="stdio"))


if __name__ == "__main__":
    main()
