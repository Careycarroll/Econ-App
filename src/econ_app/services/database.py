"""SQLite connection factory and schema initialization.

Per ADR-0005:
- WAL journal mode
- Foreign keys enforced
- Composite primary keys where natural
- Version-tracked schema (single schema.sql)
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from econ_app.services.paths import get_database_path, get_schema_path

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection to the app's database with standard PRAGMAs applied."""
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize or verify the schema. Idempotent — safe to call on every launch."""
    schema_sql = get_schema_path().read_text()
    conn.executescript(schema_sql)

    # Set version if not already set
    existing = conn.execute("SELECT version FROM _schema_version LIMIT 1").fetchone()
    if existing is None:
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO _schema_version (version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, now),
        )
        conn.commit()
        log.info("Initialized schema version %d", SCHEMA_VERSION)
    elif existing[0] != SCHEMA_VERSION:
        log.warning(
            "Schema version mismatch: found %d, expected %d. "
            "Pre-v1 apps may need to delete the local database.",
            existing[0],
            SCHEMA_VERSION,
        )
    else:
        log.debug("Schema version %d already applied", SCHEMA_VERSION)


def ensure_ready() -> None:
    """Call once on app startup to ensure the database exists and is initialized."""
    with get_connection() as conn:
        init_schema(conn)
