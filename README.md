# CopaData

Data-analysis engine for the 2026 World Cup, built on the public
[OpenFootball](https://github.com/openfootball/worldcup.json) dataset — **no API key**.

Downloads the matches, computes time and decision metrics (winning goal, late goal, extra-time
goal, comeback, survival goal) and each team's situation within its group, and materializes
everything to Parquet ready for analysis.

## Run

```bash
pip install -r requirements.txt
python -m copadata.pipeline            # download and reprocess
python -m copadata.pipeline --offline  # reprocess the snapshot already downloaded
```

The pipeline is **idempotent and cumulative**: re-running picks up new matches as the
tournament progresses.

## Outputs (`data/processed/`)

| File | Grain | Contents |
|---|---|---|
| `matches.parquet` | 1 row/match | score, stage, margin, extra time / penalties, time & decision metrics |
| `team_matches.parquet` | 2 rows/match | each team's perspective + group situation (matchday, points/position before the match) |
| `goals.parquet` | 1 row/goal | minute, extra time, late goal, own goal, penalty |

## Structure

```
copadata/   ingest · transform · derive · metrics · pipeline · config
data/       raw/ (raw snapshot)   ·   processed/ (parquets)
```

Metric definitions are concentrated in `copadata/metrics.py`.

---

> 🚧 Work in progress.
