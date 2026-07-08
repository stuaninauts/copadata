"""derive.py — matches -> data/processed/team_matches.parquet.

Two rows per match (Team-match grain): each team's perspective. This is where the group
situation lives — an in-group proxy: matchday, opener, points/GD/position BEFORE the match,
and games left. (The exact qualification math, which depends on other groups, is out of scope.)
"""
from __future__ import annotations

import pandas as pd

from copadata import config


def _result(gf: int, ga: int) -> str:
    """W/D/L over regulation + extra time (penalties => draw)."""
    return "W" if gf > ga else ("L" if gf < ga else "D")


def _points(res: str) -> int:
    return 3 if res == "W" else (1 if res == "D" else 0)


def explode(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in matches.iterrows():
        for side in (1, 2):
            other = 2 if side == 1 else 1
            gf, ga = p.get(f"goals_team{side}"), p.get(f"goals_team{other}")
            rows.append(
                {
                    "match_id": p["match_id"],
                    "stage": p["stage"],
                    "is_knockout": p["is_knockout"],
                    "group": p["group"],
                    "date": p["date"],
                    "round_raw": p["round_raw"],
                    "finished": p["finished"],
                    "team": p[f"team{side}"],
                    "opponent": p[f"team{other}"],
                    "home": side == 1,
                    "goals_for": gf,
                    "goals_against": ga,
                    "result": _result(gf, ga) if p["finished"] else None,
                }
            )
    return pd.DataFrame(rows)


def group_situation(tm: pd.DataFrame) -> pd.DataFrame:
    """Fill the group situation (proxy) on finished group-stage rows."""
    tm = tm.copy()
    cols = ["matchday", "is_opener", "points_before", "gd_before", "position_before", "games_left"]
    vals: dict[str, dict] = {c: {} for c in cols}
    groups = tm[(tm["stage"] == "groups") & (tm["finished"])]

    for _, gdf in groups.groupby("group"):
        teams = gdf["team"].unique()
        # matchday + the team's own accumulated tally (matches with an earlier date)
        for _, tdf in gdf.groupby("team"):
            tdf = tdf.sort_values("date")
            for matchday, (idx, row) in enumerate(tdf.iterrows(), start=1):
                prev = tdf[tdf["date"] < row["date"]]
                vals["matchday"][idx] = matchday
                vals["is_opener"][idx] = matchday == 1
                vals["games_left"][idx] = 3 - matchday
                vals["points_before"][idx] = int(sum(_points(r["result"]) for _, r in prev.iterrows()))
                vals["gd_before"][idx] = (
                    int((prev["goals_for"] - prev["goals_against"]).sum()) if len(prev) else 0
                )
        # group position BEFORE the match (table from matches with an earlier date)
        for idx, row in gdf.iterrows():
            prev = gdf[gdf["date"] < row["date"]]
            table = {t: [0, 0, 0] for t in teams}  # points, goal difference, goals for
            for _, r in prev.iterrows():
                e = table[r["team"]]
                e[0] += _points(r["result"])
                e[1] += r["goals_for"] - r["goals_against"]
                e[2] += r["goals_for"]
            ranking = sorted(table.items(), key=lambda kv: (-kv[1][0], -kv[1][1], -kv[1][2], kv[0]))
            pos = {t: i + 1 for i, (t, _) in enumerate(ranking)}
            vals["position_before"][idx] = pos[row["team"]]

    for c, dic in vals.items():
        s = pd.Series(dic).reindex(tm.index)
        tm[c] = s.astype("boolean") if c == "is_opener" else s.astype("Int64")
    return tm


def main() -> pd.DataFrame:
    matches = pd.read_parquet(config.MATCHES_PARQUET)
    tm = group_situation(explode(matches))
    tm.to_parquet(config.TEAM_MATCHES_PARQUET, index=False)
    print(f"[derive] {len(tm)} team-match rows -> {config.TEAM_MATCHES_PARQUET}")
    return tm


if __name__ == "__main__":
    main()
