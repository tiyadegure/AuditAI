# MCP 集成

> 通过 Model Context Protocol 将 AuditAI 工具暴露给外部代理和 IDE 集成。

## 什么是 MCP？

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) 是连接 AI 模型与外部工具和数据源的标准。AuditAI 实现了一个 MCP 服务器，将智能合约审计能力暴露为 MCP 工具，允许任何 MCP 兼容客户端（Cursor、Claude 等）运行审计。

## 启动 MCP 服务器

```bash
# 生产环境 — stdio 传输（连接 MCP 客户端）
python3 -m src.main serve
```

服务器默认通过 **stdio**（stdin/stdout）运行，这是 MCP 客户端的标准传输方式。

## 从 IDE 连接

### Cursor

1. 打开 **Settings → MCP**
2. 添加新的 MCP 服务器：
   - **Type**: `stdio`
   - **Command**: `python3 -m src.main serve`
   - **Working directory**: `/path/to/eth-beijing-2026`

### Claude Desktop

添加到 `claude_desktop_config.json`：

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

## 可用工具

MCP 服务器暴露三个工具：

### `analyze_contract`

运行完整智能合约审计。

**输入 Schema：**

```json
{
  "contract_path": "string (required) — path to the .sol file",
  "mode": "string — 'detect', 'patch', 'exploit', or 'all' (default: 'all')"
}
```

**调用示例：**

```json
{
  "name": "analyze_contract",
  "arguments": {
    "contract_path": "data/contracts/VulnerableBank.sol",
    "mode": "all"
  }
}
```

**返回：** 包含漏洞、补丁和验证结果的完整审计结果。

---

### `get_vulnerability_details`

从 RAG 知识库查找漏洞类型。

**输入 Schema：**

```json
{
  "vulnerability_type": "string (required) — e.g., 'reentrancy', 'overflow'"
}
```

**调用示例：**

```json
{
  "name": "get_vulnerability_details",
  "arguments": {
    "vulnerability_type": "reentrancy"
  }
}
```

**返回：** 相关漏洞类型的知识库条目。

---

### `generate_report`

从审计结果生成格式化审计报告。

**输入 Schema：**

```json
{
  "audit_result": "object (required) — audit result object",
  "format": "string — 'json', 'markdown', or 'html' (default: 'markdown')"
}
```

**调用示例：**

```json
{
  "name": "generate_report",
  "arguments": {
    "audit_result": { "contract_path": "...", "vulnerabilities": [...] },
    "format": "markdown"
  }
}
```

## 协议详情

服务器实现 MCP 协议版本 `2024-11-05`，支持：

- **`initialize`** — 服务器握手
- **`tools/list`** — 列出可用工具
- **`tools/call`** — 调用工具

还支持手动 JSON-RPC 调度模式，用于 HTTP/SSE 传输和测试。

## 扩展 MCP 服务器

要添加新工具，编辑 `src/mcp/mcp_server.py`：

1. 在 `_register_default_tools()` 中添加工具定义
2. 添加处理方法（如 `_handle_my_tool`）
3. 在 `_dispatch_tool()` 中注册处理程序

详见 [扩展指南](../developer-guide/extending.md)。

## 另请参阅

- [CLI 参考](cli.md) — 命令行替代方案
- [架构概述](../architecture/overview.md) — 流水线工作原理
- [扩展指南](../developer-guide/extending.md) — 添加新 MCP 工具
