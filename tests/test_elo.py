"""Tests for the Elo ratings in copadata/elo.py (ADR 0009)."""
from __future__ import annotations

import pandas as pd
import pytest

from copadata import config, elo


def results(*rows) -> pd.DataFrame:
    cols = ["home_team", "away_team", "home_score", "away_score", "tournament", "neutral"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


@pytest.mark.parametrize("tournament, k", [
    ("FIFA World Cup", 60),
    ("Copa América", 50),
    ("UEFA Euro qualification", 40),
    ("FIFA World Cup qualification", 40),
    ("UEFA Nations League", 40),
    ("CFU Caribbean Cup qualification", 30),  # qualifier of a minor tournament
    ("Merdeka Tournament", 30),
    ("Friendly", 20),
])
def test_k_factor(tournament, k):
    assert elo.k_factor(tournament) == k


@pytest.mark.parametrize("margin, g", [(0, 1), (1, 1), (-1, 1), (2, 1.5), (3, 1.75), (4, 1.875), (-6, 2.125)])
def test_goal_multiplier(margin, g):
    assert elo.goal_multiplier(margin) == pytest.approx(g)


def test_expected_is_symmetric_and_half_when_level():
    assert elo.expected(0) == pytest.approx(0.5)
    assert elo.expected(200) + elo.expected(-200) == pytest.approx(1)
    assert elo.expected(400) == pytest.approx(10 / 11)


def test_ratings_are_taken_before_each_match_and_move_by_the_formula():
    out = elo.ratings(results(
        ("A", "B", 2, 0, "FIFA World Cup", True),   # neutral: We = 0.5, change = 60 * 1.5 * 0.5 = 45
        ("A", "B", 1, 1, "Friendly", False),       # A at home: dr = 90 + 100
    ))
    assert (out.elo_home[0], out.elo_away[0]) == (config.ELO_START, config.ELO_START)
    assert (out.elo_home[1], out.elo_away[1]) == (config.ELO_START + 45, config.ELO_START - 45)
    assert out.expected_home[1] == pytest.approx(elo.expected(190))


def test_a_draw_moves_ratings_toward_each_other():
    out = elo.ratings(results(
        ("A", "B", 3, 0, "Friendly", True),
        ("A", "B", 0, 0, "Friendly", True),
        ("A", "B", 0, 0, "Friendly", True),
    ))
    gaps = (out.elo_home - out.elo_away).tolist()
    assert gaps[0] == 0 and gaps[1] > gaps[2] > 0
