"""Incremental update — the faithful analogue of codegraph's auto-reindex for a
remote source you can't inotify: poll for newly-published articles, then rebuild
the index.

Safe to run on a schedule (cron). The scraper skips articles already on disk, so
a run only fetches what's new; the index is then rebuilt from metadata.jsonl.

    python -m figraph.update                 # refresh current + previous year
    python -m figraph.update --years 2026     # only a specific year
"""
from __future__ import annotations

import argparse
import datetime
from pathlib import Path

from figraph import index, scrape


def main():
    ap = argparse.ArgumentParser(description="Incrementally refresh the figure library.")
    ap.add_argument("--out", type=Path, default=Path("figures"))
    ap.add_argument("--db", type=Path, default=Path("figraph.db"))
    ap.add_argument("--delay", type=float, default=0.8)
    ap.add_argument("--years", nargs="+", type=int, default=None,
                    help="years to refresh (default: current + previous year)")
    a = ap.parse_args()

    year = datetime.date.today().year
    years = a.years or [year - 1, year]
    print(f"update: scanning {list(scrape.JOURNALS)} for years {years}")
    scrape.scrape(list(scrape.JOURNALS), years, a.out, None, a.delay)
    index.build_index(a.out / "metadata.jsonl", a.db)


if __name__ == "__main__":
    main()
