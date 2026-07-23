# FRED Core Series Seed

This file is a compact app-ready seed generated from the local FRED release-series metadata catalog.

## Files

- `fred_core_series_seed.csv`: combined app seed of accepted core and candidate-core FRED series.

## Source

Generated from:

```text
data/fred_metadata/fred_metadata_output_20260723_010754/analysis_20260723_025957
```

Raw metadata source:

```text
data/fred_metadata/fred_metadata_output_20260723_010754
```

## Generation Logic

The seed combines:

- `curated_core_series.csv`
- `core_watchlist_series.csv`

using:

- accepted benchmark/core series as `Core`
- high-scoring review candidates as `Candidate-Core`

Current cutoff:

```text
candidate_core_score_cutoff = 75
top_n = 5000
```

## Review Fields

- `app_core_status`: Core or Candidate-Core
- `review_status`: accepted_core_seed or needs_review
- `suggested_core_domain`: macro/market domain
- `suggested_market_relevance`: High/Medium/Low
- `suggested_economist_relevance`: High/Medium/Low

## Notes

The full FRED metadata dump is intentionally not committed to Git.
