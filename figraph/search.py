"""Search the figure index — the entry point Claude calls when picking a figure.

    python -m figraph.search "kaplan-meier survival hazard ratio" -k 8
    python -m figraph.search "single-cell umap clusters" --tag umap-tsne --json
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

from figraph import store


def _render_html(query, rows, outpath):
    """Write a thumbnail gallery: each hit shows the figure, its metadata, and
    its absolute original path (selectable for copy)."""
    out_dir = os.path.dirname(os.path.abspath(outpath)) or "."
    cards = []
    for i, r in enumerate(rows, 1):
        img_abs = os.path.abspath(r["path"])
        src = os.path.relpath(img_abs, out_dir)  # so the <img> resolves anywhere
        tags = f" · {html.escape(r['tags'])}" if r["tags"] else ""
        cards.append(
            f'<div class="card"><a href="{html.escape(src)}" target="_blank">'
            f'<img src="{html.escape(src)}" loading="lazy"></a><div class="meta">'
            f'<div class="rank">#{i} · {html.escape(r["journal"])} {r["year"]} · '
            f'score {r["score"]:.2f}{tags}</div>'
            f'<div class="title">{html.escape(r["title"])}</div>'
            f'<div class="legend">{html.escape((r["legend"] or "")[:300])}</div>'
            f'<code class="path">{html.escape(img_abs)}</code></div></div>'
        )
    doc = (
        '<!doctype html><meta charset="utf-8">'
        f'<title>figraph: {html.escape(query)}</title><style>'
        'body{font-family:ui-sans-serif,system-ui,sans-serif;margin:24px;'
        'background:#0d1117;color:#e6edf3}h1{font-size:17px}h1 span{color:#8b5cf6}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}'
        '.card{background:#161b22;border:1px solid #30363d;border-radius:10px;overflow:hidden}'
        '.card img{width:100%;max-height:260px;object-fit:contain;background:#fff;display:block}'
        '.meta{padding:10px 12px}.rank{font-size:12px;color:#8b949e}'
        '.title{font-size:13px;margin:4px 0}.legend{font-size:11px;color:#8b949e;'
        'line-height:1.4;max-height:60px;overflow:hidden}.path{display:block;margin-top:8px;'
        'font-size:11px;color:#79c0ff;word-break:break-all;user-select:all}'
        '</style>'
        f'<h1>figraph search · <span>{html.escape(query)}</span> · {len(rows)} results</h1>'
        f'<div class="grid">{"".join(cards)}</div>'
    )
    Path(outpath).write_text(doc, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Search the figraph figure index.")
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=10, help="number of results")
    ap.add_argument("--tag", help="filter by chart-type tag (e.g. survival)")
    ap.add_argument("--db", type=Path, default=Path("figraph.db"))
    ap.add_argument("--figdir", type=Path, default=Path("figures"),
                    help="root the local_path is relative to")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--html", metavar="OUT.html",
                    help="write an HTML thumbnail gallery (with original paths)")
    a = ap.parse_args()

    rows = store.search(str(a.db), a.query, a.k, a.tag)
    for r in rows:
        r["path"] = str(a.figdir / r["local_path"])

    if a.html:
        _render_html(a.query, rows, a.html)
        print(f"wrote {a.html}  ({len(rows)} results)")
        return

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
