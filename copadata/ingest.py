"""Ingest: download the raw sources into data/raw/.

- 2026: the OpenFootball World Cup JSON (~40KB), pinned to a commit (ADR 0006). No key, no quota.
- 1986-2022: the Fjelstul World Cup Database CSVs, pinned to a commit (see ADR 0005).
- Team strength: the international results since 1872 (CC0), pinned to a commit (ADR 0009).
"""
from __future__ import annotations

import json

import pandas as pd
import requests

from copadata import config


def download() -> dict:
    """Download the pinned OpenFootball snapshot and save it into data/raw/."""
    config.RAW.mkdir(parents=True, exist_ok=True)
    resp = requests.get(config.OPENFOOTBALL_URL.format(commit=config.OPENFOOTBALL_COMMIT), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    config.RAW_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ingest] downloaded: {len(data.get('matches', []))} matches @ {config.OPENFOOTBALL_COMMIT[:7]} -> {config.RAW_JSON}")
    return data


def load() -> dict:
    """Read the raw snapshot already downloaded (no network)."""
    return json.loads(config.RAW_JSON.read_text(encoding="utf-8"))


def download_history() -> None:
    """Download the pinned Fjelstul CSVs into data/raw/fjelstul/."""
    config.FJELSTUL_RAW.mkdir(parents=True, exist_ok=True)
    for name in config.FJELSTUL_TABLES:
        url = config.FJELSTUL_URL.format(commit=config.FJELSTUL_COMMIT, name=name)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        path = config.FJELSTUL_RAW / f"{name}.csv"
        path.write_bytes(resp.content)
        print(f"[ingest] downloaded: fjelstul {name} @ {config.FJELSTUL_COMMIT[:7]} -> {path}")


def load_history() -> dict[str, pd.DataFrame] | None:
    """Read the Fjelstul CSVs already downloaded, or None if they aren't there yet."""
    paths = {name: config.FJELSTUL_RAW / f"{name}.csv" for name in config.FJELSTUL_TABLES}
    if not all(p.exists() for p in paths.values()):
        return None
    return {name: pd.read_csv(p) for name, p in paths.items()}


def download_international() -> None:
    """Download the pinned international results CSVs into data/raw/international/."""
    config.INTERNATIONAL_RAW.mkdir(parents=True, exist_ok=True)
    for name in config.INTERNATIONAL_TABLES:
        url = config.INTERNATIONAL_URL.format(commit=config.INTERNATIONAL_COMMIT, name=name)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        path = config.INTERNATIONAL_RAW / f"{name}.csv"
        path.write_bytes(resp.content)
        print(f"[ingest] downloaded: international {name} @ {config.INTERNATIONAL_COMMIT[:7]} -> {path}")


def load_international() -> dict[str, pd.DataFrame] | None:
    """Read the international results CSVs already downloaded, or None if they aren't there yet."""
    paths = {name: config.INTERNATIONAL_RAW / f"{name}.csv" for name in config.INTERNATIONAL_TABLES}
    if not all(p.exists() for p in paths.values()):
        return None
    return {name: pd.read_csv(p) for name, p in paths.items()}


if __name__ == "__main__":
    download()
    download_history()
    download_international()
