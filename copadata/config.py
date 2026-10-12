"""Central configuration: paths, data source, and metric constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"

SEASON = 2026
# OpenFootball: public World Cup data, no API key. Pinned to the last commit of the finished
# 2026 file (ADR 0006), so a re-run always reads the same data.
OPENFOOTBALL_COMMIT = "0c4b73b3c1fbb877e8274eb321b1ec4d9220a3a4"
OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/{commit}/2026/worldcup.json"
)
RAW_JSON = RAW / f"worldcup-{SEASON}.json"

# Fjelstul World Cup Database: historical editions (CC-BY-SA 4.0, see ADR 0005).
# Pinned to a commit so a re-run always reads the same data.
FJELSTUL_COMMIT = "35a8667f518b07469182ae16d35574dd0e7a00fb"
FJELSTUL_URL = "https://raw.githubusercontent.com/jfjelstul/worldcup/{commit}/data-csv/{name}.csv"
FJELSTUL_TABLES = ("matches", "goals", "penalty_kicks")
FJELSTUL_RAW = RAW / "fjelstul"
# First edition with the modern shape: group stage, then knockout from the round of 16.
FIRST_HISTORICAL_YEAR = 1986

# International results since 1872 (martj42/international_results, CC0): team strength by Elo
# (ADR 0009). Pinned to a commit so a re-run always reads the same data.
INTERNATIONAL_COMMIT = "d5bd6de012c87e2f325de602ae77fe2f9ab61ef3"
INTERNATIONAL_URL = "https://raw.githubusercontent.com/martj42/international_results/{commit}/{name}.csv"
INTERNATIONAL_TABLES = ("results", "shootouts", "goalscorers")
INTERNATIONAL_RAW = RAW / "international"

MATCHES_PARQUET = PROCESSED / "matches.parquet"
TEAM_MATCHES_PARQUET = PROCESSED / "team_matches.parquet"
GOALS_PARQUET = PROCESSED / "goals.parquet"
PENALTY_KICKS_PARQUET = PROCESSED / "penalty_kicks.parquet"
INTERNATIONAL_PARQUET = PROCESSED / "international.parquet"
INTERNATIONAL_GOALS_PARQUET = PROCESSED / "international_goals.parquet"

# Public export read by the web site (ADR 0006/0007). Versioned, licensed CC-BY-SA 4.0.
EXPORT = ROOT / "web" / "public" / "data"

# One name per team across sources: OpenFootball spelling -> Fjelstul spelling.
TEAM_NAMES = {"USA": "United States", "Bosnia & Herzegovina": "Bosnia and Herzegovina"}
# Historical names -> the successor federation's name in the international results (Elo lookup).
ELO_NAMES = {"West Germany": "Germany", "Soviet Union": "Russia", "Serbia and Montenegro": "Serbia"}
# ... and names that changed meaning: FR Yugoslavia (1992 on) is "Serbia" there; 1990's Yugoslavia is not.
ELO_NAMES_SINCE = {"Yugoslavia": (1992, "Serbia")}

# World Football Elo (eloratings.net method, ADR 0009): starting rating, home advantage, and K
# by match weight. Tournaments not listed weigh ELO_K_OTHER.
ELO_START = 1500
ELO_HOME = 100
ELO_K_WORLD_CUP = 60
ELO_K_CONTINENTAL = 50
ELO_K_QUALIFIER = 40
ELO_K_OTHER = 30
ELO_K_FRIENDLY = 20
ELO_CONTINENTAL = ("UEFA Euro", "Copa América", "African Cup of Nations", "AFC Asian Cup", "Gold Cup",
                   "CONCACAF Championship", "Oceania Nations Cup", "Confederations Cup")
ELO_NATIONS_LEAGUES = ("UEFA Nations League", "CONCACAF Nations League")

# Points for a win in the group table: 2 until 1990, 3 from 1994 on.
THREE_POINTS_FROM = 1994

# Late goal: scored at minute 80 or later in regulation time.
LATE_GOAL_MIN = 80

# Group zone before the match (in-group proxy): positions 1-2 qualification, 3-4 danger.
ZONE_QUALIFICATION_MAX = 2

# Format eras (number of teams), for comparisons across editions: (label, first year, last year).
FORMAT_ERAS = (("24-teams", 1986, 1994), ("32-teams", 1998, 2022), ("48-teams", 2026, 2026))
# Lopsided match: won by this many goals or more.
BIG_MARGIN = 3
# Goal-minute bands in regulation (upper bounds; the last one includes stoppage time).
GOAL_BANDS = (15, 30, 45, 60, 75, 90)

# Myths (ADR 0008): one effect, one interval and a verdict rule fixed before running.
# Bootstrap/permutation draws with a fixed seed, so the export is reproducible.
MYTH_DRAWS = 2000
MYTH_SEED = 2026
# A "true" verdict needs the same direction in both halves of the history.
MYTH_HALVES = ((1986, 2002), (2006, 2026))
# Smallest effect the claim implies: an interval wholly below it makes the claim a myth.
MYTH_THRESHOLD = 0.05
# Host countries per edition, for the home-advantage myth.
HOSTS = {1986: ("Mexico",), 1990: ("Italy",), 1994: ("United States",), 1998: ("France",),
         2002: ("South Korea", "Japan"), 2006: ("Germany",), 2010: ("South Africa",), 2014: ("Brazil",),
         2018: ("Russia",), 2022: ("Qatar",), 2026: ("United States", "Mexico", "Canada")}
# Teams need this many matches to enter the late-specialist funnel.
MYTH_MIN_MATCHES = 10
