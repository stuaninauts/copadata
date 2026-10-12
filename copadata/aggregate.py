"""aggregate.py: processed tables -> the aggregates behind the published findings (ADR 0006).

Turns the per-match, per-goal and per-team columns (defined in metrics.py, transform and derive)
into rates and means over any grouping: edition, era, stage, round, matchday, zone. Every value
carries its base: `k` hits (rates only) out of `n`, so `n` is always visible (ADR 0002).
Notebooks and the export import these functions; nothing here defines a match-level metric.

Output is long: one row per (group keys..., metric) with columns `k`, `n`, `value`.
"""
from __future__ import annotations

import warnings
from math import comb

import numpy as np
import pandas as pd

from copadata import config, elo


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


# --- myths (ADR 0008) ---------------------------------------------------------------
# A closed list of outside claims. Each gets one effect (oriented so that > 0 supports the claim),
# one 95% interval and a verdict from a rule fixed before running. Intervals resample matches
# (bootstrap); bands redraw editions (permutation); both start from config.MYTH_SEED.
# Each myth returns (detail table, summary row).

Z95, Z998 = 1.96, 3.09  # two-sided normal limits for 95% and 99.8%


def verdict(low: float, high: float, halves_agree: bool, threshold: float = config.MYTH_THRESHOLD,
            low99: float | None = None) -> str:
    """The rule for an effect interval [low, high] (effect > 0 supports the claim):
    - "true": the interval is above zero and both halves of the history agree
      ("true_borderline" if the 99% interval reaches zero);
    - "myth": the whole interval is below the smallest effect the claim implies;
    - "undecided": anything else.
    """
    if low > 0 and halves_agree:
        return "true_borderline" if low99 is not None and low99 <= 0 else "true"
    if high < threshold:
        return "myth"
    return "undecided"


def _core(matches: pd.DataFrame) -> pd.DataFrame:
    done = matches[matches["finished"] & matches["stage"].isin(["groups", "knockout"])]
    return done.reset_index(drop=True)


def _rng() -> np.random.Generator:
    return np.random.default_rng(config.MYTH_SEED)


def _with_resamples(rng: np.random.Generator, n: int) -> np.ndarray:
    """Weights over n units: row 0 is the data itself, then one row per bootstrap resample."""
    if n == 0:
        return np.ones((config.MYTH_DRAWS + 1, 0))
    draws = rng.multinomial(n, np.full(n, 1 / n), size=config.MYTH_DRAWS).astype(float)
    return np.vstack([np.ones(n), draws])


def _interval(samples: np.ndarray, level: int = 95) -> tuple[float, float]:
    if np.isnan(samples).all():
        return float("nan"), float("nan")
    tail = (100 - level) / 2
    low, high = np.nanpercentile(samples, [tail, 100 - tail])
    return float(low), float(high)



def _halves(years: np.ndarray) -> list[np.ndarray]:
    return [(years >= first) & (years <= last) for first, last in config.MYTH_HALVES]


def _half_names() -> list[str]:
    return [f"{first}_{last}" for first, last in config.MYTH_HALVES]


def _summary(myth: str, measure: str, effect: float, low: float | None, high: float | None,
             threshold: float | None, halves_agree: bool | None, result: str) -> dict:
    r3 = lambda v: None if v is None else round(v, 3)
    return {"myth": myth, "measure": measure, "effect": effect, "ci_low": r3(low), "ci_high": r3(high),
            "threshold": threshold, "halves_agree": halves_agree, "verdict": result}


