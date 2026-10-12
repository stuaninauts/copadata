"""Tests for copadata/export.py on a tiny two-edition dataset built through the real pipeline steps."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from copadata import config, derive, export, transform


def gm(t1, t2, s1, s2, day, year, round_="Group stage", group="Group A", et=None, p=None):
    score = {"ft": [s1, s2]}
    if et:
        score["et"] = et
    if p:
        score["p"] = p
    return {"round": round_, "group": group, "date": f"{year}-06-{day:02d}", "team1": t1, "team2": t2, "score": score,
            "goals1": [{"minute": "10"}] * s1, "goals2": [{"minute": "85"}] * s2}


def edition(year):
    return {"matches": [
        gm("A", "B", 1, 0, 1, year), gm("C", "D", 0, 0, 1, year),
        gm("A", "C", 2, 1, 5, year), gm("B", "D", 0, 2, 5, year),
        gm("A", "D", 0, 0, 9, year), gm("B", "C", 1, 1, 9, year),
        gm("A", "D", 1, 1, 12, year, round_="Final", group=None, et=[1, 1], p=[4, 2]),
    ]}


@pytest.fixture
def data():
    eds = {1990: edition(1990), 2026: edition(2026)}
    matches = pd.concat([transform.build_matches(d, y) for y, d in eds.items()], ignore_index=True)
    goals = pd.concat([transform.build_goals(d, y) for y, d in eds.items()], ignore_index=True)
    return {"matches": matches, "goals": goals, "team_matches": derive.group_situation(derive.explode(matches))}


def test_writes_every_table_with_manifest_and_readme(data, tmp_path):
    export.write(data, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    files = {f for t in manifest["tables"].values() for f in t["files"]}
    assert files | {"manifest.json", "README.md"} == {p.name for p in tmp_path.iterdir()}
    assert manifest["license"] == "CC-BY-SA-4.0" and manifest["editions"] == [1990, 2026]
    assert manifest["sources"]["fjelstul"]["editions"] == [1990]
    assert "Fjelstul" in (tmp_path / "README.md").read_text()


def test_summary_has_edition_era_and_history_scopes(data, tmp_path):
    export.write(data, tmp_path)
    rows = json.loads((tmp_path / "summary.json").read_text())
    scopes = {(r["scope_type"], r["scope"]) for r in rows}
    assert scopes == {("edition", "1990"), ("edition", "2026"), ("era", "24-teams"), ("era", "48-teams"),
                      ("history", "1986-2022")}
    (final,) = [r for r in rows if r["scope"] == "2026" and r["stage"] == "knockout" and r["metric"] == "penalties"]
    assert (final["k"], final["n"], final["value"]) == (1, 1, 1.0)


def test_missing_values_are_null_in_json_and_empty_in_csv(data, tmp_path):
    export.write(data, tmp_path)
    rows = json.loads((tmp_path / "summary.json").read_text())
    (r,) = [r for r in rows if r["scope"] == "2026" and r["stage"] == "knockout" and r["metric"] == "winning_goal_min"]
    assert r["k"] is None and r["n"] == 0 and r["value"] is None
    assert "NaN" not in (tmp_path / "summary.json").read_text()
    assert ",<NA>," not in (tmp_path / "summary.csv").read_text()


def test_single_test_uses_only_the_past_as_null(data, tmp_path):
    (t,) = export.single_tests(data["matches"][data["matches"].stage.isin(export.CORE_STAGES)]).to_dict("records")
    assert (t["scope"], t["null_scope"], t["alternative"]) == ("2026", "1986-2022", "greater")
    assert 0 <= t["p_value"] <= 1


def test_check_passes_when_fresh_and_names_each_difference(data, tmp_path):
    export.write(data, tmp_path)
    assert export.check(data, tmp_path) == []
    (tmp_path / "summary.csv").write_text("edited by hand\n")
    (tmp_path / "margins.json").unlink()
    (tmp_path / "notes.txt").write_text("x")
    assert export.check(data, tmp_path) == ["missing: margins.json", "unexpected: notes.txt", "outdated: summary.csv"]


def test_check_flags_a_changed_parquet(data, tmp_path):
    export.write(data, tmp_path)
    data["matches"].iloc[:1].to_parquet(tmp_path / "matches.parquet", index=False)
    assert export.check(data, tmp_path) == ["outdated: matches.parquet"]


def test_export_is_deterministic(data, tmp_path):
    export.write(data, tmp_path / "a")
    export.write(data, tmp_path / "b")
    for p in (tmp_path / "a").iterdir():
        if p.suffix != ".parquet":
            assert p.read_bytes() == (tmp_path / "b" / p.name).read_bytes(), p.name


@pytest.mark.skipif(not config.MATCHES_PARQUET.exists(), reason="run the pipeline first")
def test_committed_export_is_up_to_date():
    assert export.check(export.load(), config.EXPORT) == [], "run `python -m copadata.export`"


def test_myths_table_has_one_verdict_per_published_myth(data, tmp_path):
    export.write(data, tmp_path)
    rows = json.loads((tmp_path / "myths.json").read_text())
    assert [r["myth"] for r in rows] == list(export.MYTHS)
    assert {r["verdict"] for r in rows} <= {"true", "true_borderline", "partly_true", "undecided", "myth"}
    assert all((tmp_path / f"myth_{name}.json").exists() for name in export.MYTHS)
