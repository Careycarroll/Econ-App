# ADR-0004: Technology Stack

**Status**: Accepted
**Date**: 2026-07-18
**Deciders**: Carey Carroll
**Supersedes**: None
**Related**: ADR-0001 (Vision & Scope), ADR-0002 (MVP Feature Scope)

---

## Context

ADR-0001 established a personal desktop app for U.S. economic data. ADR-0002 locked v1 scope. Prior conversation informally settled on Python + PySide6 + PyQtGraph after weighing Swift (rejected: Apple-only), Streamlit (rejected: web-feel), Electron (rejected: heavier for what we need), and Flet (rejected: less mature charting).

This ADR formalizes those decisions as a single reference so future engineering work has one place to check "what are we using and why."

---

## Decision

### Core Stack

| Layer | Choice | Version |
|---|---|---|
| **Language** | Python | 3.11+ |
| **GUI framework** | PySide6 (Qt 6 bindings) | latest stable |
| **Charts** | PyQtGraph | latest stable |
| **Data manipulation** | pandas | latest stable |
| **HTTP client** | `httpx` | latest stable |
| **FRED integration** | Direct via `httpx` (no wrapper library) | — |
| **Local persistence** | SQLite via stdlib `sqlite3` | stdlib |
| **Secrets** | `python-dotenv` (dev) + `keyring` (post-MVP) | latest stable |
| **Packaging** | `uv` + `pyproject.toml` | latest stable |
| **Linting/formatting** | `ruff` | latest stable |
| **Testing** | `pytest` | latest stable |
| **Distribution** | Run from source (v1); PyInstaller later | — |

---

## Rationale

### Language: Python 3.11+

- User already knows it
- Cross-platform (macOS, Windows, Linux) — a v1 Must (9.5)
- Vast data ecosystem (pandas, numpy, SQLite bindings)
- 3.11+ gives us modern typing, better error messages, `tomllib` in stdlib

### GUI Framework: PySide6

- Truly native desktop experience per ADR-0001's "contained app" preference
- Cross-platform without rewrites
- Mature, battle-tested (Qt has been around since 1991)
- Official Python bindings from The Qt Company (as opposed to PyQt which has stricter licensing)
- LGPL license — fine for personal use, no attribution issues
- Rich widget library covers everything in the v1 feature inventory

### Charts: PyQtGraph

- Built for scientific/financial time series specifically
- Native pan/zoom/crosshair/regions performance
- Handles decades of daily data without lag
- Integrates cleanly with PySide6
- Alternatives considered and rejected:
  - **Qt Charts**: less powerful, less interactive by default
  - **Matplotlib embedded**: slow, awkward interactivity
  - **Plotly in QWebEngineView**: fights the native paradigm

### Data Manipulation: pandas

- Every transform in feature 3.5 (Level, YoY %, MoM %, QoQ %, Annualized) is a pandas one-liner
- Standard for economic/financial time series work
- Handles missing data, resampling, date arithmetic natively
- Interoperates with SQLite (`pd.read_sql`, `df.to_sql`)

### HTTP Client: httpx

