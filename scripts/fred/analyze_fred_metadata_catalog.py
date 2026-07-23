#!/usr/bin/env python3
"""
Analyze a local FRED release-series metadata dump.

This script reads the CSV outputs produced by pull_fred_release_series_metadata.py
and creates compact, reviewable summary outputs. It does NOT call the FRED API.

Typical usage from repo root:

  python3 data/analyze_fred_metadata_catalog.py --latest --top-n 5000
  python3 data/analyze_fred_metadata_catalog.py --latest --top-n 5000 --candidate-core-score-cutoff 90

Outputs:
  - analysis_summary.csv
  - release_series_counts_summary.csv
  - frequency_summary.csv
  - frequency_short_summary.csv
  - units_summary.csv
  - seasonal_adjustment_summary.csv
  - popularity_summary.csv
  - top_popular_series.csv
  - candidate_core_series.csv
  - curated_core_series.csv
  - core_watchlist_series.csv
  - stale_or_discontinued_series.csv
  - release_core_summary.csv
  - fred_metadata_review.xlsx
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


SERIES_FILE = "series_inventory.csv"
MAP_FILE = "release_series_map.csv"
LOG_FILE = "api_refresh_log.csv"
ERRORS_FILE = "series_pull_errors.csv"
COUNTS_FILE = "release_series_counts.csv"

EXCEL_MAX_ROWS_PER_SHEET = 100_000
DEFAULT_TOP_N = 5000
DEFAULT_CANDIDATE_CORE_SCORE_CUTOFF = 90
STALE_YEAR_CUTOFF = 2019

BENCHMARK_CORE_SERIES_IDS = {
    # Growth / output
    "GDP", "GDPC1", "A191RL1Q225SBEA", "GDI", "INDPRO", "TCU",
    # Labor
    "UNRATE", "PAYEMS", "ICSA", "CCSA", "JTSJOL", "CIVPART", "EMRATIO",
    "CES0500000003", "AHETPI", "AWHMAN",
    # Inflation / prices
    "CPIAUCSL", "CPILFESL", "CPIAUCNS", "PCEPI", "PCEPILFE", "PPIACO", "PPIFIS",
    "T5YIE", "T10YIE", "MICH", "EXPINF1YR", "EXPINF5YR",
    # Consumer / household
    "PCE", "PCEC96", "PI", "DSPIC96", "PSAVERT", "RSAFS", "UMCSENT",
    # Housing
    "HOUST", "PERMIT", "HSN1F", "EXHOSLUSM495S", "CSUSHPINSA", "MSPUS",
    "MORTGAGE30US",
    # Rates / markets
    "FEDFUNDS", "DFF", "SOFR", "DGS1MO", "DGS3MO", "DGS6MO", "DGS1",
    "DGS2", "DGS5", "DGS10", "DGS30", "T10Y2Y", "T10Y3M", "DFII10",
    "BAMLH0A0HYM2", "BAMLC0A0CM", "SP500", "VIXCLS",
    # Money / banking / credit
    "M1SL", "M2SL", "TOTRESNS", "WALCL", "BUSLOANS", "TOTLL", "NFCI",
    # Trade / fiscal
    "BOPGSTB", "NETEXP", "EXPGS", "IMPGS", "GFDEBTN", "GFDEGDQ188S",
}

DOMAIN_KEYWORDS = {
    "Trade/Fiscal": [
        "federal debt", "public debt", "debt as percent of gross domestic product",
        "federal receipts", "federal outlays", "government current receipts",
        "government current expenditures", "treasury general account", "trade balance",
        "exports", "imports", "balance of payments", "net exports",
    ],
    "Housing": [
        "housing starts", "building permits", "new home sales", "existing home sales",
        "home price", "house price", "case-shiller", "mortgage", "median sales price of houses",
        "housing inventory", "market hotness", "residential construction",
    ],
    "Rates/Markets": [
        "treasury", "federal funds", "secured overnight financing rate", "sofr",
        "yield", "spread", "corporate bond", "high yield", "option-adjusted spread",
        "mortgage-backed", "exchange rate", "dollar index", "s&p 500", "volatility index",
        "vix", "market yield", "inflation-indexed",
    ],
    "Inflation/Prices": [
        "consumer price index", "cpi", "pce price", "chain-type price index",
        "price index", "producer price index", "ppi", "inflation expectation",
        "inflation rate", "breakeven inflation", "import price", "export price",
    ],
    "Labor": [
        "unemployment", "payroll", "employment", "labor force", "job openings",
        "initial claims", "continued claims", "average hourly earnings", "hours worked",
    ],
    "Money/Credit/Banking": [
        "money stock", "m1", "m2", "bank credit", "commercial and industrial loans",
        "reserves", "federal reserve balance sheet", "financial conditions", "all commercial banks",
        "assets: total assets", "reserve balances",
    ],
    "Consumer": [
        "personal consumption", "personal income", "disposable personal income", "retail sales",
        "consumer sentiment", "consumer credit", "personal saving", "household",
    ],
    "Growth/Output": [
        "gross domestic product", "real gdp", "gdp", "gross domestic income",
        "industrial production", "capacity utilization", "productivity", "durable goods",
        "factory orders", "inventories",
    ],
}

CORE_KEYWORDS = sorted({kw for kws in DOMAIN_KEYWORDS.values() for kw in kws})

NON_CORE_HINTS = [
    "county", "msa", "metropolitan", "micropolitan", "zip", "tract",
    "all-transactions house price index for", "resident population in",
    "estimate", "projection", "forecast", "vintage", "discontinued",
    "by county", "by state", "by race", "by ethnicity", "by age", "by sex",
]

STANDARD_MACRO_UNIT_HINTS = [
    "percent", "index", "billions", "millions", "dollars", "number", "rate",
    "percent change", "percent of gdp", "chained",
]

OUTPUT_SERIES_COLUMNS = [
    "series_id", "title", "candidate_core_score", "candidate_core_reasons",
    "suggested_series_core_status", "suggested_core_domain",
    "suggested_market_relevance", "suggested_economist_relevance",
    "popularity", "frequency", "units", "seasonal_adjustment",
    "observation_start", "observation_end", "last_updated",
    "series_core_status", "market_relevance", "economist_relevance",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def find_latest_output_dir(base_dir: Path) -> Path:
    candidates = sorted(
        [p for p in base_dir.glob("fred_metadata_output_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No fred_metadata_output_* folders found under {base_dir}")
    return candidates[0]


def require_file(input_dir: Path, filename: str) -> Path:
    path = input_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def read_existing_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False)
    except pd.errors.EmptyDataError:
        print(f"Info: {path.name} is empty; continuing with empty table.", file=sys.stderr)
        return pd.DataFrame()


def safe_read_series_columns(series_path: Path, columns: list[str]) -> pd.DataFrame:
    header = pd.read_csv(series_path, nrows=0).columns.tolist()
    usecols = [c for c in columns if c in header]
    missing = sorted(set(columns) - set(usecols))
    if missing:
        print(f"Warning: missing columns in {series_path.name}: {missing}", file=sys.stderr)
    return pd.read_csv(series_path, usecols=usecols, low_memory=False)


def value_summary(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "series_count", "share"])
    counts = (
        df[column]
        .fillna("[missing]")
        .astype(str)
        .value_counts(dropna=False)
        .rename_axis(column)
        .reset_index(name="series_count")
    )
    total = counts["series_count"].sum()
    counts["share"] = counts["series_count"] / total if total else 0
    return counts


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def is_timely_frequency(freq: str) -> bool:
    f = normalize_text(freq)
    return any(token in f for token in ["daily", "weekly", "monthly", "quarterly"])


def is_seasonally_adjusted(sa: str) -> bool:
    s = normalize_text(sa)
    return bool(s) and "seasonally adjusted" in s and "not seasonally adjusted" not in s


def has_standard_macro_units(units: str) -> bool:
    u = normalize_text(units)
    return any(hint in u for hint in STANDARD_MACRO_UNIT_HINTS)


def infer_domain(title: object, series_id: object = "") -> str:
    text = f"{normalize_text(series_id)} {normalize_text(title)}"

    # Series-ID overrides where title keywords can be ambiguous.
    sid = str(series_id).strip().upper()
    if sid in {"GFDEBTN", "GFDEGDQ188S", "BOPGSTB", "NETEXP", "EXPGS", "IMPGS"}:
        return "Trade/Fiscal"
    if sid in {"CSUSHPINSA", "MORTGAGE30US", "HOUST", "PERMIT", "HSN1F", "MSPUS", "EXHOSLUSM495S"}:
        return "Housing"
    if sid in {"DFII10", "T10YIE", "T5YIE"}:
        return "Rates/Markets"

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if contains_any(text, keywords):
            return domain
    return "Other/Unclassified"


def score_candidate(row: pd.Series) -> tuple[int, str]:
    title = normalize_text(row.get("title", ""))
    sid = str(row.get("series_id", "")).strip().upper()
    frequency = normalize_text(row.get("frequency", ""))
    units = normalize_text(row.get("units", ""))
    sa = normalize_text(row.get("seasonal_adjustment", ""))
    popularity = pd.to_numeric(row.get("popularity", 0), errors="coerce")
    popularity = 0 if pd.isna(popularity) else int(popularity)

    score = 0
    reasons: list[str] = []

    if sid in BENCHMARK_CORE_SERIES_IDS:
        score += 50
        reasons.append("benchmark_core_series_id")

    if popularity >= 90:
        score += 35
        reasons.append("popularity>=90")
    elif popularity >= 80:
        score += 25
        reasons.append("popularity>=80")
    elif popularity >= 60:
        score += 15
        reasons.append("popularity>=60")
    elif popularity >= 40:
        score += 8
        reasons.append("popularity>=40")

    if contains_any(title, CORE_KEYWORDS):
        score += 25
        reasons.append("macro_market_keyword")

    if is_timely_frequency(frequency):
        score += 20
        reasons.append("timely_frequency")

    if is_seasonally_adjusted(sa):
        score += 5
        reasons.append("seasonally_adjusted")

    if has_standard_macro_units(units):
        score += 15
        reasons.append("standard_macro_units")

    # Penalize highly granular geography / narrow detail unless explicitly benchmarked.
    if sid not in BENCHMARK_CORE_SERIES_IDS and contains_any(title, NON_CORE_HINTS):
        score -= 25
        reasons.append("granular_or_non_core_hint")

    return score, "; ".join(reasons)


def suggest_status(score: int, series_id: object, candidate_cutoff: int = DEFAULT_CANDIDATE_CORE_SCORE_CUTOFF) -> str:
    sid = str(series_id).strip().upper()
    if sid in BENCHMARK_CORE_SERIES_IDS:
        return "Core"
    if score >= candidate_cutoff:
        return "Candidate-Core"
    return "Non-core"


def suggest_relevance(status: str, score: int) -> tuple[str, str]:
    if status == "Core":
        return "High", "High"
    if status == "Candidate-Core":
        if score >= 130:
            return "High", "High"
        return "Medium", "High"
    if score >= 80:
        return "Medium", "Medium"
    if score >= 50:
        return "Low", "Medium"
    return "Low", "Low"


def add_core_suggestions(series: pd.DataFrame, candidate_cutoff: int = DEFAULT_CANDIDATE_CORE_SCORE_CUTOFF) -> pd.DataFrame:
    out = series.copy()
    scored = out.apply(score_candidate, axis=1, result_type="expand")
    out["candidate_core_score"] = scored[0].astype(int)
    out["candidate_core_reasons"] = scored[1]
    out["suggested_series_core_status"] = [
        suggest_status(score, sid, candidate_cutoff) for score, sid in zip(out["candidate_core_score"], out.get("series_id", ""))
    ]
    out["suggested_core_domain"] = [infer_domain(t, sid) for t, sid in zip(out.get("title", ""), out.get("series_id", ""))]

    relevance = [suggest_relevance(status, score) for status, score in zip(out["suggested_series_core_status"], out["candidate_core_score"])]
    out["suggested_market_relevance"] = [m for m, _ in relevance]
    out["suggested_economist_relevance"] = [e for _, e in relevance]

    for col in ["series_core_status", "market_relevance", "economist_relevance"]:
        if col not in out.columns:
            out[col] = "TBD"
        else:
            out[col] = out[col].fillna("TBD")

    return out


def top_by_popularity(series: pd.DataFrame, top_n: int) -> pd.DataFrame:
    out = series.copy()
    out["popularity_numeric"] = pd.to_numeric(out.get("popularity", 0), errors="coerce").fillna(0)
    out = out.sort_values(["popularity_numeric", "series_id"], ascending=[False, True]).head(top_n)
    return out.drop(columns=["popularity_numeric"], errors="ignore")


def stale_or_discontinued(series: pd.DataFrame, top_n: int) -> pd.DataFrame:
    out = series.copy()
    if "observation_end" not in out.columns:
        return pd.DataFrame()
    end_dates = pd.to_datetime(out["observation_end"], errors="coerce")
    stale = out[end_dates.dt.year.fillna(0).astype(int) <= STALE_YEAR_CUTOFF].copy()
    if "popularity" in stale.columns:
        stale["popularity_numeric"] = pd.to_numeric(stale["popularity"], errors="coerce").fillna(0)
        stale = stale.sort_values(["popularity_numeric", "observation_end"], ascending=[False, True])
        stale = stale.drop(columns=["popularity_numeric"], errors="ignore")
    return stale.head(top_n)


def make_release_core_summary(release_counts: pd.DataFrame, release_map: pd.DataFrame, classified: pd.DataFrame) -> pd.DataFrame:
    if release_map.empty or classified.empty or "series_id" not in release_map.columns:
        return release_counts.copy()

    map_cols = [c for c in ["release_id", "release_name", "series_id"] if c in release_map.columns]
    merged = release_map[map_cols].merge(
        classified[["series_id", "suggested_series_core_status", "suggested_core_domain"]],
        on="series_id",
        how="left",
    )
    grouped = merged.groupby(["release_id", "release_name"], dropna=False).agg(
        release_series_relationships=("series_id", "count"),
        core_series_count=("suggested_series_core_status", lambda s: int((s == "Core").sum())),
        candidate_core_series_count=("suggested_series_core_status", lambda s: int((s == "Candidate-Core").sum())),
    ).reset_index()

    def top_domain(s: pd.Series) -> str:
        vc = s.dropna().astype(str).value_counts()
        return vc.index[0] if not vc.empty else "Other/Unclassified"

    domains = merged.groupby(["release_id", "release_name"], dropna=False)["suggested_core_domain"].apply(top_domain).reset_index(name="dominant_suggested_domain")
    grouped = grouped.merge(domains, on=["release_id", "release_name"], how="left")
    grouped["core_or_candidate_count"] = grouped["core_series_count"] + grouped["candidate_core_series_count"]
    grouped = grouped.sort_values(["core_series_count", "candidate_core_series_count", "release_series_relationships"], ascending=[False, False, False])
    return grouped


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = ""
    return out[columns]


def write_excel_review(output_path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]
            if df is None or df.empty:
                pd.DataFrame({"message": ["No rows"]}).to_excel(writer, sheet_name=safe_name, index=False)
            else:
                df.head(EXCEL_MAX_ROWS_PER_SHEET).to_excel(writer, sheet_name=safe_name, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze local FRED metadata CSV outputs.")
    parser.add_argument("--input-dir", help="Path to fred_metadata_output_* directory.")
    parser.add_argument("--latest", action="store_true", help="Analyze latest fred_metadata_output_* under FRED_METADATA_OUTPUT_DIR or ./data/fred_metadata.")
    parser.add_argument("--base-dir", help="Base metadata directory used with --latest.")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help=f"Top rows for review outputs. Default: {DEFAULT_TOP_N}")
    parser.add_argument(
        "--candidate-core-score-cutoff",
        type=int,
        default=DEFAULT_CANDIDATE_CORE_SCORE_CUTOFF,
        help=(
            "Minimum candidate_core_score for non-benchmark series to be marked "
            f"Candidate-Core. Default: {DEFAULT_CANDIDATE_CORE_SCORE_CUTOFF}"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.latest:
        base_dir = Path(args.base_dir or os.getenv("FRED_METADATA_OUTPUT_DIR", "data/fred_metadata")).expanduser().resolve()
        input_dir = find_latest_output_dir(base_dir)
    elif args.input_dir:
        input_dir = Path(args.input_dir).expanduser().resolve()
    else:
        raise SystemExit("Use --latest or --input-dir PATH")

    series_path = require_file(input_dir, SERIES_FILE)
    map_path = input_dir / MAP_FILE
    counts_path = input_dir / COUNTS_FILE
    log_path = input_dir / LOG_FILE
    errors_path = input_dir / ERRORS_FILE

    output_dir = input_dir / f"analysis_{utc_stamp()}"
    output_dir.mkdir(parents=True, exist_ok=False)

    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    series_columns = [
        "series_id", "title", "frequency", "frequency_short", "units", "units_short",
        "seasonal_adjustment", "seasonal_adjustment_short", "observation_start",
        "observation_end", "last_updated", "popularity", "notes",
        "series_core_status", "market_relevance", "economist_relevance",
    ]
    series = safe_read_series_columns(series_path, series_columns)
    release_map = read_existing_csv(map_path)
    release_counts = read_existing_csv(counts_path)
    refresh_log = read_existing_csv(log_path)
    errors = read_existing_csv(errors_path)

    classified = add_core_suggestions(series, candidate_cutoff=args.candidate_core_score_cutoff)
    classified = classified.sort_values(
        ["candidate_core_score", "popularity", "series_id"],
        ascending=[False, False, True],
    )

    candidate_core = ensure_columns(classified.head(args.top_n), OUTPUT_SERIES_COLUMNS)
    curated_core = ensure_columns(
        classified[classified["suggested_series_core_status"] == "Core"].sort_values(
            ["candidate_core_score", "popularity", "series_id"], ascending=[False, False, True]
        ),
        OUTPUT_SERIES_COLUMNS,
    )
    core_watchlist = ensure_columns(
        classified[classified["suggested_series_core_status"] == "Candidate-Core"].sort_values(
            ["candidate_core_score", "popularity", "series_id"], ascending=[False, False, True]
        ).head(args.top_n),
        OUTPUT_SERIES_COLUMNS,
    )

    top_popular = ensure_columns(top_by_popularity(classified, args.top_n), OUTPUT_SERIES_COLUMNS)
    stale = stale_or_discontinued(classified, args.top_n)
    stale = ensure_columns(stale, [c for c in OUTPUT_SERIES_COLUMNS if c in classified.columns]) if not stale.empty else stale

    frequency_summary = value_summary(series, "frequency")
    frequency_short_summary = value_summary(series, "frequency_short")
    units_summary = value_summary(series, "units")
    seasonal_summary = value_summary(series, "seasonal_adjustment")

    pop = pd.to_numeric(series.get("popularity", pd.Series(dtype=float)), errors="coerce").fillna(0)
    popularity_summary = pd.DataFrame({
        "popularity_bucket": ["0", "1-25", "26-50", "51-75", "76-90", "91-100"],
        "series_count": [
            int((pop == 0).sum()),
            int(((pop >= 1) & (pop <= 25)).sum()),
            int(((pop >= 26) & (pop <= 50)).sum()),
            int(((pop >= 51) & (pop <= 75)).sum()),
            int(((pop >= 76) & (pop <= 90)).sum()),
            int(((pop >= 91) & (pop <= 100)).sum()),
        ],
    })

    if release_counts.empty and not release_map.empty and "release_id" in release_map.columns:
        group_cols = ["release_id"] + (["release_name"] if "release_name" in release_map.columns else [])
        release_counts = release_map.groupby(group_cols, dropna=False).size().reset_index(name="series_count")
        release_counts["status"] = "success"
    release_counts_summary = release_counts.sort_values("series_count", ascending=False) if "series_count" in release_counts.columns else release_counts
    release_core_summary = make_release_core_summary(release_counts_summary, release_map, classified)

    analysis_summary = pd.DataFrame([
        {"metric": "input_dir", "value": str(input_dir)},
        {"metric": "output_dir", "value": str(output_dir)},
        {"metric": "unique_series_rows", "value": len(series)},
        {"metric": "release_series_relationships", "value": len(release_map)},
        {"metric": "refresh_log_rows", "value": len(refresh_log)},
        {"metric": "error_rows", "value": len(errors)},
        {"metric": "top_n", "value": args.top_n},
        {"metric": "candidate_core_score_cutoff", "value": args.candidate_core_score_cutoff},
        {"metric": "curated_core_series", "value": len(curated_core)},
        {"metric": "core_watchlist_series", "value": len(core_watchlist)},
    ])

    outputs = {
        "analysis_summary.csv": analysis_summary,
        "release_series_counts_summary.csv": release_counts_summary,
        "release_core_summary.csv": release_core_summary,
        "frequency_summary.csv": frequency_summary,
        "frequency_short_summary.csv": frequency_short_summary,
        "units_summary.csv": units_summary,
        "seasonal_adjustment_summary.csv": seasonal_summary,
        "popularity_summary.csv": popularity_summary,
        "top_popular_series.csv": top_popular,
        "candidate_core_series.csv": candidate_core,
        "curated_core_series.csv": curated_core,
        "core_watchlist_series.csv": core_watchlist,
        "stale_or_discontinued_series.csv": stale,
    }

    for filename, df in outputs.items():
        df.to_csv(output_dir / filename, index=False)

    write_excel_review(
        output_dir / "fred_metadata_review.xlsx",
        {
            "analysis_summary": analysis_summary,
            "curated_core_series": curated_core,
            "core_watchlist_series": core_watchlist,
            "candidate_core_series": candidate_core,
            "top_popular_series": top_popular,
            "release_core_summary": release_core_summary,
            "release_counts": release_counts_summary,
            "frequency_summary": frequency_summary,
            "units_summary": units_summary,
            "popularity_summary": popularity_summary,
        },
    )

    print("Analysis complete")
    print(f"Unique series rows analyzed: {len(series):,}")
    print(f"Release-series relationships analyzed: {len(release_map):,}")
    print(f"Curated core rows written: {len(curated_core):,}")
    print(f"Core watchlist rows written: {len(core_watchlist):,}")
    print(f"Candidate core rows written: {len(candidate_core):,}")
    print(f"Output directory: {output_dir}")
    print(f"Review workbook: {output_dir / 'fred_metadata_review.xlsx'}")


if __name__ == "__main__":
    main()
