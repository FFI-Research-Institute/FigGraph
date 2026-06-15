"""MCP server — exposes the figure index to an agent as `figraph_*` tools, the
way codegraph exposes `codegraph_*`.

Run:   figraph serve            (or  python -m figraph.mcp_server)
Config (env):  FIGRAPH_DB  (default figraph.db)   FIGRAPH_DIR (default figures)

Imports only the SQLite store, so it needs no scraping deps (httpx/lxml) — just
the `mcp` package.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from figraph import store

DB = os.environ.get("FIGRAPH_DB", "figraph.db")
FIGDIR = Path(os.environ.get("FIGRAPH_DIR", "figures"))

mcp = FastMCP("figraph")


@mcp.tool()
def figraph_search(query: str, k: int = 10, tag: str | None = None) -> list[dict]:
    """Search the indexed scientific figures and return the best matches.

    Use this when deciding how to plot something: search by the content or chart
    type you want, then open the returned image paths to see real published
    figures worth emulating.

    Args:
        query: free text describing the content or chart type (e.g.
            "kaplan-meier survival hazard ratio", "single-cell umap clusters").
        k: number of results to return.
        tag: optional chart-type filter, e.g. survival, heatmap, umap-tsne, box.

    Returns a list of figures, each with its local image `path`, `caption`,
    `journal`, `year`, `tags`, and relevance `score`.
    """
    rows = store.search(DB, query, k, tag)
    out = []
    for r in rows:
        out.append({
            "path": str(FIGDIR / r["local_path"]),
            "journal": r["journal"], "year": r["year"],
            "title": r["title"], "fig_num": r["fig_num"],
            "tags": r["tags"], "score": round(r["score"], 3),
            "caption": (r["legend"] or "")[:400],
        })
    return out


@mcp.tool()
def figraph_status() -> dict:
    """Report where the figure index lives and how many figures it holds."""
    if not Path(DB).exists():
        return {"db": DB, "exists": False,
                "hint": "build it with `figraph index` first"}
    c = sqlite3.connect(DB)
    n = c.execute("SELECT count(*) FROM figures").fetchone()[0]
    j = c.execute("SELECT count(DISTINCT journal) FROM figures").fetchone()[0]
    c.close()
    return {"db": DB, "figdir": str(FIGDIR), "figures": n, "journals": j}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
