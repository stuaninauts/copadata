"""Tests for copadata/aggregate.py.

Unit tests build tiny tables by hand. The golden tests reproduce the published findings on the real
processed data and are skipped when data/processed/ has not been generated
(`python -m copadata.pipeline`).
"""
from __future__ import annotations

import pandas as pd
import pytest

from copadata import aggregate, config


def matches(**cols) -> pd.DataFrame:
    n = len(next(iter(cols.values())))
    return pd.DataFrame({"finished": [True] * n, **cols})


def value(table: pd.DataFrame, **keys) -> pd.Series:
    mask = pd.Series(True, index=table.index)
    for col, v in keys.items():
        mask &= table[col] == v
    (row,) = table[mask].itertuples(index=False)
    return pd.Series(row._asdict())


# --- unit ---------------------------------------------------------------------------

@pytest.mark.parametrize("year, label", [(1986, "24-teams"), (1994, "24-teams"), (1998, "32-teams"),
                                         (2022, "32-teams"), (2026, "48-teams")])
def test_era(year, label):
    assert aggregate.era(year) == label


def test_era_outside_the_covered_editions():
    with pytest.raises(ValueError, match="1982"):
        aggregate.era(1982)


def test_rate_carries_k_and_n_and_skips_unfinished():
    m = matches(stage=["groups"] * 4, decided_final_quarter=[True, False, True, False])
    m.loc[3, "finished"] = False
    r = value(aggregate.summarize(m, ["stage"], ["decided_final_quarter"]), stage="groups")
    assert (r.k, r.n) == (2, 3) and r.value == pytest.approx(2 / 3)


def test_mean_has_no_k_and_ignores_missing():
    m = matches(stage=["knockout"] * 3, winning_goal_min=[30.0, None, 90.0])
    r = value(aggregate.summarize(m, ["stage"], ["winning_goal_min"]), stage="knockout")
    assert pd.isna(r.k) and r.n == 2 and r.value == 60


def test_one_goal_margin_counts_only_decided_matches():
    m = matches(stage=["groups"] * 4, margin=[0, 1, 1, 3])
    r = value(aggregate.summarize(m, ["stage"], ["one_goal_margin"]), stage="groups")
    assert (r.k, r.n) == (2, 3)


def test_summarize_by_several_keys():
    m = matches(year=[1990, 1990, 2026], stage=["groups", "knockout", "groups"],
                had_comeback=[True, False, True])
    t = aggregate.summarize(m, ["year", "stage"], ["comeback"])
    assert t[["year", "stage", "k", "n"]].values.tolist() == [[1990, "groups", 1, 1], [1990, "knockout", 0, 1],
                                                                [2026, "groups", 1, 1]]


def test_add_matchday_takes_it_from_team_matches():
    m = pd.DataFrame({"match_id": [1, 2]})
    tm = pd.DataFrame({"match_id": [1, 1, 2, 2], "matchday": pd.array([2, 2, None, None], dtype="Int64")})
    assert aggregate.add_matchday(m, tm).matchday.tolist() == [2, pd.NA]


def test_margin_distribution_groups_big_margins():
    m = matches(stage=["knockout"] * 4, margin=[0, 1, 4, 7])
    t = aggregate.margin_distribution(m, ["stage"])
    assert t.margin.tolist() == [0, 1, 2, config.BIG_MARGIN] and t.k.tolist() == [1, 1, 0, 2]
    assert (t.n == 4).all()


def test_goal_bands_use_regulation_goals_only():
    g = pd.DataFrame({"stage": ["groups"] * 4, "minute": [1, 15, 90, 105], "extra_time": [False, False, False, True]})
    t = aggregate.goal_bands(g, ["stage"])
    assert t.band.tolist() == ["1-15", "16-30", "31-45", "46-60", "61-75", "76-90"]
    assert t.k.tolist() == [2, 0, 0, 0, 0, 1] and (t.n == 3).all()


def test_stoppage_goals_per_match_includes_editions_without_any():
    m = matches(year=[1986, 2026, 2026])
    g = pd.DataFrame({"year": [2026, 2026, 2026], "stoppage": [True, True, False]})
    t = aggregate.stoppage_goals_per_match(g, m, ["year"])
    assert t[["year", "k", "n"]].values.tolist() == [[1986, 0, 1], [2026, 2, 2]]


