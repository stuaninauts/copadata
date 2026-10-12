"""Definitions of the match time/decision metrics — the single home for these concepts.

Every metric derived from goals is defined here; the rest of the pipeline only consumes
these results, it never redefines them.

Time/goal rules:
- A penalty shootout is never a goal (it lives in score.p, not in the goal arrays).
- Extra-time goal = base minute > 90' (its own category).
- Late goal = base minute >= 80' in REGULATION (includes stoppage "90+X"); extra time doesn't count.
- Minute "90+2" -> base 90; "103" -> base 103 (extra time).
"""
from __future__ import annotations

from dataclasses import dataclass

from copadata import config


@dataclass(frozen=True)
class Goal:
    """A regulation- or extra-time goal (NOT a penalty shootout kick)."""

    side: int          # 1 = team1, 2 = team2
    minute: int        # base minute ("90+2" -> 90; "103" -> 103)
    order: float       # sort key (base + stoppage/100)
    extra_time: bool   # True if base minute > 90
    own_goal: bool
    penalty: bool      # penalty kick in play (not the shootout)
    player: str


def parse_minute(minute) -> tuple[int, float, bool]:
    """'90+2' -> (90, 90.02, False); '103' -> (103, 103.0, True)."""
    s = str(minute).strip()
    if "+" in s:
        base_s, stoppage_s = s.split("+", 1)
        base = int(base_s)
        stoppage = int(stoppage_s) if stoppage_s.isdigit() else 0
    else:
        base, stoppage = int(s), 0
    return base, base + stoppage / 100.0, base > 90


def match_goals(match: dict) -> list["Goal"]:
    """All goals (regulation + extra time), ordered. Excludes the penalty shootout.

    Without extra time, a minute past 90 is second-half stoppage time: some sources write
    "92" for "90+2".
    """
    played_et = "et" in (match.get("score") or {})
    goals: list[Goal] = []
    for side, key in ((1, "goals1"), (2, "goals2")):
        for g in match.get(key) or []:
            base, order, et = parse_minute(g["minute"])
            if et and not played_et:
                base, order, et = 90, 90 + (base - 90) / 100.0, False
            goals.append(
                Goal(side, base, order, et, bool(g.get("owngoal")), bool(g.get("penalty")), g.get("name", ""))
            )
    goals.sort(key=lambda x: x.order)
    return goals


def final_score(goals: list["Goal"]) -> tuple[int, int]:
    """Score at the end of regulation + extra time (shootout not counted)."""
    return sum(g.side == 1 for g in goals), sum(g.side == 2 for g in goals)


def is_late_goal(g: "Goal") -> bool:
    """>= 80' in regulation (includes stoppage). Extra time doesn't count."""
    return (not g.extra_time) and g.minute >= config.LATE_GOAL_MIN


def is_stoppage_goal(g: "Goal") -> bool:
    """Second-half stoppage time ("90+X"). Extra time doesn't count."""
    return not g.extra_time and g.minute == 90 and g.order > 90


def winning_goal(goals: list["Goal"]):
    """The goal that gave the winner the lead they kept to the end (game-winner).

    Standard definition: the (loser_goals + 1)-th goal of the winner, in chronological order.
    None if level at the end of regulation+extra time (includes penalty-shootout games).
    """
    s1, s2 = final_score(goals)
    if s1 == s2:
        return None
    winner = 1 if s1 > s2 else 2
    target = min(s1, s2) + 1
    count = 0
    for g in goals:
        if g.side == winner:
            count += 1
            if count == target:
                return g
    return None


def comeback_events(goals: list["Goal"]) -> list["Goal"]:
    """Moments when the team that was LOSING went ahead (a comeback).

    A single goal never flips from behind to ahead directly (only behind->level or level->ahead),
    so a comeback is the goal that TAKES THE LEAD for a team that had TRAILED earlier.
    """
    s1 = s2 = 0
    trailed = {1: False, 2: False}
    events = []
    for g in goals:
        a1, a2 = s1, s2
        if a1 < a2:
            trailed[1] = True
        if a2 < a1:
            trailed[2] = True
        if g.side == 1:
            s1 += 1
        else:
            s2 += 1
        was_ahead = (a1 > a2) if g.side == 1 else (a2 > a1)
        now_ahead = (s1 > s2) if g.side == 1 else (s2 > s1)
        if now_ahead and not was_ahead and trailed[g.side]:
            events.append(g)
    return events


