"""SQLite + FTS5 store for the figure index.

The index is rebuilt wholesale from metadata.jsonl, so no triggers are needed:
insert rows into `figures`, then rebuild the external-content FTS5 table from it.
"""
from __future__ import annotations

import re
import sqlite3

SCHEMA = """
CREATE TABLE figures(
  id INTEGER PRIMARY KEY,
  journal TEXT, year INTEGER, article_id TEXT, doi TEXT,
  title TEXT, fig_num INTEGER, fig_title TEXT, legend TEXT,
  tags TEXT, image_url TEXT, local_path TEXT
);
CREATE VIRTUAL TABLE figures_fts USING fts5(
  title, legend, tags, content='figures', content_rowid='id'
);
"""

_COLS = ("journal", "year", "article_id", "doi", "title", "fig_num",
         "fig_title", "legend", "tags", "image_url", "local_path")


def connect(db: str) -> sqlite3.Connection:
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    return c


def build(db: str, rows: list[dict]) -> int:
    c = connect(db)
    c.executescript("DROP TABLE IF EXISTS figures; DROP TABLE IF EXISTS figures_fts;")
    c.executescript(SCHEMA)
    placeholders = ",".join(f":{k}" for k in _COLS)
    c.executemany(
        f"INSERT INTO figures({','.join(_COLS)}) VALUES({placeholders})",
        [{k: r.get(k) for k in _COLS} for r in rows],
    )
    c.execute("INSERT INTO figures_fts(figures_fts) VALUES('rebuild')")
    c.commit()
    n = c.execute("SELECT count(*) FROM figures").fetchone()[0]
    c.close()
    return n


def _fts_query(raw: str) -> str:
    """Make an FTS5-safe OR query from free text (avoids syntax errors on
    hyphens/punctuation; bm25 still ranks multi-term matches highest)."""
    terms = re.findall(r"\w+", raw, re.UNICODE)
    return " OR ".join(f'"{t}"' for t in terms) or '""'


def search(db: str, query: str, k: int = 10, tag: str | None = None) -> list[dict]:
    c = connect(db)
    sql = ("SELECT f.*, bm25(figures_fts, 2.0, 5.0, 3.0) AS score "
           "FROM figures_fts JOIN figures f ON f.id = figures_fts.rowid "
           "WHERE figures_fts MATCH ?")
    args: list = [_fts_query(query)]
    if tag:
        sql += " AND f.tags LIKE ?"
        args.append(f"%{tag}%")
    sql += " ORDER BY score LIMIT ?"
    args.append(k)
    rows = [dict(r) for r in c.execute(sql, args)]
    c.close()
    return rows
