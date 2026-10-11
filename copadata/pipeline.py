"""Run the pipeline end to end: ingest -> transform -> derive.

Downloads the pinned OpenFootball JSON (2026) and the pinned Fjelstul CSVs (1986-2022), then
reprocesses every edition. Idempotent: the same commits always give the same tables.

    python -m copadata.pipeline            # download and reprocess
    python -m copadata.pipeline --offline  # reprocess the snapshot already downloaded
"""
from __future__ import annotations

import sys

from copadata import derive, ingest, transform


def main(download: bool = True) -> None:
    if download:
        ingest.download()
        ingest.download_history()
    transform.main()
    derive.main()
    print("[pipeline] done.")


if __name__ == "__main__":
    main(download="--offline" not in sys.argv)
