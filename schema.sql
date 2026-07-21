-- Econ-App SQLite schema
-- Per ADR-0005. Version 1.
--
-- Applied on app startup by src/econ_app/services/database.py.
-- Idempotent — safe to run against a fresh or already-initialized database.

CREATE TABLE IF NOT EXISTS series (
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

CREATE TABLE IF NOT EXISTS observations (
    series_id TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,
    PRIMARY KEY (series_id, date),
    FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_observations_date ON observations(date);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    observation_count INTEGER,
    status TEXT NOT NULL,
    error_message TEXT
);
-- Note: intentionally no FK on series_id. sync_log is an audit trail and
-- must be able to record sync attempts against series that don't exist in FRED
-- (or against series we never successfully fetched metadata for). See ADR-0005.

CREATE INDEX IF NOT EXISTS idx_sync_log_series ON sync_log(series_id, synced_at DESC);

CREATE TABLE IF NOT EXISTS _schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);
