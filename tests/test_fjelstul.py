"""Tests for the Fjelstul adapter (copadata/fjelstul.py) and the multi-edition pipeline steps."""
from __future__ import annotations

import pandas as pd
import pytest

from copadata import derive, fjelstul, metrics, transform

MEN = "{year} FIFA Men's World Cup"


def fj_match(match_id, year, home, away, hs, as_, stage="group stage", group="Group A",
             date="2018-06-14", extra_time=0, shootout=0, ph=0, pa=0, tournament=MEN):
    return {
        "match_id": match_id, "tournament_id": f"WC-{year}", "tournament_name": tournament.format(year=year),
        "stage_name": stage, "group_name": group if stage == "group stage" else "not applicable",
        "match_date": date, "stadium_name": "X", "home_team_name": home, "away_team_name": away,
        "home_team_score": hs, "away_team_score": as_, "extra_time": extra_time,
        "penalty_shootout": shootout, "home_team_score_penalties": ph, "away_team_score_penalties": pa,
    }


def fj_goal(match_id, home_team, reg, stop=0, period="second half", own_goal=0, penalty=0):
    return {
        "match_id": match_id, "home_team": home_team, "given_name": "A", "family_name": "B",
        "minute_regulation": reg, "minute_stoppage": stop, "match_period": period,
        "own_goal": own_goal, "penalty": penalty,
    }


def editions(matches, goals=(), **kw):
    goal_columns = list(fj_goal("x", 1, 1))
    return fjelstul.to_editions(pd.DataFrame(matches), pd.DataFrame(list(goals), columns=goal_columns), **kw)


def test_group_match_shape_and_minutes():
    eds = editions(
        [fj_match("M-2018-01", 2018, "Russia", "Saudi Arabia", 2, 1)],
        [fj_goal("M-2018-01", 1, 90, 4, "second half, stoppage time"),
         fj_goal("M-2018-01", 1, 12, 0, "first half"),
         fj_goal("M-2018-01", 0, 45, 2, "first half, stoppage time", penalty=1)],
    )
    (m,) = eds[2018]["matches"]
    assert (m["round"], m["group"], m["team1"], m["team2"]) == ("Group stage", "Group A", "Russia", "Saudi Arabia")
    assert m["score"] == {"ft": [2, 1]} and m["num"] == 1
    assert [g["minute"] for g in m["goals1"]] == ["12", "90+4"]
    assert m["goals2"][0]["minute"] == "45+2" and m["goals2"][0]["penalty"]
    assert transform.classify_stage(m) == "groups"


def test_extra_time_and_shootout():
    eds = editions(
        [fj_match("M-2014-50", 2014, "Brazil", "Chile", 1, 1, stage="round of 16", extra_time=1,
                  shootout=1, ph=3, pa=2)],
        [fj_goal("M-2014-50", 1, 18, period="first half"), fj_goal("M-2014-50", 0, 32, period="first half")],
    )
    (m,) = eds[2014]["matches"]
    assert m["score"] == {"ft": [1, 1], "et": [1, 1], "p": [3, 2]}
    assert m["round"] == "Round of 16" and m["group"] is None
    assert metrics.final_score(metrics.match_goals(m)) == (1, 1)


def test_extra_time_goals_count_only_in_et_score():
    eds = editions(
        [fj_match("M-2010-64", 2010, "Netherlands", "Spain", 0, 1, stage="final", extra_time=1)],
        [fj_goal("M-2010-64", 0, 116, period="extra time, second half")],
    )
    (m,) = eds[2010]["matches"]
    assert m["score"] == {"ft": [0, 0], "et": [0, 1]}
    (goal,) = metrics.match_goals(m)
    assert goal.extra_time and goal.minute == 116


def test_extra_time_stoppage_minute():
    eds = editions(
        [fj_match("M-2022-64", 2022, "Argentina", "France", 1, 0, stage="final", extra_time=1)],
        [fj_goal("M-2022-64", 1, 105, 1, "extra time, first half, stoppage time")],
    )
    (goal,) = metrics.match_goals(eds[2022]["matches"][0])
    assert (goal.minute, goal.extra_time) == (105, True)


def test_own_goal_is_credited_to_the_benefiting_side():
    # Fjelstul: home_team flags the team CREDITED with the goal
    eds = editions(
        [fj_match("M-2018-03", 2018, "Morocco", "Iran", 0, 1)],
        [fj_goal("M-2018-03", 0, 90, 5, "second half, stoppage time", own_goal=1)],
    )
    (m,) = eds[2018]["matches"]
    assert m["goals1"] == [] and m["goals2"][0]["owngoal"]


