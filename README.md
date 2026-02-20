# autonomous-operator

Memory-First Autonomous Operator Platform (offline-first, provider-agnostic, safe-by-default).

## Version

`0.1.1`

## What This Project Is

A scaffolded autonomous operator framework centered on memory as the primary product:

- Swappable LLM backends (mock, OpenAI, Ollama)
- Swappable vision backends (mock VLM + OCR fallback)
- Windows OS automation scaffolding with safety guards
- Multi-type memory system:
  - context
  - episodic
  - semantic
  - procedural
  - goal
  - self-model
  - uncertainty ledger
- Consolidation cycle (`dream/replay`) with contradiction detection and forgetting
- Governance and audit with strict safe defaults
- CLI for chat, goal execution, memory inspection, consolidation, config and tool listing

## Safe Mode (Default)

Policies are defined in `config/permissions.yaml`. By default:

- `allow_shell: false`
- `allow_file_write_outside_workspace: false`
- `allow_os_automation: false`
- `allow_network: false`
- `max_daily_budget_usd: 0`
- confirmation required for sensitive actions

All tool execution routes through governance checks and risk scoring before running.

## Install

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Reproducible Dependency Lock

Use UV to create/update a lockfile:

```bash
pip install uv
uv lock
```

## Quickstart

```bash
ao --help
ao config show
ao tools list
ao run-goal "Remember I love lo-fi music and summarize it into my preferences"
ao memory inspect
ao memory consolidate
ao chat
```

## Run in Docker (Recommended Sandbox)

```bash
docker compose build
docker compose up operator
```

Optional vector service profile:

```bash
docker compose --profile vector up -d chroma
```

## Demo (No Paid APIs Required)

The default model backend is `mock`, so this works offline:

```bash
ao run-goal "Remember I love lo-fi music and summarize it into my preferences"
ao memory inspect
```

Expected result includes:

- an episode in episodic memory
- a proposed belief like "User likely likes lo-fi music" with confidence `< 1.0`

## Configuration

- `config/default.yaml`: runtime defaults
- `config/models.yaml`: LLM and vision providers
- `config/tools.yaml`: tool enablement
- `config/permissions.yaml`: governance policies

Environment variables are optional; see `.env.example`.

## Provider Plug-In Model

LLM providers implement `llm.base_llm.BaseLLM` and are created by `llm.llm_factory.build_llm`.
Vision providers are selected by `vision.vision_router.VisionRouter`.

## Memory Design

See:

- `memory/README.md`
- `docs/MEMORY_DESIGN.md`
- `docs/ARCHITECTURE.md`

## Security and Governance

See `docs/SECURITY.md`.

## Development and CI

Local quality gates:

```bash
ruff check .
black --check .
mypy .
pytest -q
```

GitHub Actions runs the same checks on push/PR from `.github/workflows/ci.yml`.

## Open Source

- License: `LICENSE` (MIT)
- Contribution guide: `CONTRIBUTING.md`
