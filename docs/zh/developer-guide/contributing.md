# 参与贡献

> 开发环境、代码风格、测试和 PR 工作流。

## 开发环境

### 1. 克隆并安装

```bash
git clone https://github.com/your-org/eth-beijing-2026.git
cd eth-beijing-2026
pip install -r requirements.txt
```

### 2. 安装开发依赖

```bash
pip install pytest pytest-asyncio black ruff mypy
```

### 3. 配置环境

```bash
cp .env.example .env
# 编辑 .env 填入密钥
```

### 4. 验证设置

```bash
python3 -m src.main --help
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

## 代码风格

### Python

- **Python 3.11+** — 使用现代语法（`list[dict]` 而非 `List[Dict]`）
- **格式化：** Black (`black .`)
- **检查：** Ruff (`ruff check .`)
- **类型提示：** 函数签名必须包含

### Solidity

- **风格：** [Solidity 风格指南](https://docs.soliditylang.org/en/latest/style-guide.html)
- **编译器：** 0.8.x
- **许可：** MIT

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 函数 | `snake_case` | `detect_vulnerabilities` |
| 类 | `PascalCase` | `AuditorAgent` |
| 常量 | `UPPER_SNAKE` | `MAX_CHUNK_CHARS` |
| 私有方法 | `_prefix` | `_run_slither` |

## 项目结构

```
src/
├── agents/          # 5 代理流水线
│   ├── auditor.py   # 检测逻辑
│   ├── architect.py # 修补策略
│   ├── code_generator.py
│   ├── refiner.py
│   ├── validator.py
│   └── orchestrator.py
├── tools/           # 领域工具
├── knowledge/       # RAG 知识库
├── chain/           # EAS 链上证明
├── mcp/             # MCP 服务器
├── evaluation/      # 评估框架
└── utils/           # 共享工具
```

## 运行测试

```bash
# 所有测试
pytest

# 特定测试文件
pytest tests/test_auditor.py

# 详细输出
pytest -v

# 带覆盖率
pytest --cov=src
```

## 代码检查和格式化

```bash
# Black 格式化
black src/ tests/

# Ruff 检查
ruff check src/ tests/

# Mypy 类型检查
mypy src/
```

## PR 工作流

### 1. 创建分支

```bash
git checkout -b feature/my-feature
# 或
git checkout -b fix/my-bugfix
```

### 2. 进行修改

- 按风格指南编写代码
- 为新功能添加测试
- 如有需要更新文档

### 3. 运行检查

```bash
black src/ tests/
ruff check src/ tests/
pytest
```

### 4. 提交

```bash
git add .
git commit -m "feat: add new detector for flash loan attacks"
```

提交信息格式：
- `feat:` — 新功能
- `fix:` — bug 修复
- `docs:` — 文档
- `test:` — 测试
- `refactor:` — 代码重构
- `chore:` — 维护

### 5. 推送并创建 PR

```bash
git push origin feature/my-feature
```

在 GitHub 上创建 PR，包含：
- 清晰的修改说明
- 相关 issue 链接
- 如有 UI 变更附截图

## 添加新代理

详见 [扩展指南](extending.md) 了解如何添加新检测器、工具和 MCP 工具。

## 另请参阅

- [扩展指南](extending.md) — 添加新功能
- [架构概述](../architecture/overview.md) — 系统设计
- [配置参考](../reference/config.md) — 所有设置
