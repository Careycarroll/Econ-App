# ADR-0005: Data Model & Storage Schema

**Status**: Accepted
**Date**: 2026-07-20
**Deciders**: Carey Carroll
**Supersedes**: None
**Related**: ADR-0004 (Technology Stack)

---

## Context

ADR-0004 locked SQLite via stdlib `sqlite3` as the persistence layer. Before writing any code in v0.3 (FRED Client + Cache), we need to lock the schema: what tables exist, what they store, how they relate, and where the database lives on disk.

Without this ADR, every downstream implementation issue (schema.sql, cache layer, FRED client integration) has open design questions that risk being answered inconsistently across issues.

---

## Decision

### Storage Strategy: Compute-On-Read

Only raw observation values are persisted. Transforms (YoY %, MoM %, QoQ %, Annualized, and any future additions) are computed at read-time via pandas.

**Rationale:**

- Storage stays small (~6 MB for a 200-series catalog with 800 observations each)
- Adding new transforms later requires zero database migration
- Bug fixes to transform math have exactly one implementation site
- pandas transforms on ~800 rows complete in ~2 ms — invisible to the user
- Series-level caching (in memory) can be added later if needed

### Physical Location

Two distinct locations serve different purposes:

| Location                                 | Purpose                               | Content                                                       |
| ---------------------------------------- | ------------------------------------- | ------------------------------------------------------------- |
| **Platform app data dir**          | Runtime cache — real FRED data       | User's downloaded observations, series metadata, sync log     |
| **Repository `tests/fixtures/`** | Test fixtures — small, deterministic | Sample data checked into git for reliable, reproducible tests |

Platform data directory paths follow OS conventions:

- **macOS**: `~/Library/Application Support/Econ-App/econ_app.sqlite`
- **Linux**: `~/.local/share/econ-app/econ_app.sqlite` (respects `$XDG_DATA_HOME`)
- **Windows**: `%APPDATA%\Econ-App\econ_app.sqlite`

Resolution uses Python's `platformdirs` library.

### Schema

Three tables. All identifiers are lowercase snake_case per PEP 8 / SQL convention.

#### `series`

Metadata about FRED series. One row per series in the user's catalog.

```sql
CREATE TABLE series (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    notes TEXT,
    frequency TEXT NOT NULL,
    frequency_short TEXT,
    units TEXT NOT NULL,
    units_short TEXT,
    seasonal_adjustment TEXT,
    seasonal_adjustment_short TEXT,
    observation_start TEXT,
    observation_end TEXT,
    last_updated_fred TEXT,
    popularity INTEGER,
    fetched_at TEXT NOT NULL
);
```

Notes:

