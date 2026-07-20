# Econ-App

A personal desktop application for exploring and learning about U.S. economic data. Pairs the daily economic release calendar with an interactive chart explorer backed by [FRED](https://fred.stlouisfed.org/) (Federal Reserve Economic Data).

**Status:** 🚧 Early build phase — scaffolding in progress.

---

## Vision

A personal tool that helps its user understand what economic data is being released, when, and what it means — by combining awareness (calendar), exploration (charts), and learning (curated context).

Not a trading platform. Not a commercial product. Not a Bloomberg replacement.

See [`docs/adr/0001-vision-and-scope.md`](docs/adr/0001-vision-and-scope.md) for the full vision statement.

---

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt 6) |
| Charts | PyQtGraph |
| Data | pandas + direct FRED API via `httpx` |
| Local storage | SQLite (stdlib `sqlite3`) |
| Config | `python-dotenv` + `keyring` for secrets |
| Packaging | `uv` + `pyproject.toml` |
| Linting/Formatting | `ruff` |
| Testing | `pytest` + `pytest-qt` |

Cross-platform target: macOS, Windows, Linux.

See [`docs/adr/0004-technology-stack.md`](docs/adr/0004-technology-stack.md) for full rationale.

---

## Repository Structure

```
Econ-App/
├── docs/
│   ├── adr/                  # Architecture Decision Records (immutable)
│   ├── specs/                # Living design specs
│   └── reference/            # Reference material (data catalogs, etc.)
├── src/
│   └── econ_app/             # Application source
├── tests/                    # Test suite
├── data/                     # (gitignored) Local FRED downloads and cache
├── scripts/                  # Utility scripts (fetch_fred_releases.py etc.)
├── .env.example              # Template for environment variables
├── .pre-commit-config.yaml   # Pre-commit hooks
├── pyproject.toml            # Dependencies, project metadata, tool config
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/) (fast Python package manager)
- Git
- A free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html)

Install `uv` if you don't have it:

```bash
# macOS
brew install uv

# Or via the official installer (macOS/Linux/Windows)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### First-time setup

```bash
# Clone
git clone https://github.com/Careycarroll/Econ-App.git
cd Econ-App

# Install runtime + dev dependencies (creates .venv, generates/uses uv.lock)
uv sync --extra dev

# Install git pre-commit hooks (one-time)
uv run pre-commit install

# Set your FRED API key
cp .env.example .env
# Edit .env and paste your key
```

### Run the app

```bash
uv run python -m econ_app
```

For now this prints a hello message — the PySide6 window arrives in Issue #14.

---

## Development

All commands are run through `uv` so they use the project's `.venv` automatically.

### Testing

```bash
# Run the full test suite
uv run pytest

# Run a single test file
uv run pytest tests/test_smoke.py

# Run with verbose output
uv run pytest -v
```

### Formatting & linting

```bash
# Auto-format all Python code (idempotent)
uv run ruff format .

# Check formatting without modifying files
uv run ruff format --check .

# Lint (finds bugs, style issues, unused imports)
uv run ruff check .

# Lint and auto-fix what's safely fixable
uv run ruff check --fix .
```

### Pre-commit hooks

Hooks run automatically on `git commit`. To run them manually:

```bash
# Run all hooks against all files (dry-run before committing)
uv run pre-commit run --all-files

# Run against only staged files
uv run pre-commit run
```

If a hook auto-fixes a file (formatter, trailing whitespace, etc.), the commit will be blocked. Re-stage the fixes and commit again:

```bash
git add -u
git commit  # retry
```

### Adding a dependency

```bash
# Runtime dependency
uv add <package>

# Dev-only dependency
uv add --dev <package>
```

This updates both `pyproject.toml` and `uv.lock`.

### Updating dependencies

```bash
# Update all dependencies to latest compatible versions
uv sync --upgrade
```

---

## Design Documentation

All product and technical decisions live under `docs/`:

- **Architecture Decision Records** (`docs/adr/`) — immutable record of what was decided and why
  - ADR-0001: Vision & Scope
  - ADR-0002: MVP Feature Scope
  - ADR-0003: Information Architecture
  - ADR-0004: Technology Stack
- **Specifications** (`docs/specs/`) — living documents describing use cases, flows, wireframes
  - `use-cases.md` — 5 concrete usage scenarios
  - `feature-inventory.md` — full feature menu with MoSCoW markup
  - `wireframes.md` — ASCII wireframes for all views
- **Reference** (`docs/reference/`) — curated data catalogs and source references

---

## Roadmap

See the [milestones on GitHub](https://github.com/Careycarroll/Econ-App/milestones) for the full v0.1 → v1.0 build plan.

---

## License

TBD — will be set once the project moves toward a first release. Assume "all rights reserved" until a license file is committed.

---

## Contact

Personal project by [Carey Carroll](https://github.com/Careycarroll). Not accepting contributions at this stage.
