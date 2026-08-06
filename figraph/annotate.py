"""Incremental caption weak labels for figures encountered during search."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
from pathlib import Path

from figraph import recommend, store


LEVEL = "L2_caption_weak_label"
TAXONOMY_VERSION = "visual-intent-v1"
ANNOTATOR_VERSION = "caption-rules-v1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS annotation_jobs(
  figure_key TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  fig_title TEXT NOT NULL DEFAULT '',
  legend TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '',
  source_query TEXT NOT NULL DEFAULT '',
  content_hash TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  annotator_version TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending', 'processing', 'done', 'no_signal', 'failed')),
  seen_count INTEGER NOT NULL DEFAULT 1,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS annotation_jobs_status_idx
  ON annotation_jobs(status, seen_count DESC, updated_at);

CREATE TABLE IF NOT EXISTS figure_annotations(
  figure_key TEXT NOT NULL,
  level TEXT NOT NULL,
  labels_json TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  confidence REAL NOT NULL,
  content_hash TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  annotator_version TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(figure_key, level)
);
"""


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)


def ensure_schema(db: str | Path) -> None:
    connection = store.connect(str(db))
    _ensure_schema(connection)
    connection.commit()
    connection.close()


def _content_hash(row: dict) -> str:
    content = "\n".join(str(row.get(field) or "") for field in (
        "title", "fig_title", "legend", "tags",
    ))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def enqueue_rows(
    db: str | Path,
    rows: list[dict],
    source_query: str,
    taxonomy_version: str = TAXONOMY_VERSION,
    annotator_version: str = ANNOTATOR_VERSION,
) -> int:
    """Queue unseen or stale search results and leave current jobs untouched."""
    connection = store.connect(str(db))
    _ensure_schema(connection)
    queued = 0
    for row in rows:
        figure_key = str(row.get("local_path") or "").strip()
        if not figure_key:
            continue
        content_hash = _content_hash(row)
        annotation = connection.execute(
            "SELECT 1 FROM figure_annotations "
            "WHERE figure_key=? AND level=? AND content_hash=? AND taxonomy_version=? "
            "AND annotator_version=?",
            (figure_key, LEVEL, content_hash, taxonomy_version, annotator_version),
        ).fetchone()
        job = connection.execute(
            "SELECT content_hash, taxonomy_version, annotator_version, status "
            "FROM annotation_jobs "
            "WHERE figure_key=?",
            (figure_key,),
        ).fetchone()

        if annotation or (
            job
            and job["content_hash"] == content_hash
            and job["taxonomy_version"] == taxonomy_version
            and job["annotator_version"] == annotator_version
            and job["status"] != "done"
        ):
            connection.execute(
                "UPDATE annotation_jobs SET seen_count=seen_count+1, "
                "source_query=?, updated_at=CURRENT_TIMESTAMP WHERE figure_key=?",
                (source_query, figure_key),
            )
            continue

        values = (
            figure_key,
            str(row.get("title") or ""),
            str(row.get("fig_title") or ""),
            str(row.get("legend") or ""),
            str(row.get("tags") or ""),
            source_query,
            content_hash,
            taxonomy_version,
            annotator_version,
        )
        connection.execute(
            "INSERT INTO annotation_jobs("
            "figure_key,title,fig_title,legend,tags,source_query,content_hash,taxonomy_version,"
            "annotator_version) VALUES(?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(figure_key) DO UPDATE SET "
            "title=excluded.title,fig_title=excluded.fig_title,legend=excluded.legend,"
            "tags=excluded.tags,source_query=excluded.source_query,"
            "content_hash=excluded.content_hash,taxonomy_version=excluded.taxonomy_version,"
            "annotator_version=excluded.annotator_version,"
            "status='pending',attempts=0,last_error=NULL,seen_count=annotation_jobs.seen_count+1,"
            "updated_at=CURRENT_TIMESTAMP",
            values,
        )
        queued += 1
    connection.commit()
    connection.close()
    return queued


def enqueue_search_results(db: str | Path, rows: list[dict], source_query: str) -> int:
    """Best-effort queueing that never makes an otherwise valid search fail."""
    try:
        return enqueue_rows(db, rows, source_query)
    except sqlite3.Error as exc:
        logging.getLogger(__name__).warning("annotation queue unavailable: %s", exc)
        return 0


