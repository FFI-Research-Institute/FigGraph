"""Search the figure index — the entry point Claude calls when picking a figure.

    python -m figraph.search "kaplan-meier survival hazard ratio" -k 8
    python -m figraph.search "single-cell umap clusters" --tag umap-tsne --json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from figraph import store


def main():
    ap = argparse.ArgumentParser(description="Search the figraph figure index.")
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=10, help="number of results")
    ap.add_argument("--tag", help="filter by chart-type tag (e.g. survival)")
    ap.add_argument("--db", type=Path, default=Path("figraph.db"))
    ap.add_argument("--figdir", type=Path, default=Path("figures"),
                    help="root the local_path is relative to")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = store.search(str(a.db), a.query, a.k, a.tag)
    for r in rows:
        r["path"] = str(a.figdir / r["local_path"])

    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if not rows:
        print("(no matches)")
        return
    for i, r in enumerate(rows, 1):
        tags = f"  [{r['tags']}]" if r["tags"] else ""
        print(f"{i}. {r['path']}{tags}")
        print(f"   {r['journal']} {r['year']}  ·  {r['title'][:80]}")
        print(f"   {r['legend'][:160]}")
        print()


if __name__ == "__main__":
    main()
