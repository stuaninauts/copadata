"""Tests for the international results adapter (copadata/international.py, ADR 0009)."""
from __future__ import annotations

import pandas as pd
import pytest

from copadata import config, international

RESULT_COLUMNS = ["date", "home_team", "away_team", "home_score", "away_score", "tournament", "city", "country", "neutral"]


def raw(results, shootouts=(), goals=()):
    return {
        "results": pd.DataFrame(results, columns=RESULT_COLUMNS),
        "shootouts": pd.DataFrame(list(shootouts), columns=["date", "home_team", "away_team", "winner", "first_shooter"]),
        "goalscorers": pd.DataFrame(list(goals), columns=["date", "home_team", "away_team", "team", "scorer", "minute",
                                                          "own_goal", "penalty", "assist"]),
    }


def test_build_adds_elo_weight_and_shootout():
    results, goals = international.build(raw(
        [("2020-01-01", "Germany", "Brazil", 1, 0, "Friendly", "x", "y", True),
         ("2022-12-01", "Germany", "Brazil", 1, 1, "FIFA World Cup", "x", "y", True)],
        shootouts=[("2022-12-01", "Germany", "Brazil", "Brazil", "Germany")],
        goals=[("2020-01-01", "Germany", "Brazil", "Germany", "A", 90.0, False, True, None)],
    ))
    assert results.k.tolist() == [20, 60]
    assert results.elo_home[0] == config.ELO_START and results.elo_home[1] > results.elo_away[1]
    assert results.shootout_winner.tolist()[1] == "Brazil" and pd.isna(results.shootout_winner[0])
    assert (goals.minute[0], goals.penalty[0]) == (90, True)


def wc_results(*rows):
    return pd.DataFrame([{"date": d, "home_team": h, "away_team": a, "tournament": "FIFA World Cup",
                          "elo_home": eh, "elo_away": ea} for d, h, a, eh, ea in rows])


def test_add_elo_matches_either_order_and_maps_historical_names():
    results = wc_results(("1990-06-10", "Germany", "Yugoslavia", 1900, 1700),
                         ("1998-06-14", "Serbia", "Iran", 1800, 1600))
    matches = pd.DataFrame({"year": [1990, 1998], "date": ["1990-06-10", "1998-06-14"],
                            "team1": ["Yugoslavia", "Iran"], "team2": ["West Germany", "Yugoslavia"]})
    out = international.add_elo(matches, results)
    assert out.elo1.tolist() == [1700, 1600] and out.elo2.tolist() == [1900, 1800]


def test_add_elo_stops_when_a_match_is_missing():
    matches = pd.DataFrame({"year": [2026], "date": ["2026-06-11"], "team1": ["Mexico"], "team2": ["South Africa"]})
    with pytest.raises(ValueError, match="Mexico x South Africa"):
        international.add_elo(matches, wc_results(("2026-06-12", "Mexico", "South Africa", 1, 2)))