@pytest.mark.parametrize(
    "stage, round_",
    [("quarter-final", "Quarter-final"), ("quarter-finals", "Quarter-final"),
     ("semi-finals", "Semi-final"), ("third-place match", "Match for third place"), ("final", "Final")],
)
def test_stage_names_map_to_openfootball_rounds(stage, round_):
    eds = editions([fj_match("M-1", 1998, "A", "B", 0, 0, stage=stage)])
    assert eds[1998]["matches"][0]["round"] == round_


def test_goals_that_dont_match_the_score_are_rejected():
    with pytest.raises(ValueError, match="M-1"):
        editions([fj_match("M-1", 2002, "A", "B", 2, 0)], [fj_goal("M-1", 1, 10)])


def test_unknown_stage_is_rejected():
    with pytest.raises(ValueError, match="second group stage"):
        editions([fj_match("M-1", 1986, "A", "B", 0, 0, stage="second group stage")])


def test_filters_mens_editions_from_first_year_and_before_2026():
    ms = [
        fj_match("M-1982", 1982, "A", "B", 0, 0),
        fj_match("M-1986", 1986, "A", "B", 0, 0),
        fj_match("W-2019", 2019, "A", "B", 0, 0, tournament="{year} FIFA Women's World Cup"),
        fj_match("M-2026", 2026, "A", "B", 0, 0),
    ]
    assert list(editions(ms, first_year=1986)) == [1986]


def test_matches_are_ordered_by_date():
    ms = [fj_match("M-2", 1990, "C", "D", 0, 0, date="1990-06-09"),
          fj_match("M-1", 1990, "A", "B", 0, 0, date="1990-06-08")]
    teams = [m["team1"] for m in editions(ms)[1990]["matches"]]
    assert teams == ["A", "C"]


# --- derive: group situation is per (year, group) ----------------------------------

def test_group_situation_does_not_mix_editions():
    def group_match(t1, t2, s1, s2, date):
        return {"round": "Group stage", "group": "Group A", "date": date, "team1": t1, "team2": t2,
                "score": {"ft": [s1, s2]}, "goals1": [{"minute": "10"}] * s1, "goals2": [{"minute": "20"}] * s2}

    # same group name in two editions; the 1994 team only plays 1994 matches
    e1990 = {"matches": [group_match("A", "B", 1, 0, "1990-06-08"), group_match("A", "C", 2, 0, "1990-06-12")]}
    e1994 = {"matches": [group_match("X", "A", 3, 0, "1994-06-08"), group_match("X", "Y", 0, 0, "1994-06-12")]}
    m = pd.concat([transform.build_matches(e1990, 1990), transform.build_matches(e1994, 1994)], ignore_index=True)
    tm = derive.group_situation(derive.explode(m))

    a_1990 = tm[(tm.year == 1990) & (tm.team == "A")].sort_values("date")
    assert a_1990.matchday.tolist() == [1, 2] and a_1990.points_before.tolist() == [0, 2]  # 2 pts per win in 1990
    a_1994 = tm[(tm.year == 1994) & (tm.team == "A")]
    assert a_1994.matchday.tolist() == [1] and a_1994.points_before.tolist() == [0]
    # before 1994's 2nd match, X (3 pts) leads; A's 4 pts from 1990 must not leak into 1994
    x_1994 = tm[(tm.year == 1994) & (tm.team == "X")].sort_values("date")
    assert x_1994.points_before.tolist() == [0, 3] and x_1994.position_before.iloc[1] == 1


def test_points_for_a_win_were_two_before_1994():
    # A: win + heavy loss; B: two draws. 2 pts each until 1990 (B ahead on goal difference),
    # 3 x 2 from 1994 on (A ahead). D leads in both.
    def gm(t1, t2, s1, s2, day, year):
        return {"round": "Group stage", "group": "Group A", "date": f"{year}-06-{day:02d}", "team1": t1, "team2": t2,
                "score": {"ft": [s1, s2]}, "goals1": [{"minute": "10"}] * s1, "goals2": [{"minute": "20"}] * s2}

    def table_before_md3(year):
        ms = [gm("A", "C", 1, 0, 1, year), gm("B", "D", 0, 0, 1, year),
              gm("A", "D", 0, 3, 5, year), gm("B", "C", 1, 1, 5, year),
              gm("A", "B", 0, 0, 9, year), gm("C", "D", 0, 0, 9, year)]
        tm = derive.group_situation(derive.explode(transform.build_matches({"matches": ms}, year)))
        md3 = tm[tm.matchday == 3].set_index("team")
        return md3.points_before.to_dict(), md3.position_before.to_dict()

    pts, pos = table_before_md3(1990)
    assert pts == {"A": 2, "B": 2, "C": 1, "D": 3}
    assert pos == {"D": 1, "B": 2, "A": 3, "C": 4}

    pts, pos = table_before_md3(1994)
    assert pts == {"A": 3, "B": 2, "C": 1, "D": 4}
    assert pos == {"D": 1, "A": 2, "B": 3, "C": 4}
