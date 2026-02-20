# Contributing

## Setup

1. Create a virtual environment.
2. Install project + dev dependencies:
   - `pip install -e ".[dev]"`
3. Run checks:
   - `ruff check .`
   - `black --check .`
   - `mypy .`
   - `pytest`

## Branch and PR Flow

1. Fork the repository and create a feature branch.
2. Keep changes focused and include tests.
3. Open a PR with:
   - problem statement
   - implementation summary
   - safety impact (if tool/governance changes)

## Adding an LLM Provider

1. Add provider implementation under `llm/providers/` or `llm/local/`.
2. Implement `llm.base_llm.BaseLLM`.
3. Register in `llm/llm_factory.py`.
4. Add provider config in `config/models.yaml`.
5. Add tests for graceful failure when dependency/credentials are missing.

## Adding a Tool

1. Implement a subclass of `tools.base_tool.BaseTool`.
2. Register it in `tools/tool_registry.py`.
3. Ensure it routes through `executor/safe_runner.py`.
4. Add policy expectations in `config/permissions.yaml` / `config/tools.yaml`.
5. Add tests confirming risky behavior is blocked by default.

## Safety Requirements

- Do not bypass governance checks.
- Keep destructive operations disabled by default.
- Keep workspace boundaries enforced.
- Preserve audit logging for all tool execution paths.