- Modern, well-typed, sync + async support in one library
- Better error handling and timeout ergonomics than `requests`
- Async support is future-proofing (v1 doesn't need it, but adding it later is free)

### FRED Integration: Direct via httpx (no wrapper)

- The `fredapi` package exists but is a thin wrapper
- Writing our own client is ~100 lines and gives full control over:
  - Rate limiting behavior (Must 7.9)
  - Retry logic
  - Response caching
  - Error messages
- No maintenance risk from an unmaintained third-party wrapper

### Local Persistence: SQLite via stdlib `sqlite3`

**Choice: raw stdlib `sqlite3` module** (not SQLAlchemy).

Rationale:
- **Ships with Python** — zero additional dependency
- **Zero learning curve** — you write SQL directly
- **Right-sized for scope** — Econ-App has a small schema (essentially: observations table, series metadata table, sync log). SQLAlchemy shines when you have 20+ tables with complex relationships. Here it would be overkill.
- **Lighter install** — SQLAlchemy adds ~10 MB and pulls in its own type system
- **Perfect fit for read-heavy time series** — SQL is genuinely the clearest way to express "give me all observations for CPI between date X and date Y"

Trade-offs accepted:
- No ORM convenience for model objects (we'll use dataclasses instead)
- Manual migration handling if the schema evolves (fine — for a personal tool, a `schema.sql` file plus a version number is enough)

If the schema ever grows past ~10 tables or we need multi-database support, we'll write ADR-000N to migrate to SQLAlchemy. Not a v1 concern.

### Secrets: python-dotenv + keyring

- **`python-dotenv`** for v1: reads `.env` file at startup. Simple, standard, works cross-platform. Fine for a single-user local app.
- **`keyring`** post-v1 (Should feature 8.2): OS-level keychain integration for better security. Only matters if the app is ever distributed or the machine is shared.

### Packaging: uv + pyproject.toml

- **`uv`** is Astral's Rust-based package manager — dramatically faster than pip/poetry
- **`pyproject.toml`** is modern Python's standard for project metadata and dependencies
- `uv sync` handles virtualenv + install in one command
- Alternatives considered:
  - **poetry**: mature but slower, larger dependency footprint
  - **pip + requirements.txt**: works but lacks lockfile guarantees
  - **conda**: overkill for a pure-Python app

### Linting/Formatting: ruff

- Rust-based, ~100x faster than flake8/black
- Single tool replaces flake8, isort, pyupgrade, and (via `ruff format`) black
- Sensible defaults, minimal config
- Actively developed by Astral (same folks as `uv`)

### Testing: pytest

- Standard for Python testing
- Simpler syntax than unittest
- Rich fixture system
- Wide ecosystem (pytest-mock, pytest-qt for Qt testing)

### Distribution: Run from source (v1)

- ADR-0002 marked "Run from source" as the only Distribution Must
- PyInstaller bundles are Should — added when personal convenience justifies it
- Signed builds, auto-update, crash reporting are Won't per ADR-0001 non-goals

---

## Consequences

### Positive

- **Every choice is stable, mature, and well-documented.** Nothing on the bleeding edge.
- **Stack fits the scope.** No overkill (SQLAlchemy) or wrong-tool-for-the-job (matplotlib).
- **Cross-platform out of the box.** PySide6 + PyQtGraph + Python stdlib work identically on macOS, Windows, Linux.
- **Small dependency footprint.** Roughly 6-8 top-level runtime dependencies for the whole app.
- **Familiar to user.** Nothing requires learning a new language or paradigm.

### Trade-offs Accepted

- **No web version, no mobile version.** By design.
- **PyQtGraph aesthetics require styling work.** Default looks are utilitarian. Themeing is a v1 task, not "free."
- **SQLite means single-writer.** Not a real limitation for a single-user app but worth naming.
- **Manual FRED client means we own the maintenance.** Small surface area but not zero.
- **No ORM means SQL directly in code.** Preferred trade-off for this scope but must be disciplined about SQL injection (parameterized queries only — never string concatenation).

### Consequences for Repository

New files this stack implies:

- `pyproject.toml` — dependencies, project metadata, build config
- `.python-version` — Python version pin for uv
- `uv.lock` — dependency lockfile (committed to git)
- `src/econ_app/` — source layout
- `tests/` — test suite
- `schema.sql` — SQLite schema (evolves; version tracked)

### Consequences for Workflow

- All commands run through `uv`: `uv run python`, `uv run pytest`, `uv add <pkg>`, etc.
- Lint/format on save via VSCode + ruff extension
- CI (future) runs `uv sync` then `pytest` on push to main

---

## Alternatives Considered

Already covered in prior discussion, summarized here for the record:

| Alternative | Why Rejected |
|---|---|
| **Swift + SwiftUI** | Apple-only; kills cross-platform Must |
| **Streamlit** | Feels like a web page in a window; not "contained app" per user preference |
| **Dash (Plotly)** | Same web-feel issue |
| **Flet** | Younger, less mature charting story |
| **Electron + Python backend** | Heavier, and we already know the web-feel is unwanted |
| **Tkinter + matplotlib** | Ugly by default, slow charts, poor DX |
| **SQLAlchemy over raw sqlite3** | Overkill for schema of this size |
| **fredapi wrapper** | Prefer direct control for rate limits, retries, caching |
| **poetry** | Slower than uv, larger footprint |
| **black + flake8 + isort** | ruff replaces all three faster and with less config |

---

## Open Questions (Deferred)

- **Which VSCode extensions to standardize on** — worth deciding once we start coding (Python, Pylance, Ruff, EditorConfig at minimum)
- **Async architecture for FRED calls** — httpx supports both sync and async; we'll pick a pattern when we design the data-fetch layer
- **Whether to use Qt Designer for any UI** — probably not (code-first preferred), but keep option open for complex layouts
- **CI setup on GitHub Actions** — defer until there's testable code

These become their own ADRs if the decisions turn out to matter.

---

## Approval

- [ ] Stack choices accepted
- [ ] Persistence approach (stdlib sqlite3, not SQLAlchemy) accepted
- [ ] Distribution posture (run from source in v1) accepted
- [ ] Ready to proceed to ADR-0003 (Information Architecture)

*Sign here (metaphorically) by confirming in conversation, then this ADR moves from "Proposed" to "Accepted."*