def test_edition_standing():
    by_year = pd.DataFrame({"year": [1990, 2010, 2026], "value": [0.4, 0.1, 0.3]})
    assert aggregate.edition_standing(by_year, 2026) == {
        "value": 0.3, "rank": 2, "of": 3, "others_min": 0.1, "others_max": 0.4}


def test_binomial_tests():
    assert aggregate.binomial_upper_tail(0, 5, 0.3) == pytest.approx(1)
    assert aggregate.binomial_upper_tail(2, 2, 0.5) == pytest.approx(0.25)
    # symmetric at p=0.5: 6 of 9 -> P(X>=6) + P(X<=3)
    assert aggregate.binomial_two_sided(6, 9) == pytest.approx(2 * 130 / 512)


# --- golden: the published findings ------------------------------------------------

needs_data = pytest.mark.skipif(not config.MATCHES_PARQUET.exists(), reason="run the pipeline first")


@pytest.fixture(scope="module")
def data():
    return {name: pd.read_parquet(path) for name, path in [
        ("matches", config.MATCHES_PARQUET), ("goals", config.GOALS_PARQUET),
        ("team_matches", config.TEAM_MATCHES_PARQUET)]}


@pytest.fixture(scope="module")
def core(data):
    m = data["matches"]
    return aggregate.add_era(m[m.stage.isin(["groups", "knockout"])])


def kn(row) -> tuple[int, int]:
    return int(row.k), int(row.n)


@needs_data
def test_golden_2026_groups_vs_knockout(core):
    t = aggregate.summarize(core[core.year == 2026], ["stage"])
    g, k = (lambda metric: value(t, stage="groups", metric=metric)), (lambda metric: value(t, stage="knockout", metric=metric))
    assert (round(g("winning_goal_min").value), g("winning_goal_min").n) == (44, 52)
    assert (round(k("winning_goal_min").value), k("winning_goal_min").n) == (71, 27)
    assert (round(k("winning_goal_min_90").value), k("winning_goal_min_90").n) == (62, 22)
    assert kn(g("one_goal_margin")) == (18, 52) and kn(k("one_goal_margin")) == (17, 27)
    assert round(g("goals_per_match").value, 2) == 2.99 and round(k("goals_per_match").value, 2) == 2.68
    assert round(k("goals_per_match_90").value, 2) == 2.42
    assert kn(g("late_goal")) == (36, 72) and kn(k("late_goal")) == (16, 31)
    assert kn(g("comeback")) == (10, 72) and kn(k("comeback")) == (7, 31)
    assert kn(g("decided_final_quarter")) == (14, 72) and kn(k("decided_final_quarter")) == (12, 31)
    assert kn(k("extra_time")) == (9, 31) and kn(k("penalties")) == (4, 31) and kn(k("survival_goal")) == (7, 31)


@needs_data
def test_golden_2026_margins_and_goal_minutes(core, data):
    md = aggregate.margin_distribution(core[(core.year == 2026) & (core.stage == "knockout")], ["stage"])
    assert md.k.tolist() == [4, 17, 6, 4]
    g = data["goals"]
    bands = aggregate.goal_bands(g[(g.year == 2026) & g.stage.isin(["groups", "knockout"])], ["stage"])
    late = bands[bands.band == "76-90"].set_index("stage")
    assert kn(late.loc["groups"]) == (55, 215) and kn(late.loc["knockout"]) == (23, 75)


@needs_data
def test_golden_2026_knockout_by_round(core):
    t = aggregate.summarize(core[(core.year == 2026) & (core.stage == "knockout")], ["round_raw"],
                            ["decided_final_quarter"]).set_index("round_raw")
    assert {r: kn(t.loc[r]) for r in t.index} == {
        "Round of 32": (7, 16), "Round of 16": (3, 8), "Quarter-final": (1, 4), "Semi-final": (1, 2), "Final": (0, 1)}


@needs_data
def test_golden_h1_knockout_final_quarter_against_history(core):
    ko = core[core.stage == "knockout"]
    by_year = aggregate.summarize(ko, ["year"], ["decided_final_quarter"])
    history = value(aggregate.summarize(ko[ko.year < 2026], ["stage"], ["decided_final_quarter"]), stage="knockout")
    assert kn(history) == (37, 150)
    s = aggregate.edition_standing(by_year, 2026)
    assert (s["rank"], s["of"], round(s["others_min"], 2), round(s["others_max"], 2)) == (3, 11, 0.13, 0.40)
    assert round(aggregate.binomial_upper_tail(12, 31, history.value), 2) == 0.06