def _weak_label(job: sqlite3.Row, catalog: Path) -> dict | None:
    text = "\n".join((job["title"], job["fig_title"], job["legend"], job["tags"]))
    intents = recommend.detect_intents(text)
    chart_tags = sorted(set(job["tags"].split()))
    candidates = []
    if catalog.is_file():
        for row in recommend.recommend(text, 3, catalog):
            candidates.append({
                "num": row["num"],
                "chart_type": row["chart_type"],
                "score": row["score"],
                "matched_intents": row["matched_intents"],
                "why": row["why"],
            })
    if not intents and not chart_tags and not candidates:
        return None

    confidence = 0.0
    if intents:
        confidence = max(confidence, 0.42)
    if chart_tags:
        confidence = max(confidence, 0.58)
    if candidates:
        confidence = max(confidence, min(0.75, 0.35 + 0.02 * candidates[0]["score"]))

    return {
        "labels": {
            "semantic_intents": intents,
            "caption_chart_tags": chart_tags,
            "candidate_profiles": candidates,
        },
        "evidence": {
            "source_fields": ["title", "fig_title", "legend", "tags"],
            "candidate_reasons": [row["why"] for row in candidates],
        },
        "confidence": round(confidence, 3),
    }


def run_worker(db: str | Path, budget: int, catalog: Path) -> dict:
    """Process at most ``budget`` pending jobs and persist L2 weak labels."""
    if budget < 0:
        raise ValueError("budget must be non-negative")
    connection = store.connect(str(db))
    _ensure_schema(connection)
    connection.execute(
        "UPDATE annotation_jobs SET status='pending', updated_at=CURRENT_TIMESTAMP "
        "WHERE status='processing' AND updated_at < datetime('now', '-1 hour')"
    )
    jobs = connection.execute(
        "SELECT * FROM annotation_jobs WHERE status='pending' "
        "ORDER BY seen_count DESC, updated_at ASC LIMIT ?",
        (budget,),
    ).fetchall()
    connection.commit()

    result = {"processed": 0, "labelled": 0, "no_signal": 0, "failed": 0}
    for job in jobs:
        claimed = connection.execute(
            "UPDATE annotation_jobs SET status='processing', attempts=attempts+1, "
            "updated_at=CURRENT_TIMESTAMP WHERE figure_key=? AND status='pending'",
            (job["figure_key"],),
        ).rowcount
        connection.commit()
        if not claimed:
            continue
        result["processed"] += 1
        try:
            label = _weak_label(job, catalog)
            if label is None:
                connection.execute(
                    "UPDATE annotation_jobs SET status='no_signal',last_error=NULL,"
                    "updated_at=CURRENT_TIMESTAMP WHERE figure_key=?",
                    (job["figure_key"],),
                )
                result["no_signal"] += 1
            else:
                connection.execute(
                    "INSERT INTO figure_annotations("
                    "figure_key,level,labels_json,evidence_json,confidence,content_hash,"
                    "taxonomy_version,annotator_version"
                    ") VALUES(?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(figure_key,level) DO UPDATE SET "
                    "labels_json=excluded.labels_json,evidence_json=excluded.evidence_json,"
                    "confidence=excluded.confidence,content_hash=excluded.content_hash,"
                    "taxonomy_version=excluded.taxonomy_version,"
                    "annotator_version=excluded.annotator_version,updated_at=CURRENT_TIMESTAMP",
                    (
                        job["figure_key"], LEVEL,
                        json.dumps(label["labels"], ensure_ascii=False),
                        json.dumps(label["evidence"], ensure_ascii=False),
                        label["confidence"], job["content_hash"], job["taxonomy_version"],
                        job["annotator_version"],
                    ),
                )
                connection.execute(
                    "UPDATE annotation_jobs SET status='done',last_error=NULL,"
                    "updated_at=CURRENT_TIMESTAMP WHERE figure_key=?",
                    (job["figure_key"],),
                )
                result["labelled"] += 1
        except Exception as exc:
            connection.execute(
                "UPDATE annotation_jobs SET status='failed',last_error=?,"
                "updated_at=CURRENT_TIMESTAMP WHERE figure_key=?",
                (str(exc)[:500], job["figure_key"]),
            )
            result["failed"] += 1
        connection.commit()
    connection.close()
    return result


