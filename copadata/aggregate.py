"""aggregate.py: processed tables -> the aggregates behind the published findings (ADR 0006).

Turns the per-match, per-goal and per-team columns (defined in metrics.py, transform and derive)
into rates and means over any grouping: edition, era, stage, round, matchday, zone. Every value
carries its base: `k` hits (rates only) out of `n`, so `n` is always visible (ADR 0002).
Notebooks and the export import these functions; nothing here defines a match-level metric.

Output is long: one row per (group keys..., metric) with columns `k`, `n`, `value`.
"""
from __future__ import annotations

from math import comb

import pandas as pd

from copadata import config


def era(year: int) -> str:
    """Format era (number of teams) of an edition: 1990 -> '24-teams'."""
    for label, first, last in config.FORMAT_ERAS:
        if first <= year <= last:
            return label
    raise ValueError(f"no format era for {year}")


def add_era(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(era=df["year"].map(era))


def add_matchday(matches: pd.DataFrame, team_matches: pd.DataFrame) -> pd.DataFrame:
    """Group-stage matches get the matchday (1-3) from the team-match grain."""
    md = team_matches.dropna(subset=["matchday"]).groupby("match_id")["matchday"].max()
    return matches.assign(matchday=matches["match_id"].map(md).astype("Int64"))


# --- registries: metric name -> (k, n, value) over a slice -------------------------

def _rate(hit: pd.Series) -> tuple[int, int, float]:
    k, n = int(hit.sum()), len(hit)
    return k, n, (k / n if n else float("nan"))


def _mean(values: pd.Series) -> tuple[None, int, float]:
    v = values.dropna()
    return None, len(v), (float(v.mean()) if len(v) else float("nan"))


MATCH_METRICS = {
    "goals_per_match": lambda d: _mean(d["total_goals"]),
    "goals_per_match_90": lambda d: _mean(d["goals_regulation"]),
    # share of decided matches won by one goal (full match / regulation only)
    "one_goal_margin": lambda d: _rate(d.loc[d["margin"] > 0, "margin"] == 1),
    "one_goal_margin_90": lambda d: _rate(d.loc[d["margin_ft"] > 0, "margin_ft"] == 1),
    "big_margin": lambda d: _rate(d["margin"] >= config.BIG_MARGIN),
    "mean_margin": lambda d: _mean(d["margin"]),
    "draw_90": lambda d: _rate(d["draw_in_regulation"]),
    "extra_time": lambda d: _rate(d["has_extra_time"]),
    "penalties": lambda d: _rate(d["decided_on_penalties"]),
    "winning_goal_min": lambda d: _mean(d["winning_goal_min"]),
    "winning_goal_min_90": lambda d: _mean(d["winning_goal_min_90"]),
    "decided_final_quarter": lambda d: _rate(d["decided_final_quarter"]),
    # decisive moment (90') at minute 90 or in its stoppage time
    "decisive_at_90": lambda d: _rate(d["decisive_moment_90"].dropna() == 90),
    "late_goal": lambda d: _rate(d["has_late_goal"]),
    "comeback": lambda d: _rate(d["had_comeback"]),
    "survival_goal": lambda d: _rate(d["has_survival_goal"]),
}

TEAM_METRICS = {
    "goals_for": lambda d: _mean(d["goals_for"]),
    "win": lambda d: _rate(d["result"] == "W"),
}


def _summarize(df: pd.DataFrame, by: list[str], registry: dict, metrics) -> pd.DataFrame:
    rows = []
    for keys, part in df.groupby(by, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for name in metrics or registry:
            k, n, value = registry[name](part)
            rows.append({**dict(zip(by, keys)), "metric": name, "k": k, "n": n, "value": value})
    out = pd.DataFrame(rows, columns=[*by, "metric", "k", "n", "value"])
    return out.astype({"k": "Int64", "n": "int64", "value": "float64"})


def summarize(matches: pd.DataFrame, by: list[str], metrics: list[str] | None = None) -> pd.DataFrame:
    """Match-grain aggregates (finished matches only) per group of `by`."""
    return _summarize(matches[matches["finished"]], by, MATCH_METRICS, metrics)


def summarize_teams(team_matches: pd.DataFrame, by: list[str], metrics: list[str] | None = None) -> pd.DataFrame:
    """Team-match aggregates (finished rows only) per group of `by`."""
    return _summarize(team_matches[team_matches["finished"]], by, TEAM_METRICS, metrics)


def margin_distribution(matches: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Share of matches by final margin 0, 1, 2 and BIG_MARGIN+ (0 = level, incl. penalties)."""
    done = matches[matches["finished"]]
    margin = done["margin"].clip(upper=config.BIG_MARGIN)
    return _shares(done.assign(bucket=margin), by, "margin", range(config.BIG_MARGIN + 1))


def goal_bands(goals: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Share of regulation goals per minute band (1-15, ..., 76-90 incl. stoppage)."""
    reg = goals[~goals["extra_time"]]
    edges = [0, *config.GOAL_BANDS]
    labels = [f"{lo + 1}-{hi}" for lo, hi in zip(edges, edges[1:])]
    band = pd.cut(reg["minute"], bins=edges, labels=labels)
    return _shares(reg.assign(bucket=band.astype(str)), by, "band", labels)


def _shares(df: pd.DataFrame, by: list[str], name: str, buckets) -> pd.DataFrame:
    rows = []
    for keys, part in df.groupby(by, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        n = len(part)
        for b in buckets:
            k = int((part["bucket"] == b).sum())
            rows.append({**dict(zip(by, keys)), name: b, "k": k, "n": n, "value": k / n})
    return pd.DataFrame(rows, columns=[*by, name, "k", "n", "value"])


def stoppage_goals_per_match(goals: pd.DataFrame, matches: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Second-half stoppage-time goals (k) per finished match (n)."""
    done = matches[matches["finished"]]
    k = goals[goals["stoppage"]].groupby(by).size()
    n = done.groupby(by).size()
    out = pd.DataFrame({"k": k.reindex(n.index, fill_value=0), "n": n}).reset_index()
    return out.assign(value=out["k"] / out["n"])


# --- one edition against the others ------------------------------------------------

def edition_standing(by_year: pd.DataFrame, year: int) -> dict:
    """Where `year` sits among editions for one metric (rows of summarize(..., by=["year"])).

    Returns its value, rank (1 = highest) among all editions and the min/max of the others.
    """
    values = by_year.set_index("year")["value"]
    others = values.drop(year)
    return {
        "value": float(values[year]),
        "rank": int((values > values[year]).sum()) + 1,
        "of": len(values),
        "others_min": float(others.min()),
        "others_max": float(others.max()),
    }


# --- the single externally defined tests (ADR 0002) --------------------------------

def _pmf(i: int, n: int, p: float) -> float:
    return comb(n, i) * p**i * (1 - p) ** (n - i)


def binomial_upper_tail(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p): how often a rate at least this high shows up by chance."""
    return sum(_pmf(i, n, p) for i in range(k, n + 1))


def binomial_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """Two-sided exact test: total probability of outcomes no more likely than k."""
    observed = _pmf(k, n, p)
    return min(1.0, sum(_pmf(i, n, p) for i in range(n + 1) if _pmf(i, n, p) <= observed * (1 + 1e-9)))
