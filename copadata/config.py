"""Central configuration: paths, data source, and metric constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"

SEASON = 2026
# OpenFootball: public World Cup data, no API key.
OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)
RAW_JSON = RAW / f"worldcup-{SEASON}.json"
MATCHES_PARQUET = PROCESSED / "matches.parquet"
TEAM_MATCHES_PARQUET = PROCESSED / "team_matches.parquet"
GOALS_PARQUET = PROCESSED / "goals.parquet"

# Late goal: scored at minute 80 or later in regulation time.
LATE_GOAL_MIN = 80
