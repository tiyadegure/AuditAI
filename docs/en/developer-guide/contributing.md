# Contributing to AuditAI

> Development setup, code style, testing, and PR workflow.

## Development Environment

### 1. Clone and Install

```bash
git clone https://github.com/your-org/eth-beijing-2026.git
cd eth-beijing-2026
pip install -r requirements.txt
```

### 2. Install Dev Dependencies

```bash
pip install pytest pytest-asyncio black ruff mypy
```

### 3. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your keys
```

### 4. Verify Setup

```bash
python3 -m src.main --help
python3 -m src.main detect data/contracts/VulnerableBank.sol
```

## Code Style

### Python

- **Python 3.11+** — use modern syntax (`list[dict]` not `List[Dict]`)
- **Formatter:** Black (`black .`)
- **Linter:** Ruff (`ruff check .`)
- **Type hints:** Required for function signatures

### Solidity

- **Style:** [Solidity Style Guide](https://docs.soliditylang.org/en/latest/style-guide.html)
- **Compiler:** 0.8.x
- **License:** MIT

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Functions | `snake_case` | `detect_vulnerabilities` |
| Classes | `PascalCase` | `AuditorAgent` |
| Constants | `UPPER_SNAKE` | `MAX_CHUNK_CHARS` |
| Private methods | `_prefix` | `_run_slither` |

## Project Structure

```
src/
├── agents/          # 5-agent pipeline
│   ├── auditor.py   # Detection logic
│   ├── architect.py # Repair strategy
│   ├── code_generator.py
│   ├── refiner.py
│   ├── validator.py
│   └── orchestrator.py
├── tools/           # Domain tools
├── knowledge/       # RAG knowledge base
├── chain/           # EAS attestation
├── mcp/             # MCP server
├── evaluation/      # Evaluation framework
└── utils/           # Shared utilities
```

## Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_auditor.py

# With verbose output
pytest -v

# With coverage
pytest --cov=src
```

## Linting and Formatting

```bash
# Format with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type check with Mypy
mypy src/
```

## PR Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bugfix
```

### 2. Make Changes

- Write code following the style guide
- Add tests for new functionality
- Update documentation if needed

### 3. Run Checks

```bash
black src/ tests/
ruff check src/ tests/
pytest
```

### 4. Commit

```bash
git add .
git commit -m "feat: add new detector for flash loan attacks"
```

Commit message format:
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `test:` — tests
- `refactor:` — code refactoring
- `chore:` — maintenance

### 5. Push and Create PR

```bash
git push origin feature/my-feature
```

Create a PR on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots if UI changes

## Adding New Agents

See [Extending Guide](extending.md) for how to add new detectors, tools, and MCP tools.

## See Also

- [Extending Guide](extending.md) — add new features
- [Architecture Overview](../architecture/overview.md) — system design
- [Configuration Reference](../reference/config.md) — all settings