def retry_failed(db: str | Path) -> int:
    connection = store.connect(str(db))
    _ensure_schema(connection)
    count = connection.execute(
        "UPDATE annotation_jobs SET status='pending',attempts=0,last_error=NULL,"
        "updated_at=CURRENT_TIMESTAMP WHERE status='failed'"
    ).rowcount
    connection.commit()
    connection.close()
    return count


def status(db: str | Path) -> dict:
    connection = store.connect(str(db))
    _ensure_schema(connection)
    counts = {
        row["status"]: row["n"]
        for row in connection.execute(
            "SELECT status,count(*) AS n FROM annotation_jobs GROUP BY status"
        )
    }
    try:
        total_figures = connection.execute(
            "SELECT count(*) FROM figures"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        total_figures = 0
    l2 = connection.execute(
        "SELECT count(*) FROM figure_annotations WHERE level=? AND taxonomy_version=? "
        "AND annotator_version=?",
        (LEVEL, TAXONOMY_VERSION, ANNOTATOR_VERSION),
    ).fetchone()[0]
    last_event = connection.execute(
        "SELECT max(updated_at) FROM annotation_jobs"
    ).fetchone()[0]
    seen = sum(counts.values())
    terminal = counts.get("done", 0) + counts.get("no_signal", 0) + counts.get("failed", 0)
    connection.close()
    return {
        "total_figures": total_figures,
        "seen_figures": seen,
        "pending": counts.get("pending", 0),
        "processing": counts.get("processing", 0),
        "done": counts.get("done", 0),
        "no_signal": counts.get("no_signal", 0),
        "failed": counts.get("failed", 0),
        "l2_annotations": l2,
        "library_coverage": round(l2 / total_figures, 6) if total_figures else 0.0,
        "queue_completion": round(terminal / seen, 6) if seen else 1.0,
        "last_event": last_event,
        "taxonomy_version": TAXONOMY_VERSION,
        "annotator_version": ANNOTATOR_VERSION,
    }


def attach_annotations(db: str | Path, rows: list[dict]) -> None:
    keys = [str(row.get("local_path") or "") for row in rows]
    keys = [key for key in keys if key]
    if not keys:
        return
    try:
        connection = store.connect(str(db))
        _ensure_schema(connection)
        placeholders = ",".join("?" for _ in keys)
        found = {
            row["figure_key"]: row
            for row in connection.execute(
                "SELECT * FROM figure_annotations WHERE level=? AND taxonomy_version=? "
                "AND annotator_version=? "
                f"AND figure_key IN ({placeholders})",
                (LEVEL, TAXONOMY_VERSION, ANNOTATOR_VERSION, *keys),
            )
        }
        connection.close()
    except sqlite3.Error as exc:
        logging.getLogger(__name__).warning("weak annotations unavailable: %s", exc)
        return
    for row in rows:
        annotation = found.get(str(row.get("local_path") or ""))
        if annotation and annotation["content_hash"] == _content_hash(row):
            row["weak_annotation"] = {
                "level": annotation["level"],
                "labels": json.loads(annotation["labels_json"]),
                "evidence": json.loads(annotation["evidence_json"]),
                "confidence": annotation["confidence"],
                "taxonomy_version": annotation["taxonomy_version"],
                "annotator_version": annotation["annotator_version"],
            }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process persistent caption weak-label jobs.")
    parser.add_argument("--db", type=Path, default=Path("figraph.db"))
    parser.add_argument("--catalog", type=Path, default=recommend.DEFAULT_CATALOG)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    if args.retry_failed:
        print(json.dumps({"retried": retry_failed(args.db)}, ensure_ascii=False))
    if not args.status and not args.retry_failed:
        run = run_worker(args.db, args.budget, args.catalog)
        print(json.dumps({"run": run, "status": status(args.db)}, ensure_ascii=False))
    else:
        print(json.dumps(status(args.db), ensure_ascii=False))


if __name__ == "__main__":
    main()