def score_grid(matches: pd.DataFrame, goals: pd.DataFrame) -> np.ndarray:
    """Regulation score at the END of each minute 1-90: shape (2, len(matches), 90), side 1 then
    side 2, rows in `matches` order. Stoppage goals count at their base minute (45 or 90)."""
    row = pd.Series(np.arange(len(matches)), index=matches["match_id"].to_numpy())
    reg = goals[~goals["extra_time"] & goals["match_id"].isin(row.index)]
    per_minute = np.zeros((2, len(matches), 90), dtype=int)
    np.add.at(per_minute, (reg["side"].to_numpy() - 1, row[reg["match_id"]].to_numpy(),
                           reg["minute"].clip(1, 90).to_numpy() - 1), 1)
    return per_minute.cumsum(axis=2)


def two_nil(matches: pd.DataFrame, goals: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Myth "2-0 is the most dangerous score".

    For the first 2-0 of each match, and for the 2-1 right after it: how often the leader did not
    win at 90', against teams leading exactly 1-0 at the end of the same minute (pooled in 15-minute
    bands). The verdict goes on the 2-1, the serious form of the claim.
    """
    core = _core(matches)
    end = score_grid(core, goals)
    ft = end[:, :, -1]
    weights = _with_resamples(_rng(), len(core))

    def not_won(i, side):
        return (ft[side, i] <= ft[1 - side, i]).astype(float)

    ref = [np.nonzero((end[s] == 1) & (end[1 - s] == 0)) + (s,) for s in (0, 1)]
    ref_i = np.concatenate([i for i, _, _ in ref])
    ref_band = np.concatenate([m // 15 for _, m, _ in ref])
    ref_nw = np.concatenate([not_won(i, s) for i, _, s in ref])
    rates = np.stack([(weights[:, ref_i[ref_band == b]] @ ref_nw[ref_band == b])
                      / weights[:, ref_i[ref_band == b]].sum(1) for b in range(6)], axis=1)

    rows = []
    years = core["year"].to_numpy()
    for case, col in (("2-0", "two_nil_min"), ("2-1 after 2-0", "two_one_min")):
        ev = core[core["two_nil_side"].notna() & core[col].notna()]
        i = ev.index.to_numpy()
        side = ev["two_nil_side"].astype(int).to_numpy() - 1
        band = (ev[col].astype(int).clip(1, 90).to_numpy() - 1) // 15
        nw = not_won(i, side)
        w = weights[:, i]
        effect = (w @ nw) / w.sum(1) - (w * rates[:, band]).sum(1) / w.sum(1)
        halves = [float(nw[h].mean() - rates[0, band[h]].mean()) for h in _halves(years[i])]
        low, high = _interval(effect[1:])
        rows.append({"case": case, "k": int(nw.sum()), "n": len(nw), "value": float(nw.mean()),
                     "reference": float(nw.mean() - effect[0]), "effect": float(effect[0]),
                     "ci_low": round(low, 3), "ci_high": round(high, 3),
                     **{f"effect_{name}": h for name, h in zip(_half_names(), halves)}})
        if case == "2-1 after 2-0":
            agree = all(np.sign(h) == np.sign(effect[0]) for h in halves)
            summary = _summary("two_nil", "not won after the 2-1, minus 1-0 at the same minute", float(effect[0]),
                               low, high, config.MYTH_THRESHOLD, agree,
                               verdict(low, high, agree, low99=_interval(effect[1:], 99)[0]))
    return pd.DataFrame(rows), summary


def leader_scoring(matches: pd.DataFrame, goals: pd.DataFrame, from_minute: int = 76) -> tuple[pd.DataFrame, dict]:
    """Myth "the team leading by one sits back".

    From `from_minute` to the end of regulation: goals per 90 minutes of a team at 1-0, at 0-0 and at
    0-1 (score at the start of the minute). True only if the leader scores less AND the trailer more
    than a team at 0-0 (intervals of the ratios clear of 1, both halves agreeing); a myth if neither.
    """
    core = _core(matches)
    end = score_grid(core, goals)
    zeros = np.zeros((2, len(core), 1), dtype=int)
    start = np.concatenate([zeros, end[:, :, :-1]], axis=2)
    scored = np.diff(np.concatenate([zeros, end], axis=2), axis=2)
    late = np.arange(1, 91) >= from_minute
    states = {"lead 1-0": (1, 0), "level 0-0": (0, 0), "trail 0-1": (0, 1)}
    goals_in = np.zeros((len(core), 3))
    minutes_in = np.zeros((len(core), 3))
    for s in (0, 1):
        for j, (own, opp) in enumerate(states.values()):
            at = (start[s] == own) & (start[1 - s] == opp) & late
            goals_in[:, j] += (scored[s] * at).sum(1)
            minutes_in[:, j] += at.sum(1)

    def ratios(w):
        per90 = (w @ goals_in) / (w @ minutes_in) * 90
        return per90, per90[:, 0] / per90[:, 1], per90[:, 2] / per90[:, 1]

    per90, lead, trail = ratios(_with_resamples(_rng(), len(core)))
    halves = [ratios(h.astype(float)[None, :]) for h in _halves(core["year"].to_numpy())]
    lead_ci, trail_ci = _interval(lead[1:]), _interval(trail[1:])
    rows = []
    for j, state in enumerate(states):
        ratio, ci = {0: (lead, lead_ci), 2: (trail, trail_ci)}.get(j, (None, (None, None)))
        rows.append({"state": state, "k": int(goals_in[:, j].sum()), "n": int(minutes_in[:, j].sum()),
                     "value": float(per90[0, j]), "ratio_to_level": None if ratio is None else float(ratio[0]),
                     "ci_low": None if ci[0] is None else round(ci[0], 3),
                     "ci_high": None if ci[1] is None else round(ci[1], 3),
                     **{f"ratio_{name}": (None if ratio is None else float((h[1] if j == 0 else h[2])[0]))
                        for name, h in zip(_half_names(), halves)}})
    lead_less = lead_ci[1] < 1 and all(h[1][0] < 1 for h in halves)
    trail_more = trail_ci[0] > 1 and all(h[2][0] > 1 for h in halves)
    result = "true" if lead_less and trail_more else ("myth" if not (lead_less or trail_more) else "partly_true")
    agree = all(np.sign(h[1][0] - 1) == np.sign(lead[0] - 1) and np.sign(h[2][0] - 1) == np.sign(trail[0] - 1)
                for h in halves)
    summary = _summary("leader_sits_back", "1 - (leader at 1-0 / team at 0-0), goals per 90 from minute 76",
                       float(1 - lead[0]), 1 - lead_ci[1], 1 - lead_ci[0], None, agree, result)
    return pd.DataFrame(rows), summary


def late_specialists(matches: pd.DataFrame, goals: pd.DataFrame, team_matches: pd.DataFrame,
                     min_matches: int = config.MYTH_MIN_MATCHES) -> tuple[pd.DataFrame, dict]:
    """Myth "some teams are specialists in deciding late".

    Share of each team's regulation goals scored (and conceded) in the final quarter, for teams with
    `min_matches` or more, with funnel limits around the pooled share. A myth if no team falls outside
    the 99.8% limit (outside 95% is expected for ~1 in 20 teams by chance).
    """
    core = _core(matches)
    tm = team_matches[team_matches["match_id"].isin(core["match_id"])]
    played = tm.groupby("team").size()
    teams = played[played >= min_matches].index
    reg = goals[~goals["extra_time"] & goals["match_id"].isin(core["match_id"])]
    names = core.set_index("match_id")
    reg = reg.assign(against=np.where(reg["side"] == 1, names.loc[reg["match_id"], "team2"],
                                      names.loc[reg["match_id"], "team1"]))
    parts = []
    for direction, col in (("scored", "team"), ("conceded", "against")):
        t = reg[reg[col].isin(teams)].groupby(col)["final_quarter"].agg(k="sum", n="size")
        mean = t["k"].sum() / t["n"].sum()
        se = np.sqrt(mean * (1 - mean) / t["n"])
        parts.append(t.assign(value=t["k"] / t["n"], mean=mean, z=(t["k"] / t["n"] - mean) / se,
                              low95=mean - Z95 * se, high95=mean + Z95 * se,
                              low998=mean - Z998 * se, high998=mean + Z998 * se)
                     .rename_axis("team").reset_index().assign(direction=direction))
    detail = pd.concat(parts, ignore_index=True)
    detail = detail.assign(matches=detail["team"].map(played), k=detail["k"].astype(int))
    detail = detail[["direction", "team", "matches", "k", "n", "value", "mean", "z",
                     "low95", "high95", "low998", "high998"]]
    beyond = int((detail["z"].abs() > Z998).sum())
    summary = _summary("late_specialists", "teams outside the 99.8% funnel limit (scored or conceded)",
                       float(beyond), None, None, None, None, "myth" if beyond == 0 else "true")
    return detail, summary


def opener_survival(team_matches: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Myth "lose the opener and you are out" (and: the 48-team format softened it).

    Share of teams that reached the knockout, by format era and opener result. The verdict is on the
    48-team minus 32-team difference among opener losers (it is about the format, so the halves
    rule does not apply).
    """
    tm = team_matches[team_matches["finished"] & team_matches["stage"].isin(["groups", "knockout"])]
    ko = tm[tm["stage"] == "knockout"]
    reached = set(zip(ko["year"], ko["team"]))
    op = add_era(tm[tm["is_opener"].fillna(False).astype(bool)])
    op = op.assign(advanced=[(y, t) in reached for y, t in zip(op["year"], op["team"])])
    detail = op.groupby(["era", "result"])["advanced"].agg(k="sum", n="size").reset_index()
    detail = detail.assign(k=detail["k"].astype(int), value=detail["k"] / detail["n"])
    lost = op[op["result"] == "L"]
    l32 = lost.loc[lost["era"] == "32-teams", "advanced"].to_numpy(float)
    l48 = lost.loc[lost["era"] == "48-teams", "advanced"].to_numpy(float)
    measure = "reached the knockout after losing the opener, 48 minus 32 teams"
    if not (len(l32) and len(l48)):
        return detail, _summary("opener_loss", measure, float("nan"), None, None, config.MYTH_THRESHOLD, None,
                                "undecided")
    rng = _rng()
    samples = (l48[rng.integers(len(l48), size=(config.MYTH_DRAWS, len(l48)))].mean(1)
               - l32[rng.integers(len(l32), size=(config.MYTH_DRAWS, len(l32)))].mean(1))
    low, high = _interval(samples)
    summary = _summary("opener_loss", measure, float(l48.mean() - l32.mean()), low, high, config.MYTH_THRESHOLD,
                       None, verdict(low, high, True, low99=_interval(samples, 99)[0]))
    return detail, summary


