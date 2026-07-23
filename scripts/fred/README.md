# FRED Metadata Pipeline Scripts

These scripts support the local FRED metadata catalog workflow.

## Scripts

### `pull_fred_release_series_metadata.py`

Pulls FRED release-series metadata using the FRED API.

Primary outputs are local CSV files and per-release JSON cache/checkpoints. The large metadata dump is intentionally ignored by Git.

Typical full metadata pull:

```bash
python3 scripts/fred/pull_fred_release_series_metadata.py --mode pull --no-excel
```

Useful preflight count run:

```bash
python3 scripts/fred/pull_fred_release_series_metadata.py --mode preflight
```

### `analyze_fred_metadata_catalog.py`

Analyzes the local CSV metadata dump without calling the FRED API.

Typical review run:

```bash
python3 scripts/fred/analyze_fred_metadata_catalog.py --latest --top-n 5000 --candidate-core-score-cutoff 75
```

## Environment Variables

The scripts expect these environment variables when needed:

- `FRED_API_KEY`
- `FRED_RELEASE_WORKBOOK`
- `FRED_METADATA_OUTPUT_DIR`

The API key should never be committed to Git.

## Git Policy

The following are intentionally not committed:

- raw FRED metadata dumps
- per-release JSON cache files
- generated analysis folders
- local virtual environments

The committed app-facing output is:

```text
seeds/fred_core_series_seed.csv
```
