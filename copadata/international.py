"""Adapter: international results since 1872 (martj42, CC0) -> Elo and processed tables (ADR 0009).

- `build`: every international match with its pre-match Elo (elo.py), match weight and shootout;
  and the goals with minute.
- `add_elo`: the pre-match Elo of both teams on each World Cup match. Every match must find its
  pair in the international results (same date, same teams); a miss stops the pipeline.
"""
from __future__ import annotations

import pandas as pd

from copadata import config, elo

KEY = ["date", "home_team", "away_team"]


def build(raw: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(results with Elo, goals) from the raw CSVs. `results` keeps the file order (chronological)."""
    results = elo.ratings(raw["results"]).assign(k=lambda d: d["tournament"].map(elo.k_factor))
    shootouts = raw["shootouts"][[*KEY, "winner", "first_shooter"]].rename(columns={"winner": "shootout_winner"})
    results = results.merge(shootouts.drop_duplicates(KEY), on=KEY, how="left", validate="m:1")
    goals = raw["goalscorers"][[*KEY, "team", "minute", "own_goal", "penalty"]].assign(
        minute=lambda d: d["minute"].astype("Int64"),
        own_goal=lambda d: d["own_goal"].astype(bool),
        penalty=lambda d: d["penalty"].astype(bool),
    )
    return results, goals


def _name(team: str, year: int) -> str:
    since = config.ELO_NAMES_SINCE.get(team)
    if since and year >= since[0]:
        return since[1]
    return config.ELO_NAMES.get(team, team)


def add_elo(matches: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """`matches` plus elo1 and elo2: each team's rating before the match."""
    wc = results[results["tournament"] == "FIFA World Cup"]
    lookup = {(r.date, r.home_team, r.away_team): (r.elo_home, r.elo_away) for r in wc.itertuples()}
    elo1, elo2, missing = [], [], []
    for m in matches.itertuples():
        t1, t2 = _name(m.team1, m.year), _name(m.team2, m.year)
        if (m.date, t1, t2) in lookup:
            a, b = lookup[(m.date, t1, t2)]
        elif (m.date, t2, t1) in lookup:
            b, a = lookup[(m.date, t2, t1)]
        else:
            missing.append(f"{m.date} {m.team1} x {m.team2}")
            a = b = None
        elo1.append(a)
        elo2.append(b)
    if missing:
        raise ValueError(f"{len(missing)} World Cup match(es) not in the international results: {missing[:5]}")
    return matches.assign(elo1=elo1, elo2=elo2)
