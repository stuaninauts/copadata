"""Ingest: download the 2026 World Cup JSON from OpenFootball into data/raw/.

No key, no quota: downloads a single JSON (~40KB) and saves the raw snapshot. Idempotent —
re-running overwrites with the latest state, picking up new matches as the tournament
progresses (cumulative snapshot).
"""
from __future__ import annotations

import json

import requests

from copadata import config


def download() -> dict:
    """Download the current OpenFootball snapshot and save it into data/raw/."""
    config.RAW.mkdir(parents=True, exist_ok=True)
    resp = requests.get(config.OPENFOOTBALL_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    config.RAW_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ingest] downloaded: {len(data.get('matches', []))} matches -> {config.RAW_JSON}")
    return data


def load() -> dict:
    """Read the raw snapshot already downloaded (no network)."""
    return json.loads(config.RAW_JSON.read_text(encoding="utf-8"))


if __name__ == "__main__":
    download()
