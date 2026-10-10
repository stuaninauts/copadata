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

# Fjelstul World Cup Database: historical editions (CC-BY-SA 4.0, see ADR 0005).
# Pinned to a commit so a re-run always reads the same data.
FJELSTUL_COMMIT = "35a8667f518b07469182ae16d35574dd0e7a00fb"
FJELSTUL_URL = "https://raw.githubusercontent.com/jfjelstul/worldcup/{commit}/data-csv/{name}.csv"
FJELSTUL_TABLES = ("matches", "goals")
FJELSTUL_RAW = RAW / "fjelstul"
# First edition with the modern shape: group stage, then knockout from the round of 16.
FIRST_HISTORICAL_YEAR = 1986

MATCHES_PARQUET = PROCESSED / "matches.parquet"
TEAM_MATCHES_PARQUET = PROCESSED / "team_matches.parquet"
GOALS_PARQUET = PROCESSED / "goals.parquet"

# Points for a win in the group table: 2 until 1990, 3 from 1994 on.
THREE_POINTS_FROM = 1994

# Late goal: scored at minute 80 or later in regulation time.
LATE_GOAL_MIN = 80