- `id` is the FRED series ID (e.g., `CPIAUCSL`) — natural primary key
- Date/timestamp columns are TEXT in ISO 8601 format (SQLite doesn't have a native date type; ISO 8601 sorts lexicographically which is convenient)
- `fetched_at` = when *we* last called FRED for this metadata (distinct from `last_updated_fred` = when FRED itself updated the series)

#### `observations`

The actual time-series values.

```sql
CREATE TABLE observations (
    series_id TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,
    PRIMARY KEY (series_id, date),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX idx_observations_date ON observations(date);
```

Notes:

- Composite PK `(series_id, date)` — natural key, prevents duplicates without an artificial ID column
- `value` is nullable — FRED marks missing observations with `.` and we store those as SQL NULL
- Foreign key cascade delete: removing a series wipes its observations
- Secondary index on `date` alone supports "all observations across series in date range" queries

#### `sync_log`

Tracks every sync operation for a series — successes, failures, and observation counts.

```sql
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    observation_count INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX idx_sync_log_series ON sync_log(series_id, synced_at DESC);
```

Notes:

- `status` is one of: `success`, `partial`, `error` (enforced in application code, not via CHECK constraint — keeps schema portable)
- `observation_count` is NULL on error
- `error_message` is NULL on success
- Index supports "get most recent sync for series X"

### Connection Settings (PRAGMAs)

Applied on every connection open:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

Rationale:

- `foreign_keys = ON` — SQLite disables FK enforcement by default; we want it on
- `journal_mode = WAL` — Write-Ahead Logging enables concurrent reads during writes and improves overall performance
- `synchronous = NORMAL` — reasonable durability without the perf hit of FULL; WAL makes NORMAL safe

### Schema Versioning

Single `schema.sql` at project root. Every change increments an integer version stored in a version table:

```sql
CREATE TABLE _schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);
```

On app startup, code checks the version and refuses to run against an incompatible schema. For v1, we start at version 1 and don't build migration machinery — if the schema evolves before v1 releases, users blow away their local database. Post-v1 migrations become their own ADR.

### Retention Policy

None for v1. Observations accumulate indefinitely. Given the small size (~40 bytes/row), 10 years of daily data across 200 series is ~150 MB — still not concerning. Retention becomes relevant if we ever pull intraday data (out of scope per ADR-0001).

### Concurrency

Single-writer, single-reader model. The app is single-user, single-process. WAL mode handles the rare case of a background refresh worker writing while the UI reads. No connection pooling needed.

---

## Rationale

### Why raw-only storage instead of pre-computed transforms

Considered: storing `level`, `yoy_pct`, `mom_pct`, `qoq_pct`, `annualized` as separate columns. Rejected because:

- Storage grows 5x for no perceptible speed benefit (pandas transforms on 800 rows are ~2 ms)
- Adding a new transform requires a schema migration and full re-computation of every series
- Pre-computed values encode assumptions (e.g., "YoY means same-month-last-year" vs "12-period lag") that we might want to revisit
- Bug fixes in transform logic only need one place updated

### Why platform data dir instead of project folder

Considered: `data/econ_app.sqlite` in the repo. Rejected because:

- User data belongs separate from source code per XDG-style conventions
- Repo-local data breaks if the user reclones or moves the project
- OS-level backups (Time Machine, etc.) protect app data dirs; project folders often aren't backed up
- Distinguishing "test fixtures" (in-repo, deterministic) from "real cache" (platform dir, user-specific) prevents the confusion of accidentally committing user data

### Why composite PK on observations instead of surrogate ID

Considered: `id INTEGER PRIMARY KEY AUTOINCREMENT` + unique constraint on `(series_id, date)`. Rejected because:

- Adds a column with no semantic meaning
- Slightly larger row size
- Prevents natural upsert-by-natural-key patterns (SQLite's `INSERT ... ON CONFLICT` needs a natural key)

### Why WAL mode

Standard for modern SQLite apps. Enables concurrent reads during writes, which matters if we ever add background refresh. Also improves write performance for our append-heavy workload. Downside: creates two extra files (`-wal`, `-shm`) alongside the main DB — already covered by `.gitignore`.

### Why platformdirs

Cross-platform correctness. Rolling our own path logic is a source of subtle bugs (Windows AppData variants, XDG spec edge cases). `platformdirs` is battle-tested, tiny, and has no other dependencies.

---

## Consequences

### Positive

- Storage layer is small, portable, and standardized
- Adding new transforms is a code change, not a schema change
- User data is protected by OS-level backups
- Schema is stable enough to survive most feature additions in v0.4+ without migration
- Test fixtures in the repo make CI deterministic

### Trade-offs Accepted

- Compute-on-read means every chart render does a pandas transform. Fine for personal use; would need caching if we scaled to thousands of series
- Platform data dir means the user has to know where their data is if they want to inspect it manually. `Data -> Open Data Folder` menu item will point at it
- Single-file schema without migrations means schema changes during v1 development require blowing away the local DB. Acceptable trade-off pre-1.0

### Consequences for Repository

New files this ADR implies:

- `schema.sql` — the actual DDL (Issue #26 creates this)
- `src/econ_app/services/database.py` — connection factory, PRAGMA setup, schema init (Issue #26)
- `src/econ_app/services/paths.py` — cross-platform data directory resolution
- Add `platformdirs` to `pyproject.toml` dependencies
- `tests/fixtures/` — sample data directory (populated by later issues as fixtures are needed)

### Consequences for Later Issues

- **Issue #26** (schema.sql): implements exactly what's specified above
- **Issue #31** (cache layer): reads/writes against this schema; uses parameterized queries only
- **Issue #66** (data folder menu item): opens the platform data dir in the OS file manager
- **Issue #71** (packaging): must include `schema.sql` in the bundled resources

---

## Alternatives Considered

| Alternative                                                      | Why Rejected                                                                                         |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Store all transforms                                             | 5x storage for no perceptible speed benefit; adds migration burden                                   |
| Project`data/` folder for real cache                           | Data belongs separate from code; OS backups don't cover it well                                      |
| Single flat table with`(series, date, key, value)` EAV pattern | Ugly, slow, hard to query, no meaningful benefit                                                     |
| SQLAlchemy ORM                                                   | Already rejected in ADR-0004 (SQLite via stdlib)                                                     |
| Parquet files instead of SQLite                                  | Not queryable ad-hoc; adds pandas-specific coupling; better for analytics workloads, not app storage |

---

## Open Questions (Deferred)

- Migration strategy post-v1 — will become its own ADR if the schema evolves after 1.0 release
- Multi-user support — explicitly out of scope per ADR-0001
- Full-text search on series notes — nice-to-have, deferred

---

## Approval

- [x] Storage strategy (compute-on-read) accepted
- [x] Location (platform data dir + repo test fixtures) accepted
- [x] Schema (3 tables) accepted
- [x] PRAGMAs and versioning strategy accepted
- [x] Ready to proceed to v0.3 implementation issues
