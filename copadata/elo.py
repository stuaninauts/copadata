"""elo.py: team strength as World Football Elo ratings, the single home for it (ADR 0009).

Ratings are computed over every international match in date order, starting at ELO_START:

    R' = R + K * G * (W - We),   We = 1 / (10 ** (-dr / 400) + 1)

- dr: rating difference, plus ELO_HOME for the home team unless the ground is neutral;
- K: match weight by tournament (k_factor);
- G: goal-difference multiplier (goal_multiplier);
- W: 1 win, 0.5 draw (a penalty shootout counts as a draw), 0 loss.
"""
from __future__ import annotations

import pandas as pd

from copadata import config


def k_factor(tournament: str) -> int:
    """Match weight: 60 World Cup, 50 continental finals, 40 qualifiers and Nations Leagues,
    20 friendlies, 30 anything else."""
    if tournament == "FIFA World Cup":
        return config.ELO_K_WORLD_CUP
    if tournament in config.ELO_CONTINENTAL:
        return config.ELO_K_CONTINENTAL
    if tournament in config.ELO_NATIONS_LEAGUES or (
        tournament.endswith(" qualification")
        and tournament.removesuffix(" qualification") in ("FIFA World Cup", *config.ELO_CONTINENTAL)
    ):
        return config.ELO_K_QUALIFIER
    if tournament == "Friendly":
        return config.ELO_K_FRIENDLY
    return config.ELO_K_OTHER


def goal_multiplier(margin: int) -> float:
    """1 for a draw or a one-goal win, 1.5 for two goals, (11 + N) / 8 for N >= 3."""
    margin = abs(margin)
    if margin <= 1:
        return 1.0
    if margin == 2:
        return 1.5
    return (11 + margin) / 8


def expected(dr: float) -> float:
    """Expected result (win 1, draw 0.5) for a rating difference dr in favor of the team."""
    return 1 / (10 ** (-dr / 400) + 1)


def ratings(results: pd.DataFrame) -> pd.DataFrame:
    """Pre-match ratings for every match, in the given order (chronological).

    `results` needs home_team, away_team, home_score, away_score, tournament and neutral.
    Returns `results` plus elo_home and elo_away (before the match) and expected_home (the home
    team's expected result, home advantage included).
    """
    current: dict[str, float] = {}
    before_home, before_away, exp_home = [], [], []
    for r in results[["home_team", "away_team", "home_score", "away_score", "tournament", "neutral"]].itertuples(index=False):
        rh = current.get(r.home_team, config.ELO_START)
        ra = current.get(r.away_team, config.ELO_START)
        we = expected(rh - ra + (0 if r.neutral else config.ELO_HOME))
        w = 1.0 if r.home_score > r.away_score else (0.5 if r.home_score == r.away_score else 0.0)
        change = k_factor(r.tournament) * goal_multiplier(r.home_score - r.away_score) * (w - we)
        current[r.home_team] = rh + change
        current[r.away_team] = ra - change
        before_home.append(rh)
        before_away.append(ra)
        exp_home.append(we)
    return results.assign(elo_home=before_home, elo_away=before_away, expected_home=exp_home)