SEASON_HEADLINES = (  # (metric, stage or None for both, value per match)
    ("goals_per_match_90", None, lambda d: d["goals_regulation"]),
    ("big_margin", "groups", lambda d: d["margin"] >= config.BIG_MARGIN),
    ("one_goal_margin_90", "groups", lambda d: (d["margin_ft"] == 1).where(d["margin_ft"] > 0)),
    ("decided_final_quarter", "knockout", lambda d: d["decided_final_quarter"]),
    ("stoppage_goals_per_match", None, lambda d: d["stoppage_goals"]),
)


def season_outlier(matches: pd.DataFrame, goals: pd.DataFrame, year: int = config.SEASON) -> tuple[pd.DataFrame, dict]:
    """Myth "2026 was an outlier World Cup": an audit of the published headlines.

    For each headline, draw a World Cup of the same size from all editions (without replacement)
    and see where `year` falls. Outside the 95% band: "outside"; inside but beyond the 5th/95th
    percentile: "edge"; else "inside".
    """
    core = _core(matches)
    stoppage = goals[goals["stoppage"]].groupby("match_id").size()
    core = core.assign(stoppage_goals=core["match_id"].map(stoppage).fillna(0))
    rng = _rng()
    rows = []
    for metric, stage, per_match in SEASON_HEADLINES:
        part = core if stage is None else core[core["stage"] == stage]
        x = per_match(part).astype(float)
        keep = x.notna().to_numpy()
        x = x.to_numpy()[keep]
        in_year = part["year"].to_numpy()[keep] == year
        value = float(x[in_year].mean())
        sims = np.array([rng.choice(x, in_year.sum(), replace=False).mean() for _ in range(config.MYTH_DRAWS)])
        low, high = _interval(sims)
        pct = float((sims < value).mean())
        reading = ("outside" if value > high or value < low
                   else "edge" if pct >= 0.95 or pct <= 0.05 else "inside")
        rows.append({"metric": metric, "stage": stage or "all", "n": int(in_year.sum()), "value": value,
                     "mean_all": float(x.mean()), "band_low": round(low, 3), "band_high": round(high, 3),
                     "percentile": round(pct, 3), "reading": reading})
    detail = pd.DataFrame(rows)
    outside = int((detail["reading"] == "outside").sum())
    result = "myth" if outside == 0 else ("true" if outside == len(detail) else "partly_true")
    return detail, _summary("season_outlier", f"headlines of {year} outside the band of all editions",
                            float(outside), None, None, None, None, result)


