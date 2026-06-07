# MCP Integration

> Expose AuditAI tools to external agents and IDE integrations via Model Context Protocol.

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is a standard for connecting AI models to external tools and data sources. AuditAI implements an MCP server that exposes smart contract audit capabilities as MCP tools, allowing any MCP-compatible client (Cursor, Claude, etc.) to run audits.

## Starting the MCP Server

```bash
# Production — stdio transport (connects to MCP clients)
python3 -m src.main serve
```

The server runs over **stdio** by default (stdin/stdout), which is the standard transport for MCP clients.

## Connecting from IDEs

### Cursor

1. Open **Settings → MCP**
2. Add a new MCP server:
   - **Type**: `stdio`
   - **Command**: `python3 -m src.main serve`
   - **Working directory**: `/path/to/eth-beijing-2026`

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "auditai": {
      "command": "python3",
      "args": ["-m", "src.main", "serve"],
      "cwd": "/path/to/eth-beijing-2026"
    }
  }
}
```

## Available Tools

The MCP server exposes three tools:

### `analyze_contract`

Run a full smart contract audit.

**Input Schema:**

```json
{
  "contract_path": "string (required) — path to the .sol file",
  "mode": "string — 'detect', 'patch', 'exploit', or 'all' (default: 'all')"
}
```

**Example call:**

```json
{
  "name": "analyze_contract",
  "arguments": {
    "contract_path": "data/contracts/VulnerableBank.sol",
    "mode": "all"
  }
}
```

**Returns:** Full audit result with vulnerabilities, patches, and verification.

---

### `get_vulnerability_details`

Look up a vulnerability type from the RAG knowledge base.

**Input Schema:**

```json
{
  "vulnerability_type": "string (required) — e.g., 'reentrancy', 'overflow'"
}
```

**Example call:**

```json
{
  "name": "get_vulnerability_details",
  "arguments": {
    "vulnerability_type": "reentrancy"
  }
}
```

**Returns:** Relevant knowledge base entries about the vulnerability type.

---

### `generate_report`

Generate a formatted audit report from audit results.

**Input Schema:**

```json
{
  "audit_result": "object (required) — audit result object",
  "format": "string — 'json', 'markdown', or 'html' (default: 'markdown')"
}
```

**Example call:**

```json
{
  "name": "generate_report",
  "arguments": {
    "audit_result": { "contract_path": "...", "vulnerabilities": [...] },
    "format": "markdown"
  }
}
```

## Protocol Details

The server implements MCP protocol version `2024-11-05` and supports:

- **`initialize`** — server handshake
- **`tools/list`** — list available tools
- **`tools/call`** — invoke a tool

It also supports a manual JSON-RPC dispatch mode for HTTP/SSE transports and testing.

## Extending the MCP Server

To add new tools, edit `src/mcp/mcp_server.py`:

1. Add a tool definition to `_register_default_tools()`
2. Add a handler method (e.g., `_handle_my_tool`)
3. Register the handler in `_dispatch_tool()`

See [Extending Guide](../developer-guide/extending.md) for details.

## See Also

- [CLI Reference](cli.md) — command-line alternative
- [Architecture Overview](../architecture/overview.md) — how the pipeline works
- [Extending Guide](../developer-guide/extending.md) — add new MCP tools
