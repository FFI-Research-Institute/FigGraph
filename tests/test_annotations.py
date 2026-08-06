import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from figraph import annotate


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.db = root / "figraph.db"
        connection = sqlite3.connect(self.db)
        connection.execute(
            "CREATE TABLE figures(id INTEGER PRIMARY KEY, local_path TEXT)"
        )
        connection.executemany(
            "INSERT INTO figures(local_path) VALUES(?)",
            [("nature/flow.png",), ("nature/no-signal.png",)],
        )
        connection.commit()
        connection.close()
        self.catalog = root / "router.jsonl"
        row = {
            "num": "019", "chart_type": "Sankey/alluvial diagram",
            "display_name": "桑基图", "folder": "019_桑基图",
            "aliases": ["sankey", "alluvial"],
            "intents": ["flow", "composition"],
            "intent_terms": ["transition flow"],
            "use_when": "show source-target flow",
            "avoid_when": "flow is not conserved",
            "data_shape": ["source-target flows"],
            "claim_roles": ["transition pathways"],
            "search_query": "019 sankey alluvial flow",
            "folder_path": "figures/019", "r_script": "figures/019.R",
            "annotation_level": "L1_curated_folder", "confidence": 0.88,
        }
        self.catalog.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_enqueue_is_idempotent_and_counts_repeated_use(self):
        rows = [{
            "local_path": "nature/flow.png", "title": "Transition flow",
            "fig_title": "", "legend": "Source to target migration flow.",
            "tags": "",
        }]
        self.assertEqual(annotate.enqueue_rows(self.db, rows, "first"), 1)
        self.assertEqual(annotate.enqueue_rows(self.db, rows, "second"), 0)
        connection = sqlite3.connect(self.db)
        seen_count = connection.execute(
            "SELECT seen_count FROM annotation_jobs"
        ).fetchone()[0]
        connection.close()
        self.assertEqual(seen_count, 2)

    def test_worker_separates_l2_from_no_signal(self):
        rows = [
            {
                "local_path": "nature/flow.png", "title": "Transition flow",
                "fig_title": "", "legend": "Source to target migration flow.",
                "tags": "",
            },
            {
                "local_path": "nature/no-signal.png", "title": "Supplementary panel",
                "fig_title": "", "legend": "Representative observations are shown.",
                "tags": "",
            },
        ]
        annotate.enqueue_rows(self.db, rows, "query")
        result = annotate.run_worker(self.db, 10, self.catalog)
        self.assertEqual(result, {
            "processed": 2, "labelled": 1, "no_signal": 1, "failed": 0,
        })
        state = annotate.status(self.db)
        self.assertEqual(state["l2_annotations"], 1)
        self.assertEqual(state["no_signal"], 1)
        annotate.attach_annotations(self.db, rows)
        self.assertEqual(rows[0]["weak_annotation"]["level"], annotate.LEVEL)
        self.assertNotIn("weak_annotation", rows[1])

    def test_taxonomy_change_requeues_a_completed_job(self):
        row = {
            "local_path": "nature/flow.png", "title": "Transition flow",
            "fig_title": "", "legend": "Source to target migration flow.",
            "tags": "",
        }
        annotate.enqueue_rows(self.db, [row], "query")
        annotate.run_worker(self.db, 1, self.catalog)
        queued = annotate.enqueue_rows(
            self.db, [row], "query", taxonomy_version="visual-intent-v2",
        )
        self.assertEqual(queued, 1)
        self.assertEqual(annotate.status(self.db)["pending"], 1)

    def test_annotator_change_requeues_a_completed_job(self):
        row = {
            "local_path": "nature/flow.png", "title": "Transition flow",
            "fig_title": "", "legend": "Source to target migration flow.",
            "tags": "",
        }
        annotate.enqueue_rows(self.db, [row], "query")
        annotate.run_worker(self.db, 1, self.catalog)
        queued = annotate.enqueue_rows(
            self.db, [row], "query", annotator_version="caption-rules-v2",
        )
        self.assertEqual(queued, 1)
        self.assertEqual(annotate.status(self.db)["pending"], 1)


if __name__ == "__main__":
    unittest.main()