def _result_90(matches: pd.DataFrame) -> np.ndarray:
    """Team 1's result at 90': 1 win, 0.5 draw, 0 loss."""
    return np.select([matches["goals_ft1"] > matches["goals_ft2"], matches["goals_ft1"] == matches["goals_ft2"]],
                     [1.0, 0.5], 0.0)


def _grouped_means(values: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """Mean of `values`, then one bootstrap mean per resample of whole groups (e.g. matches)."""
    codes, uniq = pd.factorize(groups)
    sums = np.bincount(codes, weights=values)
    counts = np.bincount(codes)
    w = _with_resamples(_rng(), len(uniq))
    return (w @ sums) / (w @ counts)


def _standard(myth: str, measure: str, samples: np.ndarray, halves: list[float]) -> dict:
    """Summary under the standard rule: samples[0] is the effect, the rest its bootstrap."""
    effect = float(samples[0])
    low, high = _interval(samples[1:])
    agree = all(np.sign(h) == np.sign(effect) for h in halves)
    return _summary(myth, measure, effect, low, high, config.MYTH_THRESHOLD, agree,
                    verdict(low, high, agree, low99=_interval(samples[1:], 99)[0]))


def home_advantage(matches: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Myth "playing at home helps at the World Cup".

    Hosts' matches: result at 90' minus the Elo expectation WITHOUT home advantage (neutral ground).
    Bootstrap by match. For reference, Elo gives the home side 100 points, worth about +0.14.
    """
    core = _core(matches)
    r1 = _result_90(core)
    e1 = elo.expected(core["elo1"] - core["elo2"]).to_numpy()
    parts = []
    for side in (1, 2):
        host = np.array([t in config.HOSTS.get(y, ()) for t, y in zip(core[f"team{side}"], core["year"])], dtype=bool)
        result, expect = (r1, e1) if side == 1 else (1 - r1, 1 - e1)
        parts.append(pd.DataFrame({"year": core["year"][host], "team": core[f"team{side}"][host],
                                   "match_id": core["match_id"][host], "result": result[host],
                                   "expected": expect[host]}))
    rows = pd.concat(parts, ignore_index=True).assign(residual=lambda d: d["result"] - d["expected"])
    detail = (rows.groupby(["year", "team"])
              .agg(n=("result", "size"), result=("result", "mean"), expected=("expected", "mean"),
                   residual=("residual", "mean")).reset_index())
    samples = _grouped_means(rows["residual"].to_numpy(), rows["match_id"].to_numpy())
    halves = [rows.loc[h, "residual"].mean() for h in _halves(rows["year"].to_numpy())]
    return detail, _standard("home_advantage", "hosts' result at 90' minus the neutral Elo expectation",
                             samples, halves)


def favorite_in_knockout(matches: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Myth "the favorite suffers more in the knockout".

    Favorite (higher Elo) result at 90' minus its Elo expectation, in the group stage and in the
    knockout. Effect = group residual minus knockout residual (> 0: the favorite does worse in the
    knockout). Bootstrap by match.
    """
    core = _core(matches)
    r1 = _result_90(core)
    e1 = elo.expected(core["elo1"] - core["elo2"]).to_numpy()
    fav1 = (core["elo1"] >= core["elo2"]).to_numpy()
    result, expect = np.where(fav1, r1, 1 - r1), np.where(fav1, e1, 1 - e1)
    ko = core["is_knockout"].to_numpy()
    detail = pd.DataFrame([{"stage": stage, "n": int(mask.sum()), "result": result[mask].mean(),
                            "expected": expect[mask].mean(), "residual": (result - expect)[mask].mean()}
                           for stage, mask in (("groups", ~ko), ("knockout", ko))])
    residual = result - expect
    w = _with_resamples(_rng(), len(core))
    samples = (w[:, ~ko] @ residual[~ko]) / w[:, ~ko].sum(1) - (w[:, ko] @ residual[ko]) / w[:, ko].sum(1)
    halves = [residual[h & ~ko].mean() - residual[h & ko].mean() for h in _halves(core["year"].to_numpy())]
    return detail, _standard("favorite_knockout", "favorite's residual in groups minus in the knockout",
                             samples, halves)


def must_score_kicks(penalty_kicks: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Myth "the kick that must go in trembles".

    Shootout conversion when a miss eliminates the kicker at once (metrics.must_score) against the
    other kicks. Effect = other minus must-score. Bootstrap by shootout.
    """
    k = penalty_kicks
    must = k["must_score"].to_numpy(bool)
    scored = k["converted"].to_numpy(float)
    detail = pd.DataFrame([{"must_score": flag, "k": int(scored[mask].sum()), "n": int(mask.sum()),
                            "value": scored[mask].mean()} for flag, mask in ((True, must), (False, ~must))])
    codes, uniq = pd.factorize(k["match_id"])
    sums = {flag: (np.bincount(codes, weights=scored * mask, minlength=len(uniq)),
                   np.bincount(codes, weights=mask.astype(float), minlength=len(uniq)))
            for flag, mask in ((True, must), (False, ~must))}
    w = _with_resamples(_rng(), len(uniq))
    rate = {flag: (w @ s) / (w @ n) for flag, (s, n) in sums.items()}
    years = k["year"].to_numpy()
    halves = [scored[h & ~must].mean() - scored[h & must].mean() for h in _halves(years)]
    return detail, _standard("must_score_kick", "conversion of other kicks minus must-score kicks",
                             rate[False] - rate[True], halves)


def myths(matches: pd.DataFrame, goals: pd.DataFrame, team_matches: pd.DataFrame,
          penalty_kicks: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, dict]]:
    """The myths published on the site (ADR 0008): id -> (detail table, summary row).

    A slice with no cases (e.g. an era missing from a small dataset) gives NaN, exported as null.
    """
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        return {
            "two_nil": two_nil(matches, goals),
            "leader_sits_back": leader_scoring(matches, goals),
            "late_specialists": late_specialists(matches, goals, team_matches),
            "opener_loss": opener_survival(team_matches),
            "season_outlier": season_outlier(matches, goals),
            "home_advantage": home_advantage(matches),
            "favorite_knockout": favorite_in_knockout(matches),
            "must_score_kick": must_score_kicks(penalty_kicks),
        }
