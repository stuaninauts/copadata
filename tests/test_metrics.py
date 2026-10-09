"""Tests for the metric definitions in copadata/metrics.py.

Matches are built in the OpenFootball shape (goals1/goals2 with string minutes, score with
ft/et/p) so every test goes through the same parsing path as the real pipeline.
"""
from __future__ import annotations

import pandas as pd
import pytest

from copadata import metrics, transform


def g(minute: str, **flags) -> dict:
    return {"name": "x", "minute": minute, **flags}


def match(goals1=(), goals2=(), ft=None, et=None, p=None, round_="Round of 16", group=None) -> dict:
    goals1, goals2 = list(goals1), list(goals2)
    if ft is None:
        reg = lambda gs: sum(1 for x in gs if not metrics.parse_minute(x["minute"])[2])
        ft = [reg(goals1), reg(goals2)]
    score = {"ft": ft}
    if et is not None:
        score["et"] = et
    if p is not None:
        score["p"] = p
    return {"round": round_, "group": group, "date": "2026-07-01", "team1": "A", "team2": "B",
            "score": score, "goals1": goals1, "goals2": goals2}


def goals_of(m: dict) -> list[metrics.Goal]:
    return metrics.match_goals(m)


# --- minute parsing ----------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("17", (17, 17.0, False)),
        ("45+2", (45, 45.02, False)),
        ("90+3", (90, 90.03, False)),
        ("90", (90, 90.0, False)),
        ("91", (91, 91.0, True)),
        ("105+1", (105, 105.01, True)),
        ("120+5", (120, 120.05, True)),
        ("90+", (90, 90.0, False)),
        (" 33 ", (33, 33.0, False)),
    ],
)
def test_parse_minute(raw, expected):
    base, order, et = metrics.parse_minute(raw)
    assert (base, et) == (expected[0], expected[2])
    assert order == pytest.approx(expected[1])


def test_match_goals_sorted_with_stoppage_time_and_flags():
    m = match(goals1=[g("46"), g("45+2", penalty=True)], goals2=[g("45+1", owngoal=True)])
    goals = goals_of(m)
    assert [(x.side, x.minute) for x in goals] == [(2, 45), (1, 45), (1, 46)]
    assert goals[0].own_goal and goals[1].penalty
    assert not goals[2].own_goal and not goals[2].penalty


def test_match_goals_ignore_missing_arrays():
    m = match()
    m["goals1"] = None
    del m["goals2"]
    assert goals_of(m) == []


def test_shootout_is_not_a_goal():
    m = match(goals1=[g("30")], goals2=[g("70")], et=[1, 1], p=[4, 3])
    assert metrics.final_score(goals_of(m)) == (1, 1)


# --- late goal ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "minute, late",
    [("79", False), ("80", True), ("89", True), ("90", True), ("90+7", True), ("91", False), ("118", False)],
)
def test_is_late_goal(minute, late):
    (goal,) = goals_of(match(goals1=[g(minute)]))
    assert metrics.is_late_goal(goal) is late


# --- winning goal ------------------------------------------------------------------

def test_winning_goal_is_winners_goal_number_loser_plus_one():
    # 3-1: the winner's 2nd goal (55') is the one they never gave back
    m = match(goals1=[g("10"), g("55"), g("80")], goals2=[g("30")])
    wg = metrics.winning_goal(goals_of(m))
    assert (wg.side, wg.minute) == (1, 55)


def test_winning_goal_after_comeback():
    # team2 goes 0-2 down, comes back to win 3-2 at 85'
    m = match(goals1=[g("10"), g("20")], goals2=[g("50"), g("70"), g("85")])
    wg = metrics.winning_goal(goals_of(m))
    assert (wg.side, wg.minute) == (2, 85)


def test_winning_goal_none_on_draw_and_on_shootout():
    assert metrics.winning_goal(goals_of(match(goals1=[g("10")], goals2=[g("20")]))) is None
    assert metrics.winning_goal([]) is None
    shootout = match(goals1=[g("10")], goals2=[g("20")], et=[1, 1], p=[5, 4])
    assert metrics.winning_goal(goals_of(shootout)) is None


def test_winning_goal_in_extra_time():
    m = match(goals1=[g("30"), g("106")], goals2=[g("60")], et=[2, 1])
    wg = metrics.winning_goal(goals_of(m))
    assert (wg.minute, wg.extra_time) == (106, True)


# --- comeback and lead changes -----------------------------------------------------

def test_comeback_is_the_goal_that_takes_the_lead_after_trailing():
    # 1-0, 1-1, 1-2, 2-2, 3-2
    m = match(goals1=[g("10"), g("50"), g("85")], goals2=[g("20"), g("30")])
    events = metrics.comeback_events(goals_of(m))
    # B trailed 0-1 then led 1-2 at 30' -> comeback; A trailed 1-2 then led 3-2 at 85' -> comeback
    assert [(e.side, e.minute) for e in events] == [(2, 30), (1, 85)]


def test_no_comeback_when_leader_never_trailed():
    m = match(goals1=[g("10"), g("60")], goals2=[g("30")])
    assert metrics.comeback_events(goals_of(m)) == []


