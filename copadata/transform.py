"""transform.py — raw (OpenFootball JSON) -> data/processed/matches.parquet.

One row per match (Match grain). Computes stage, score, margin, flags, and the match-level
metrics — all defined in metrics.py.
"""
from __future__ import annotations

import pandas as pd

from copadata import config, ingest, metrics

_KNOCKOUT = {"Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"}
_THIRD_PLACE = {"Match for third place"}


def classify_stage(m: dict) -> str:
    if m.get("group"):
        return "groups"
    if m["round"] in _THIRD_PLACE:
        return "third_place"
    if m["round"] in _KNOCKOUT:
        return "knockout"
    return "other"


def build_matches(data: dict) -> pd.DataFrame:
    rows = []
    for i, m in enumerate(data["matches"]):
        score = m.get("score")
        finished = bool(score and "ft" in score)
        stage = classify_stage(m)
        row = {
            "match_id": i,
            "num": m.get("num"),
            "date": m.get("date"),
            "venue": m.get("ground"),
            "group": m.get("group"),
            "round_raw": m.get("round"),
            "stage": stage,
            "is_knockout": stage == "knockout",
            "team1": m["team1"],
            "team2": m["team2"],
            "finished": finished,
        }
        if finished:
            ft = score["ft"]
            et = score.get("et")
            pen = score.get("p")
            goals = metrics.match_goals(m)
            s1, s2 = metrics.final_score(goals)
            wg = metrics.winning_goal(goals)
            comebacks = metrics.comeback_events(goals)
            sg = metrics.survival_goal(goals, stage == "knockout", ft)
            wgr = metrics.winning_goal_regulation(goals, ft)
            dm = metrics.decisive_moment_regulation(goals, ft, stage == "knockout")
            row.update(
                {
                    "goals_team1": s1,
                    "goals_team2": s2,
                    "goals_ft1": ft[0],
                    "goals_ft2": ft[1],
                    "has_extra_time": et is not None,
                    "decided_on_penalties": pen is not None,
                    "pen1": pen[0] if pen else None,
                    "pen2": pen[1] if pen else None,
                    # margin at the end of regulation/extra time (penalties => draw => margin 0)
                    "margin": abs(s1 - s2),
                    # level at the end of REGULATION: in the knockout this forces extra time/penalties
                    "draw_in_regulation": ft[0] == ft[1],
                    "total_goals": len(goals),
                    "winning_goal_min": wg.minute if wg else None,
                    "winning_goal_in_et": wg.extra_time if wg else None,
                    "late_goals_count": sum(metrics.is_late_goal(g) for g in goals),
                    "has_late_goal": any(metrics.is_late_goal(g) for g in goals),
                    "et_goals_count": sum(g.extra_time for g in goals),
                    "had_comeback": len(comebacks) > 0,
                    "last_comeback_min": comebacks[-1].minute if comebacks else None,
                    "lead_changes": metrics.lead_changes(goals),
                    "has_survival_goal": sg is not None,
                    "survival_goal_min": sg.minute if sg else None,
                    # regulation-only lens (fair comparison)
                    "goals_regulation": ft[0] + ft[1],
                    "margin_ft": abs(ft[0] - ft[1]),
                    "winning_goal_min_90": wgr.minute if wgr else None,
                    "decisive_moment_90": dm.minute if dm else None,
                    "decided_final_quarter": (dm.minute >= metrics.FINAL_QUARTER_MIN) if dm else False,
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def build_goals(data: dict) -> pd.DataFrame:
    """Goal grain: one row per goal (regulation + extra time; no shootout). Feeds the
    goal-minute distributions. Uses metrics.match_goals — no new definitions here.
    """
    rows = []
    for i, m in enumerate(data["matches"]):
        score = m.get("score")
        if not (score and "ft" in score):
            continue
        stage = classify_stage(m)
        for g in metrics.match_goals(m):
            rows.append(
                {
                    "match_id": i,
                    "stage": stage,
                    "is_knockout": stage == "knockout",
                    "team": m[f"team{g.side}"],
                    "side": g.side,
                    "minute": g.minute,
                    "order": g.order,
                    "extra_time": g.extra_time,
                    "late": metrics.is_late_goal(g),
                    "own_goal": g.own_goal,
                    "penalty": g.penalty,
                }
            )
    return pd.DataFrame(rows)


def main() -> pd.DataFrame:
    data = ingest.load()
    df = build_matches(data)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.MATCHES_PARQUET, index=False)
    goals = build_goals(data)
    goals.to_parquet(config.GOALS_PARQUET, index=False)
    print(
        f"[transform] {len(df)} matches ({int(df['finished'].sum())} finished), "
        f"{len(goals)} goals -> {config.PROCESSED}"
    )
    return df


if __name__ == "__main__":
    main()