@needs_data
def test_golden_h2_eras(core):
    t = aggregate.summarize(core, ["era", "stage"], ["decided_final_quarter", "winning_goal_min_90", "late_goal"])
    pct = lambda era, stage, metric: round(100 * value(t, era=era, stage=stage, metric=metric).value)
    minute = lambda era, stage: round(value(t, era=era, stage=stage, metric="winning_goal_min_90").value)
    assert [pct(e, s, "decided_final_quarter") for e in ("24-teams", "32-teams", "48-teams")
            for s in ("groups", "knockout")] == [10, 36, 17, 20, 19, 39]
    assert [minute(e, s) for e in ("24-teams", "32-teams", "48-teams")
            for s in ("groups", "knockout")] == [44, 53, 51, 48, 44, 62]
    assert [pct(e, s, "late_goal") for e in ("24-teams", "32-teams", "48-teams")
            for s in ("groups", "knockout")] == [31, 51, 42, 31, 50, 52]
    assert [value(t, era=e, stage=s, metric="late_goal").n for e in ("24-teams", "32-teams", "48-teams")
            for s in ("groups", "knockout")] == [108, 45, 336, 105, 72, 31]


@needs_data
def test_golden_h3_group_margins(core):
    t = aggregate.summarize(core[core.stage == "groups"], ["year"], ["big_margin", "one_goal_margin_90", "mean_margin"])
    big = t[t.metric == "big_margin"].set_index("year")
    assert kn(big.loc[2026]) == (18, 72) and round(big.loc[1998].value, 2) == 0.17
    assert round(big.drop(2026).value.min(), 2) == 0.10 and round(big.drop(2026).value.max(), 2) == 0.21
    one = t[t.metric == "one_goal_margin_90"].set_index("year").value
    assert round(one[2026], 2) == 0.35 and (round(one.drop(2026).min(), 2), round(one.drop(2026).max(), 2)) == (0.41, 0.62)
    mean = t[t.metric == "mean_margin"].set_index("year").value
    assert round(mean[2026], 2) == 1.65 and (round(mean.drop(2026).min(), 2), round(mean.drop(2026).max(), 2)) == (1.19, 1.48)
    by_era = aggregate.summarize(core[core.stage == "groups"], ["era"], ["goals_per_match_90"]).set_index("era").value
    assert [round(by_era[e], 2) for e in ("24-teams", "32-teams", "48-teams")] == [2.40, 2.54, 2.99]


@needs_data
def test_golden_h4_stoppage_time(data):
    m, g = data["matches"], data["goals"]
    per_match = aggregate.stoppage_goals_per_match(g, m, ["year"]).set_index("year").value
    assert [round(per_match[y], 2) for y in (2018, 2022, 2026)] == [0.30, 0.23, 0.33]
    assert round(per_match.loc[:2010].max(), 2) == 0.14
    at_90 = aggregate.summarize(m, ["year"], ["decisive_at_90"]).set_index("year").value
    assert round(at_90[2018], 2) == 0.18 and round(at_90[2026], 2) == 0.15 and round(at_90.loc[:2014].max(), 2) == 0.10


@needs_data
def test_golden_group_matchdays_and_zones(core, data):
    groups = aggregate.add_matchday(core[core.stage == "groups"], data["team_matches"])
    t = aggregate.summarize(groups, ["era", "matchday"], ["draw_90", "goals_per_match_90"])
    draws = lambda era: [round(100 * value(t, era=era, matchday=d, metric="draw_90").value) for d in (1, 2, 3)]
    assert draws("48-teams") == [38, 21, 25] and draws("32-teams") == [25, 27, 22]
    assert [round(value(t, era="48-teams", matchday=d, metric="goals_per_match_90").value, 2)
            for d in (1, 2, 3)] == [3.12, 2.75, 3.08]
    tm = data["team_matches"]
    z = aggregate.summarize_teams(tm[(tm.year == 2026) & (tm.stage == "groups") & (tm.matchday > 1)], ["zone_before"])
    assert round(value(z, zone_before="qualification", metric="win").value, 2) == 0.42
    assert round(value(z, zone_before="danger", metric="win").value, 2) == 0.35
    assert round(value(z, zone_before="qualification", metric="goals_for").value, 2) == 1.50
    assert round(value(z, zone_before="danger", metric="goals_for").value, 2) == 1.42