def lead_changes(goals: list["Goal"]) -> int:
    """Secondary metric: how many times the leading side changes (includes leaving a tie)."""
    s1 = s2 = 0
    leader = 0
    changes = 0
    for g in goals:
        if g.side == 1:
            s1 += 1
        else:
            s2 += 1
        new = 1 if s1 > s2 else (2 if s2 > s1 else 0)
        if new != 0 and new != leader:
            changes += 1
            leader = new
    return changes


def survival_goal(goals: list["Goal"], is_knockout: bool, ft: list[int]):
    """Knockout only. The REGULATION goal that leveled the score from behind, in a match that
    ended level in regulation (forcing extra time/penalties) — the equalizer that avoided
    elimination. None otherwise.
    """
    if not is_knockout or ft[0] != ft[1]:
        return None
    s1 = s2 = 0
    survival = None
    for g in goals:
        if g.extra_time:
            break  # regulation only
        a1, a2 = s1, s2
        if g.side == 1:
            s1 += 1
        else:
            s2 += 1
        if s1 == s2 and ((g.side == 1 and a1 < a2) or (g.side == 2 and a2 < a1)):
            survival = g
    return survival


# --- "Regulation only" lens (fair group vs knockout comparison) ------------------
# The knockout has extra time and the group stage doesn't; restricting to regulation
# removes that artifact and compares what both buckets actually share.

FINAL_QUARTER_MIN = 76  # "final quarter" of the match = 76'-90' (includes stoppage)


def is_final_quarter_goal(g: "Goal") -> bool:
    """Regulation goal in the final quarter (76'-90', stoppage included). Extra time doesn't count."""
    return not g.extra_time and g.minute >= FINAL_QUARTER_MIN


def two_goal_lead(goals: list["Goal"]) -> tuple[int, int, int | None] | None:
    """Regulation only. The first time a side leads exactly 2-0: (side, minute, minute of the 2-1
    that follows or None). The 2-1 can only be the next goal: if the leader scores first it is 3-0.
    None if no side ever led 2-0.
    """
    s = {1: 0, 2: 0}
    lead = None
    for g in goals:
        if g.extra_time:
            break
        s[g.side] += 1
        if lead is not None:
            return (*lead, g.minute) if g.side != lead[0] else (*lead, None)
        if sorted(s.values()) == [0, 2]:
            lead = (g.side, g.minute)
    return (*lead, None) if lead else None


def must_score(kicks: list[tuple[str, bool]]) -> list[bool]:
    """Shootout kicks in order as (team, converted): True where a miss eliminates the kicker at once.

    In the first five rounds: even scoring every kick left after this one would not reach the rival.
    In sudden death (round 6 on): the second kicker of the round, after the rival scored.
    """
    first = kicks[0][0] if kicks else None
    goals: dict[str, int] = {}
    taken: dict[str, int] = {}
    out = []
    for team, converted in kicks:
        rival = next((t for t, _ in kicks if t != team), None)
        a, b = goals.get(team, 0), goals.get(rival, 0)
        rnd = taken.get(team, 0) + 1
        out.append(a + (5 - rnd) < b if rnd <= 5 else (team != first and b > a))
        goals[team] = a + bool(converted)
        taken[team] = rnd
    return out


def winning_goal_regulation(goals: list["Goal"], ft: list[int]):
    """Game-winner using regulation only and the 90' score (ft). None if level at 90'."""
    if ft[0] == ft[1]:
        return None
    winner = 1 if ft[0] > ft[1] else 2
    target = min(ft[0], ft[1]) + 1
    count = 0
    for g in goals:
        if g.extra_time:
            break
        if g.side == winner:
            count += 1
            if count == target:
                return g
    return None


def decisive_moment_regulation(goals: list["Goal"], ft: list[int], is_knockout: bool):
    """The goal that 'settled' the match within 90':
    - decided at 90' -> the regulation winning goal;
    - knockout level at 90' -> the survival goal (equalizer that forced extra time);
    - otherwise (0-0, group draw) -> None.
    """
    if ft[0] != ft[1]:
        return winning_goal_regulation(goals, ft)
    if is_knockout:
        return survival_goal(goals, True, ft)
    return None
