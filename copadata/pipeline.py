"""Run the pipeline end to end: ingest -> transform -> derive.

Cumulative re-run: downloads the current OpenFootball state and reprocesses. Idempotent —
running again after new rounds simply incorporates the new matches.

    python -m copadata.pipeline            # download and reprocess
    python -m copadata.pipeline --offline  # reprocess the snapshot already downloaded
"""
from __future__ import annotations

import sys

from copadata import derive, ingest, transform


def main(download: bool = True) -> None:
    if download:
        ingest.download()
    transform.main()
    derive.main()
    print("[pipeline] done.")


if __name__ == "__main__":
    main(download="--offline" not in sys.argv)
