"""Adapter: Fjelstul World Cup Database (CSV) -> OpenFootball-shaped editions.

Reshapes each historical edition into the same dict the OpenFootball JSON has (score with
ft/et/p, goals1/goals2 with string minutes such as "90+2"), so transform and metrics process
every edition with the same code. No metric is defined here (ADR 0003, ADR 0005).

Fjelstul conventions relied on:
- goals.team_name / goals.home_team are the team CREDITED with the goal (own goals included);
- goals.match_period starting with "extra time" marks extra-time goals;
- matches.home_team_score includes extra time and excludes the penalty shootout.
"""
from __future__ import annotations

import pandas as pd

from copadata import config

# Fjelstul stage_name -> OpenFootball round, as transform.classify_stage expects.
ROUND = {
    "round of 16": "Round of 16",
    "quarter-final": "Quarter-final",
    "quarter-finals": "Quarter-final",
    "semi-final": "Semi-final",
    "semi-finals": "Semi-final",
    "final": "Final",
    "third-place match": "Match for third place",
}
GROUP_STAGE = "group stage"


def _minute(regulation: int, stoppage: int) -> str:
    """(90, 3) -> '90+3'; (17, 0) -> '17'."""
    return f"{regulation}+{stoppage}" if stoppage else str(regulation)


def _goal(row) -> dict:
    return {
        "name": f"{row.given_name} {row.family_name}".replace("not applicable", "").strip(),
        "minute": _minute(int(row.minute_regulation), int(row.minute_stoppage)),
        "owngoal": bool(row.own_goal),
        "penalty": bool(row.penalty),
    }


def _match(m, goals: pd.DataFrame) -> dict:
    goals = goals.sort_values(["minute_regulation", "minute_stoppage"])
    goals1 = [_goal(g) for g in goals[goals.home_team == 1].itertuples()]
    goals2 = [_goal(g) for g in goals[goals.home_team == 0].itertuples()]
    if (len(goals1), len(goals2)) != (m.home_team_score, m.away_team_score):
        raise ValueError(
            f"{m.match_id}: {len(goals1)}-{len(goals2)} goals listed, score is "
            f"{m.home_team_score}-{m.away_team_score}"
        )

    regulation = ~goals.match_period.str.startswith("extra time")
    score = {"ft": [int((regulation & (goals.home_team == 1)).sum()),
                    int((regulation & (goals.home_team == 0)).sum())]}
    if m.extra_time:
        score["et"] = [int(m.home_team_score), int(m.away_team_score)]
    if m.penalty_shootout:
        score["p"] = [int(m.home_team_score_penalties), int(m.away_team_score_penalties)]

    is_group = m.stage_name == GROUP_STAGE
    if not is_group and m.stage_name not in ROUND:
        raise ValueError(f"{m.match_id}: unknown stage {m.stage_name!r}")
    return {
        "round": "Group stage" if is_group else ROUND[m.stage_name],
        "num": int(m.match_id.rsplit("-", 1)[1]),  # "M-2018-03" -> 3
        "group": m.group_name if is_group else None,
        "date": m.match_date,
        "ground": m.stadium_name,
        "team1": m.home_team_name,
        "team2": m.away_team_name,
        "score": score,
        "goals1": goals1,
        "goals2": goals2,
    }


def to_editions(matches: pd.DataFrame, goals: pd.DataFrame,
                first_year: int = config.FIRST_HISTORICAL_YEAR) -> dict[int, dict]:
    """Men's World Cups from `first_year` on, as {year: {"matches": [...]}} in OpenFootball shape."""
    men = matches[matches.tournament_name.str.contains("Men's", regex=False)].copy()
    men["year"] = men.tournament_id.str[3:].astype(int)
    men = men[(men.year >= first_year) & (men.year < config.SEASON)]
    by_match = dict(tuple(goals.groupby("match_id")))
    empty = goals.iloc[0:0]

    editions = {}
    for year, ed in men.sort_values(["match_date", "match_id"]).groupby("year"):
        editions[int(year)] = {"matches": [_match(m, by_match.get(m.match_id, empty))
                                           for m in ed.itertuples()]}
    return editions