def test_equalizer_alone_is_not_a_comeback():
    m = match(goals1=[g("10")], goals2=[g("88")])
    assert metrics.comeback_events(goals_of(m)) == []


def test_lead_changes_count_leaving_a_tie():
    # A leads (1), level, B leads (2), level, A leads (3)
    m = match(goals1=[g("10"), g("50"), g("85")], goals2=[g("20"), g("30")])
    assert metrics.lead_changes(goals_of(m)) == 3
    # same side extending or restoring its lead is not a change
    assert metrics.lead_changes(goals_of(match(goals1=[g("10"), g("20")], goals2=[g("30")]))) == 1
    assert metrics.lead_changes([]) == 0


# --- survival goal (knockout only) -------------------------------------------------

def test_survival_goal_is_last_regulation_equalizer_from_behind():
    m = match(goals1=[g("10"), g("90+4")], goals2=[g("20"), g("30")], et=[2, 2], p=[3, 4])
    sg = metrics.survival_goal(goals_of(m), True, m["score"]["ft"])
    assert (sg.side, sg.minute) == (1, 90)


def test_survival_goal_ignores_extra_time_goals():
    # level 1-1 at 90' via a 60' equalizer; ET goals don't replace it
    m = match(goals1=[g("10"), g("110")], goals2=[g("60"), g("115")], et=[2, 2], p=[5, 4])
    sg = metrics.survival_goal(goals_of(m), True, m["score"]["ft"])
    assert sg.minute == 60


@pytest.mark.parametrize(
    "m, is_knockout",
    [
        (match(goals1=[g("10")], goals2=[g("88")], round_="Matchday 1", group="Group A"), False),  # group stage
        (match(et=[0, 0], p=[4, 2]), True),  # 0-0: nobody came from behind
        (match(goals1=[g("10"), g("60")], goals2=[g("88")]), True),  # not level at 90'
    ],
)
def test_survival_goal_none(m, is_knockout):
    assert metrics.survival_goal(goals_of(m), is_knockout, m["score"]["ft"]) is None


# --- regulation-only lens ----------------------------------------------------------

def test_winning_goal_regulation_ignores_extra_time():
    m = match(goals1=[g("30"), g("106")], goals2=[g("60")], et=[2, 1])
    assert metrics.winning_goal_regulation(goals_of(m), m["score"]["ft"]) is None
    m = match(goals1=[g("30"), g("77")], goals2=[g("60")])
    assert metrics.winning_goal_regulation(goals_of(m), m["score"]["ft"]).minute == 77


def test_decisive_moment_regulation():
    decided = match(goals1=[g("12"), g("81")], goals2=[g("40")])
    assert metrics.decisive_moment_regulation(goals_of(decided), decided["score"]["ft"], True).minute == 81

    ko_level = match(goals1=[g("10")], goals2=[g("90+2")], et=[1, 1], p=[2, 4])
    assert metrics.decisive_moment_regulation(goals_of(ko_level), ko_level["score"]["ft"], True).minute == 90

    group_draw = match(goals1=[g("10")], goals2=[g("50")], round_="Matchday 2", group="Group B")
    assert metrics.decisive_moment_regulation(goals_of(group_draw), group_draw["score"]["ft"], False) is None


# --- integration: one row per match in transform.build_matches ---------------------

def _rows(*ms):
    df = transform.build_matches({"matches": list(ms)})
    return df  # positional index: row i is the i-th match given


def test_build_matches_stage_classification():
    df = _rows(
        match(round_="Matchday 1", group="Group A"),
        match(round_="Round of 32"),
        match(round_="Match for third place"),
        match(round_="Final"),
    )
    assert df["stage"].tolist() == ["groups", "knockout", "third_place", "knockout"]
    assert df["is_knockout"].tolist() == [False, True, False, True]


def test_build_matches_shootout_row():
    df = _rows(match(goals1=[g("10")], goals2=[g("90+2")], et=[1, 1], p=[3, 4]))
    r = df.iloc[0]
    assert r.decided_on_penalties and r.has_extra_time and r.draw_in_regulation
    assert (r.margin, r.pen1, r.pen2) == (0, 3, 4)
    assert pd.isna(r.winning_goal_min)
    assert r.has_survival_goal and r.survival_goal_min == 90
    assert r.decisive_moment_90 == 90 and r.decided_final_quarter


def test_build_matches_final_quarter_boundary():
    df = _rows(
        match(goals1=[g("75")], round_="Matchday 1", group="Group A"),
        match(goals1=[g("76")], round_="Matchday 1", group="Group A"),
        match(round_="Matchday 1", group="Group A"),  # 0-0
    )
    assert df["decided_final_quarter"].tolist() == [False, True, False]


def test_build_matches_unfinished_match_has_no_metrics():
    m = match(round_="Final")
    del m["score"]
    r = _rows(m).iloc[0]
    assert not r.finished
    assert "winning_goal_min" not in r or pd.isna(r.winning_goal_min)



def test_build_matches_ids_are_unique_across_editions():
    a = transform.build_matches({"matches": [match(), match()]}, year=1990)
    b = transform.build_matches({"matches": [match()]}, year=2026)
    assert a["match_id"].tolist() == [1990000, 1990001] and a["year"].eq(1990).all()
    assert b["match_id"].tolist() == [2026000]
