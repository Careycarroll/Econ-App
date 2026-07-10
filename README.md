# Econ-App

A personal desktop application for exploring and learning about U.S. economic data. Pairs the daily economic release calendar with an interactive chart explorer backed by [FRED](https://fred.stlouisfed.org/) (Federal Reserve Economic Data).

**Status:** 🚧 Early design phase — not yet buildable.

---

## Vision

A personal tool that helps its user understand what economic data is being released, when, and what it means — by combining awareness (calendar), exploration (charts), and learning (curated context).

Not a trading platform. Not a commercial product. Not a Bloomberg replacement.

See [`docs/adr/0001-vision-and-scope.md`](docs/adr/0001-vision-and-scope.md) for the full vision statement.

---

## Planned Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt 6) |
| Charts | PyQtGraph |
| Data | pandas + FRED API (`fredapi`) |
| Local storage | SQLite |
| Config | `python-dotenv` + `keyring` for secrets |
| Packaging | `pyproject.toml` |

Cross-platform target: macOS, Windows, Linux.

---

## Repository Structure

```
Econ-App/
├── docs/
│   ├── adr/                  # Architecture Decision Records (immutable)
│   ├── specs/                # Living design specs
│   └── reference/            # Reference material (data catalogs, etc.)
├── src/                      # (later) Application source
├── tests/                    # (later) Tests
├── data/                     # (gitignored) Local FRED downloads and cache
├── .env.example              # Template for environment variables
├── .gitignore
├── README.md
└── pyproject.toml            # (later) Dependencies and build config
```

---

## Getting Started (Developer Setup)

*This section will expand as the project progresses. For now:*

### Prerequisites

- Python 3.11 or newer
- Git
- A free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html)

### Initial Setup

```bash
# Clone
git clone https://github.com/Careycarroll/Econ-App.git
cd Econ-App

# (Later, once code exists) Create a virtual environment and install deps
python -m venv .venv
source .venv/bin/activate     # macOS/Linux
# or: .venv\Scripts\activate  # Windows
pip install -e .

# Set your FRED API key
cp .env.example .env
# Edit .env and paste your key
```

---

## Design Documentation

All product and technical decisions live under `docs/`:

- **Architecture Decision Records** (`docs/adr/`) — immutable record of what was decided and why
- **Specifications** (`docs/specs/`) — living documents describing use cases, flows, wireframes
- **Reference** (`docs/reference/`) — curated data catalogs and source references

Design is proceeding in structured phases:

1. ✅ Vision & Scope (ADR-0001, drafted)
2. ⏳ MVP Feature Scope (ADR-0002, next)
3. ⏳ Information Architecture
4. ⏳ User Flows & Wireframes
5. ⏳ Technical Design
6. ⏳ Build

---

## License

TBD — will be set once the project moves toward a first release. Assume "all rights reserved" until a license file is committed.

---

## Contact

Personal project by [Carey Carroll](https://github.com/Careycarroll). Not accepting contributions at this stage.
