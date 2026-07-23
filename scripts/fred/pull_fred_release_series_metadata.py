"""
Pull FRED series metadata for releases in an Excel workbook.

This script is designed for large FRED releases. It supports:
  - metadata-only pulls, not observation values
  - per-release JSON cache/checkpoints for resume
  - preflight series counts
  - CSV outputs plus an Excel summary workbook
  - safe versioned workbook output without overwriting the source

Environment variables:
  FRED_API_KEY                 Required. Your FRED API key.
  FRED_RELEASE_WORKBOOK        Optional. Path to the input workbook.
                                Defaults to ./fred_releases-2.xlsx
  FRED_METADATA_OUTPUT_DIR     Optional. Directory for CSV/cache outputs.
                                Defaults to the workbook directory.

Typical usage:
  export FRED_API_KEY="your_key_here"
  export FRED_RELEASE_WORKBOOK="~/Github Projects/Econ-App/data/fred_releases-2.xlsx"

  # Recommended first pass: get counts only
  python3 pull_fred_release_series_metadata.py --mode preflight

  # Full metadata pull with checkpoint/resume
  python3 pull_fred_release_series_metadata.py --mode pull

  # Pull specific releases only
  python3 pull_fred_release_series_metadata.py --mode pull --release-ids 1,46,52

  # Pull only releases with <= 10000 series after a preflight cache exists
  python3 pull_fred_release_series_metadata.py --mode pull --skip-large-releases 10000

Dependencies:
  pip install pandas openpyxl requests
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

FRED_API_BASE = "https://api.stlouisfed.org/fred"
DEFAULT_WORKBOOK_PATH = Path.cwd() / "fred_releases-2.xlsx"
REQUEST_LIMIT = 1000
REQUEST_SLEEP_SECONDS = 0.15
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

GENERATED_SHEETS = {
    "README_api_pull",
    "api_pull_summary",
    "series_inventory",
    "release_series_map",
    "api_refresh_log",
    "series_pull_errors",
    "release_series_counts",
}

EXCEL_MAX_ROWS = 1_048_576


# -----------------------------------------------------------------------------
# General helpers
# -----------------------------------------------------------------------------

def utc_now_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def require_api_key() -> str:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is not set.\n\n"
            "macOS/Linux:\n"
            "  export FRED_API_KEY='your_key_here'\n\n"
            "Windows PowerShell:\n"
            "  $env:FRED_API_KEY='your_key_here'\n"
        )
    return api_key


def get_input_workbook_path() -> Path:
    return Path(os.getenv("FRED_RELEASE_WORKBOOK", str(DEFAULT_WORKBOOK_PATH))).expanduser().resolve()


def get_output_dir(input_path: Path) -> Path:
    raw = os.getenv("FRED_METADATA_OUTPUT_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return input_path.parent.resolve()


def next_version_path(input_path: Path) -> Path:
    stem = input_path.stem
    suffix = input_path.suffix
    match = re.search(r"_v(\d+)$", stem)

    if match:
        base = stem[: match.start()]
        version = int(match.group(1)) + 1
    else:
        base = stem
        version = 2

    candidate = input_path.with_name(f"{base}_v{version}{suffix}")
    while candidate.exists():
        version += 1
        candidate = input_path.with_name(f"{base}_v{version}{suffix}")
    return candidate


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def find_release_sheet(workbook: Dict[str, pd.DataFrame]) -> Tuple[str, pd.DataFrame]:
    if "releases_catalog" in workbook:
        return "releases_catalog", normalize_columns(workbook["releases_catalog"])

    for sheet_name, df in workbook.items():
        normalized = normalize_columns(df)
        lower_cols = {c.lower(): c for c in normalized.columns}
        if "release_id" in lower_cols:
            return sheet_name, normalized

    raise ValueError("No sheet with a release_id column was found.")


def coerce_release_id(value: Any) -> Optional[str]:
    if pd.isna(value):
        return None
    try:
        as_float = float(value)
        if as_float.is_integer():
            return str(int(as_float))
    except Exception:
        pass
    cleaned = str(value).strip()
    return cleaned if cleaned else None


def build_release_table(releases_df: pd.DataFrame) -> pd.DataFrame:
    lower_cols = {c.lower(): c for c in releases_df.columns}
    release_id_col = lower_cols.get("release_id")
    release_name_col = lower_cols.get("name") or lower_cols.get("release_name")

    if not release_id_col:
        raise ValueError("The release sheet must contain a release_id column.")

    out = pd.DataFrame()
    out["release_id"] = releases_df[release_id_col].apply(coerce_release_id)
    if release_name_col:
        out["release_name"] = releases_df[release_name_col].fillna("").astype(str).str.strip()
    else:
        out["release_name"] = ""

    out = out.dropna(subset=["release_id"]).drop_duplicates(subset=["release_id"]).reset_index(drop=True)
    return out


def parse_release_ids(raw: Optional[str]) -> Optional[set[str]]:
    if not raw:
        return None
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    return ids or None


def filter_release_table(release_table: pd.DataFrame, release_ids: Optional[set[str]]) -> pd.DataFrame:
    if not release_ids:
        return release_table
    return release_table[release_table["release_id"].astype(str).isin(release_ids)].reset_index(drop=True)


def cache_file_for_release(cache_dir: Path, release_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(release_id))
    return cache_dir / f"release_{safe_id}_series.json"


def counts_cache_path(cache_dir: Path) -> Path:
    return cache_dir / "release_series_counts.csv"


# -----------------------------------------------------------------------------
# FRED API helpers
# -----------------------------------------------------------------------------

def fred_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{FRED_API_BASE}/{endpoint.lstrip('/')}"
    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                sleep_seconds = 1.5 * attempt
                print(f"  retrying after error ({attempt}/{MAX_RETRIES}): {exc}", file=sys.stderr)
                time.sleep(sleep_seconds)
            else:
                raise RuntimeError(f"FRED request failed after {MAX_RETRIES} attempts: {url} | {exc}") from exc

    raise RuntimeError(f"FRED request failed: {last_error}")


def get_release_series_count(api_key: str, release_id: str) -> int:
    payload = fred_get(
        "release/series",
        {
            "api_key": api_key,
            "file_type": "json",
            "release_id": release_id,
            "limit": 1,
            "offset": 0,
        },
    )
    return int(payload.get("count", 0))


def pull_series_for_release(api_key: str, release_id: str, cache_dir: Path, force_refresh: bool = False) -> List[Dict[str, Any]]:
    cache_path = cache_file_for_release(cache_dir, release_id)

    if cache_path.exists() and not force_refresh:
        with cache_path.open("r", encoding="utf-8") as f:
            cached = json.load(f)
        return cached.get("seriess", [])

    all_series: List[Dict[str, Any]] = []
    offset = 0
    count: Optional[int] = None

    while True:
        payload = fred_get(
            "release/series",
            {
                "api_key": api_key,
                "file_type": "json",
                "release_id": release_id,
                "limit": REQUEST_LIMIT,
                "offset": offset,
                "order_by": "series_id",
                "sort_order": "asc",
            },
        )

        batch = payload.get("seriess", [])
        all_series.extend(batch)

        if count is None:
            count = int(payload.get("count", len(all_series)))

        print(f"    release_id={release_id}: {len(all_series):,}/{count:,} series", flush=True)

        offset += REQUEST_LIMIT
        if len(all_series) >= count or not batch:
            break

        time.sleep(REQUEST_SLEEP_SECONDS)

    cache_payload = {
        "release_id": release_id,
        "pulled_at_utc": utc_now_string(),
        "count": len(all_series),
        "seriess": all_series,
    }
    tmp_path = cache_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(cache_payload, f, ensure_ascii=False)
    tmp_path.replace(cache_path)

    return all_series


# -----------------------------------------------------------------------------
# Metadata shaping
# -----------------------------------------------------------------------------

def classify_initial_relevance(row: pd.Series) -> Dict[str, str]:
    title = str(row.get("title", "")).lower()
    series_id = str(row.get("series_id", "")).upper()

    high_signal_terms = [
        "gross domestic product",
        "consumer price index",
        "personal consumption expenditures",
        "unemployment rate",
        "all employees",
        "nonfarm payroll",
        "federal funds",
        "treasury",
        "industrial production",
        "retail sales",
        "producer price index",
        "housing starts",
        "building permits",
        "personal income",
        "real disposable personal income",
    ]

    high_signal_ids = {
        "GDP", "GDPC1", "CPIAUCSL", "CPIAUCNS", "PCEPI", "PCEPILFE", "UNRATE", "PAYEMS",
        "FEDFUNDS", "DGS10", "DGS2", "INDPRO", "RSAFS", "HOUST", "PERMIT", "PCE", "PI",
    }

    if any(term in title for term in high_signal_terms) or series_id in high_signal_ids:
        return {
            "series_core_status": "Core",
            "market_relevance": "High",
            "economist_relevance": "High",
            "core_classification_basis": "Initial rule-based flag: widely followed macro/market benchmark series. Needs human review.",
        }

    return {
        "series_core_status": "TBD",
        "market_relevance": "TBD",
        "economist_relevance": "TBD",
        "core_classification_basis": "Needs review using economist/market relevance framework.",
    }


def make_series_and_map_rows(
    release_id: str,
    release_name: str,
    series_list: Iterable[Dict[str, Any]],
    refresh_timestamp: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    series_rows: List[Dict[str, Any]] = []
    map_rows: List[Dict[str, Any]] = []

    for item in series_list:
        series_id = item.get("id")
        title = item.get("title")

        row = {
            "series_id": series_id,
            "title": title,
            "frequency": item.get("frequency"),
            "frequency_short": item.get("frequency_short"),
            "units": item.get("units"),
            "units_short": item.get("units_short"),
            "seasonal_adjustment": item.get("seasonal_adjustment"),
            "seasonal_adjustment_short": item.get("seasonal_adjustment_short"),
            "observation_start": item.get("observation_start"),
            "observation_end": item.get("observation_end"),
            "last_updated": item.get("last_updated"),
            "popularity": item.get("popularity"),
            "notes": item.get("notes"),
            "metadata_source": "FRED API: release/series",
            "metadata_refresh_date": refresh_timestamp,
            "description_short": "",
            "description_medium": "",
            "description_long": "",
            "description_review_status": "not_started",
            "classification_review_status": "rule_seeded_needs_review",
        }
        row.update(classify_initial_relevance(pd.Series(row)))
        series_rows.append(row)

        map_rows.append(
            {
                "release_id": release_id,
                "release_name": release_name,
                "series_id": series_id,
                "series_title": title,
                "relationship_source": "FRED API: release/series",
                "metadata_refresh_date": refresh_timestamp,
            }
        )

    return series_rows, map_rows


def dataframe_from_rows(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# -----------------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------------

def write_csv_outputs(
    output_dir: Path,
    run_label: str,
    series_inventory: pd.DataFrame,
    release_series_map: pd.DataFrame,
    api_refresh_log: pd.DataFrame,
    series_pull_errors: pd.DataFrame,
    release_series_counts: Optional[pd.DataFrame] = None,
) -> Path:
    run_dir = output_dir / f"fred_metadata_output_{run_label}"
    run_dir.mkdir(parents=True, exist_ok=True)

    series_inventory.to_csv(run_dir / "series_inventory.csv", index=False)
    release_series_map.to_csv(run_dir / "release_series_map.csv", index=False)
    api_refresh_log.to_csv(run_dir / "api_refresh_log.csv", index=False)
    series_pull_errors.to_csv(run_dir / "series_pull_errors.csv", index=False)
    if release_series_counts is not None:
        release_series_counts.to_csv(run_dir / "release_series_counts.csv", index=False)

    return run_dir


def safe_to_excel(df: pd.DataFrame, writer: pd.ExcelWriter, sheet_name: str) -> None:
    if len(df) > EXCEL_MAX_ROWS:
        print(
            f"WARNING: {sheet_name} has {len(df):,} rows, above Excel's row limit. "
            "Skipping this sheet in Excel; use CSV output instead.",
            file=sys.stderr,
        )
        return
    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)


def write_excel_output(
    input_path: Path,
    workbook: Dict[str, pd.DataFrame],
    readme: pd.DataFrame,
    summary: pd.DataFrame,
    series_inventory: pd.DataFrame,
    release_series_map: pd.DataFrame,
    api_refresh_log: pd.DataFrame,
    series_pull_errors: pd.DataFrame,
    release_series_counts: Optional[pd.DataFrame] = None,
) -> Path:
    output_path = next_version_path(input_path)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Preserve user/original sheets, but do not preserve old generated sheets
        # because this run writes fresh versions.
        for sheet_name, df in workbook.items():
            if sheet_name in GENERATED_SHEETS:
                continue
            safe_to_excel(df, writer, sheet_name)

        safe_to_excel(readme, writer, "README_api_pull")
        safe_to_excel(summary, writer, "api_pull_summary")
        if release_series_counts is not None:
            safe_to_excel(release_series_counts, writer, "release_series_counts")
        safe_to_excel(series_inventory, writer, "series_inventory")
        safe_to_excel(release_series_map, writer, "release_series_map")
        safe_to_excel(api_refresh_log, writer, "api_refresh_log")
        safe_to_excel(series_pull_errors, writer, "series_pull_errors")

    return output_path


def make_summary(
    input_path: Path,
    release_sheet_name: str,
    refresh_timestamp: str,
    releases_processed: int,
    release_series_map: pd.DataFrame,
    series_inventory: pd.DataFrame,
    series_pull_errors: pd.DataFrame,
    csv_output_dir: Optional[Path],
    output_workbook: Optional[Path] = None,
) -> pd.DataFrame:
    rows = [
        {"metric": "input_workbook", "value": input_path.name},
        {"metric": "output_workbook", "value": output_workbook.name if output_workbook else ""},
        {"metric": "csv_output_dir", "value": str(csv_output_dir) if csv_output_dir else ""},
        {"metric": "release_sheet_used", "value": release_sheet_name},
        {"metric": "metadata_refresh_date", "value": refresh_timestamp},
        {"metric": "releases_processed", "value": releases_processed},
        {"metric": "release_series_relationships", "value": len(release_series_map)},
        {"metric": "unique_series", "value": len(series_inventory)},
        {"metric": "release_errors", "value": len(series_pull_errors)},
        {"metric": "observation_values_pulled", "value": "No; metadata only"},
    ]
    return pd.DataFrame(rows)


def make_readme() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "section": "Purpose",
                "note": "This workbook/output adds FRED series metadata for releases listed in the release catalog.",
            },
            {
                "section": "Security",
                "note": "The FRED API key is read from FRED_API_KEY and is not stored in output files.",
            },
            {
                "section": "Scope",
                "note": "This pull retrieves series metadata only, not historical observation values.",
            },
            {
                "section": "Large releases",
                "note": "Large releases are expected. Per-release JSON cache files allow resume if interrupted.",
            },
            {
                "section": "Next step",
                "note": "Use series_core_status, market_relevance, and economist_relevance as draft fields for review.",
            },
        ]
    )


# -----------------------------------------------------------------------------
# Modes
# -----------------------------------------------------------------------------

def run_preflight(api_key: str, release_table: pd.DataFrame, cache_dir: Path) -> pd.DataFrame:
    counts_rows: List[Dict[str, Any]] = []
    counts_path = counts_cache_path(cache_dir)

    existing: Dict[str, Dict[str, Any]] = {}
    if counts_path.exists():
        prior = pd.read_csv(counts_path, dtype={"release_id": str})
        existing = {str(row["release_id"]): dict(row) for _, row in prior.iterrows()}

    total = len(release_table)
    for i, release in release_table.iterrows():
        release_id = str(release["release_id"])
        release_name = str(release.get("release_name", ""))

        if release_id in existing:
            row = existing[release_id]
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: {int(row.get('series_count', 0)):,} series (cached)")
            counts_rows.append(row)
            continue

        started_at = utc_now_string()
        try:
            count = get_release_series_count(api_key, release_id)
            row = {
                "release_id": release_id,
                "release_name": release_name,
                "series_count": count,
                "status": "success",
                "checked_at_utc": utc_now_string(),
                "started_at_utc": started_at,
                "error": "",
            }
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: {count:,} series")
        except Exception as exc:
            row = {
                "release_id": release_id,
                "release_name": release_name,
                "series_count": 0,
                "status": "error",
                "checked_at_utc": utc_now_string(),
                "started_at_utc": started_at,
                "error": str(exc),
            }
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: ERROR - {exc}")

        counts_rows.append(row)
        pd.DataFrame(counts_rows).to_csv(counts_path, index=False)
        time.sleep(REQUEST_SLEEP_SECONDS)

    counts_df = pd.DataFrame(counts_rows).sort_values("series_count", ascending=False).reset_index(drop=True)
    counts_df.to_csv(counts_path, index=False)
    return counts_df


def load_counts_if_available(cache_dir: Path) -> Optional[pd.DataFrame]:
    path = counts_cache_path(cache_dir)
    if path.exists():
        return pd.read_csv(path, dtype={"release_id": str})
    return None


def run_pull(
    api_key: str,
    release_table: pd.DataFrame,
    cache_dir: Path,
    skip_large_releases: Optional[int],
    force_refresh: bool,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
    counts_df = load_counts_if_available(cache_dir)
    count_lookup: Dict[str, int] = {}
    if counts_df is not None and "series_count" in counts_df.columns:
        count_lookup = {
            str(row["release_id"]): int(row["series_count"])
            for _, row in counts_df.iterrows()
            if not pd.isna(row.get("series_count"))
        }

    refresh_timestamp = utc_now_string()
    series_rows: List[Dict[str, Any]] = []
    map_rows: List[Dict[str, Any]] = []
    log_rows: List[Dict[str, Any]] = []
    error_rows: List[Dict[str, Any]] = []

    total = len(release_table)

    for i, release in release_table.iterrows():
        release_id = str(release["release_id"])
        release_name = str(release.get("release_name", ""))
        started_at = utc_now_string()

        known_count = count_lookup.get(release_id)
        if skip_large_releases is not None and known_count is not None and known_count > skip_large_releases:
            message = f"Skipped because preflight count {known_count:,} exceeds threshold {skip_large_releases:,}."
            log_rows.append(
                {
                    "release_id": release_id,
                    "release_name": release_name,
                    "status": "skipped_large_release",
                    "series_count": known_count,
                    "started_at_utc": started_at,
                    "completed_at_utc": utc_now_string(),
                    "error": message,
                }
            )
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: SKIP - {message}")
            continue

        try:
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: pulling metadata")
            series_list = pull_series_for_release(api_key, release_id, cache_dir, force_refresh=force_refresh)
            new_series_rows, new_map_rows = make_series_and_map_rows(
                release_id=release_id,
                release_name=release_name,
                series_list=series_list,
                refresh_timestamp=refresh_timestamp,
            )
            series_rows.extend(new_series_rows)
            map_rows.extend(new_map_rows)

            log_rows.append(
                {
                    "release_id": release_id,
                    "release_name": release_name,
                    "status": "success",
                    "series_count": len(series_list),
                    "started_at_utc": started_at,
                    "completed_at_utc": utc_now_string(),
                    "error": "",
                }
            )
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: {len(series_list):,} series complete")

        except KeyboardInterrupt:
            print("\nInterrupted by user. Cached releases are preserved; rerun to resume.", file=sys.stderr)
            raise
        except Exception as exc:
            error_message = str(exc)
            log_rows.append(
                {
                    "release_id": release_id,
                    "release_name": release_name,
                    "status": "error",
                    "series_count": 0,
                    "started_at_utc": started_at,
                    "completed_at_utc": utc_now_string(),
                    "error": error_message,
                }
            )
            error_rows.append(
                {
                    "release_id": release_id,
                    "release_name": release_name,
                    "error": error_message,
                    "metadata_refresh_date": refresh_timestamp,
                }
            )
            print(f"[{i + 1:>3}/{total}] release_id={release_id}: ERROR - {error_message}")

        time.sleep(REQUEST_SLEEP_SECONDS)

    series_inventory = dataframe_from_rows(series_rows)
    release_series_map = dataframe_from_rows(map_rows)
    api_refresh_log = dataframe_from_rows(log_rows)
    series_pull_errors = dataframe_from_rows(error_rows)

    if not series_inventory.empty:
        series_inventory = (
            series_inventory
            .drop_duplicates(subset=["series_id"])
            .sort_values(["series_core_status", "popularity", "series_id"], ascending=[True, False, True])
            .reset_index(drop=True)
        )

    if not release_series_map.empty:
        release_series_map = (
            release_series_map
            .drop_duplicates(subset=["release_id", "series_id"])
            .sort_values(["release_id", "series_id"])
            .reset_index(drop=True)
        )

    return series_inventory, release_series_map, api_refresh_log, series_pull_errors, counts_df


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pull FRED release/series metadata.")
    parser.add_argument(
        "--mode",
        choices=["preflight", "pull"],
        default="pull",
        help="preflight gets series counts only; pull gets full series metadata.",
    )
    parser.add_argument(
        "--release-ids",
        default=None,
        help="Optional comma-separated release IDs to process, e.g. 1,46,52.",
    )
    parser.add_argument(
        "--skip-large-releases",
        type=int,
        default=None,
        help="Optional threshold. Requires preflight counts. In pull mode, skip releases above this series count.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore cached per-release JSON files and call FRED again.",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Write CSV outputs only. Useful for very large pulls.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    api_key = require_api_key()
    input_path = get_input_workbook_path()
    if not input_path.exists():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")

    output_dir = get_output_dir(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".fred_metadata_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    workbook = pd.read_excel(input_path, sheet_name=None)
    release_sheet_name, releases_df = find_release_sheet(workbook)
    release_table = build_release_table(releases_df)
    release_ids = parse_release_ids(args.release_ids)
    release_table = filter_release_table(release_table, release_ids)

    print(f"Input workbook: {input_path}")
    print(f"Release sheet: {release_sheet_name}")
    print(f"Output directory: {output_dir}")
    print(f"Cache directory: {cache_dir}")
    print(f"Releases to process: {len(release_table):,}")
    print(f"Mode: {args.mode}")

    run_label = timestamp_for_filename()
    refresh_timestamp = utc_now_string()

    if args.mode == "preflight":
        counts_df = run_preflight(api_key, release_table, cache_dir)
        counts_csv_dir = output_dir / f"fred_metadata_preflight_{run_label}"
        counts_csv_dir.mkdir(parents=True, exist_ok=True)
        counts_df.to_csv(counts_csv_dir / "release_series_counts.csv", index=False)

        print("\nPreflight complete.")
        print(f"Counts CSV: {counts_csv_dir / 'release_series_counts.csv'}")
        print("\nLargest releases:")
        print(counts_df[["release_id", "release_name", "series_count", "status"]].head(15).to_string(index=False))
        return

    series_inventory, release_series_map, api_refresh_log, series_pull_errors, counts_df = run_pull(
        api_key=api_key,
        release_table=release_table,
        cache_dir=cache_dir,
        skip_large_releases=args.skip_large_releases,
        force_refresh=args.force_refresh,
    )

    csv_run_dir = write_csv_outputs(
        output_dir=output_dir,
        run_label=run_label,
        series_inventory=series_inventory,
        release_series_map=release_series_map,
        api_refresh_log=api_refresh_log,
        series_pull_errors=series_pull_errors,
        release_series_counts=counts_df,
    )

    readme = make_readme()
    summary = make_summary(
        input_path=input_path,
        release_sheet_name=release_sheet_name,
        refresh_timestamp=refresh_timestamp,
        releases_processed=len(release_table),
        release_series_map=release_series_map,
        series_inventory=series_inventory,
        series_pull_errors=series_pull_errors,
        csv_output_dir=csv_run_dir,
        output_workbook=None,
    )

    output_workbook: Optional[Path] = None
    if not args.no_excel:
        output_workbook = write_excel_output(
            input_path=input_path,
            workbook=workbook,
            readme=readme,
            summary=summary,
            series_inventory=series_inventory,
            release_series_map=release_series_map,
            api_refresh_log=api_refresh_log,
            series_pull_errors=series_pull_errors,
            release_series_counts=counts_df,
        )

        # Update summary CSV with workbook name.
        summary = make_summary(
            input_path=input_path,
            release_sheet_name=release_sheet_name,
            refresh_timestamp=refresh_timestamp,
            releases_processed=len(release_table),
            release_series_map=release_series_map,
            series_inventory=series_inventory,
            series_pull_errors=series_pull_errors,
            csv_output_dir=csv_run_dir,
            output_workbook=output_workbook,
        )
        summary.to_csv(csv_run_dir / "api_pull_summary.csv", index=False)

    print("\nDone.")
    if output_workbook:
        print(f"Output workbook: {output_workbook}")
    else:
        print("Output workbook: skipped (--no-excel)")
    print(f"CSV output directory: {csv_run_dir}")
    print(f"Unique series: {len(series_inventory):,}")
    print(f"Release-series relationships: {len(release_series_map):,}")
    print(f"Errors: {len(series_pull_errors):,}")
    print("\nNote: Cached release JSON files let you rerun/resume without re-pulling completed releases.")


if __name__ == "__main__":
    main()
