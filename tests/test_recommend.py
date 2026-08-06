import json
import tempfile
import unittest
from pathlib import Path

from figraph import recommend


class RecommendTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.catalog = Path(self.tempdir.name) / "router.jsonl"
        rows = [
            {
                "num": "017", "chart_type": "raincloud plot", "display_name": "云雨图",
                "folder": "017_云雨图", "aliases": ["raincloud", "云雨图", "plot"],
                "intents": ["comparison", "distribution", "raw_observations"],
                "intent_terms": ["全部观测"], "use_when": "compare distributions",
                "avoid_when": "small n", "data_shape": ["continuous", "groups"],
                "claim_roles": ["heterogeneity"], "search_query": "017 raincloud",
                "folder_path": "figures/017", "r_script": "017.R",
                "annotation_level": "L1_curated_folder", "confidence": 0.88,
            },
            {
                "num": "066", "chart_type": "time-series line", "display_name": "折线图",
                "folder": "066_折线图", "aliases": ["line", "折线图"],
                "intents": ["time"], "intent_terms": ["时序趋势"],
                "use_when": "show trends", "avoid_when": "unordered observations",
                "data_shape": ["ordered time"], "claim_roles": ["temporal dynamics"],
                "search_query": "066 line", "folder_path": "figures/066",
                "r_script": "066.R", "annotation_level": "L1_curated_folder",
                "confidence": 0.88,
            },
            {
                "num": "019", "chart_type": "Sankey", "display_name": "桑基图",
                "folder": "019_桑基图", "aliases": ["sankey", "桑基图"],
                "intents": ["flow", "composition"], "intent_terms": ["来源去向"],
                "use_when": "show flows", "avoid_when": "non-conserved flow",
                "data_shape": ["source-target"], "claim_roles": ["flow"],
                "search_query": "019 sankey", "folder_path": "figures/019",
                "r_script": "019.R", "annotation_level": "L1_curated_folder",
                "confidence": 0.88,
            },
            {
                "num": "036", "chart_type": "forest plot", "display_name": "森林图",
                "folder": "036_森林图", "aliases": ["forest", "森林图"],
                "intents": ["comparison", "ranking", "uncertainty"],
                "intent_terms": ["效应量区间"], "use_when": "compare effects",
                "avoid_when": "p-values only", "data_shape": ["effects", "intervals"],
                "claim_roles": ["effect comparison"], "search_query": "036 forest",
                "folder_path": "figures/036", "r_script": "036.R",
                "annotation_level": "L1_curated_folder", "confidence": 0.88,
            },
            {
                "num": "029", "chart_type": "Table 1", "display_name": "基线表",
                "folder": "029_基线表", "aliases": ["table", "one"],
                "intents": ["table"], "intent_terms": ["baseline characteristics"],
                "use_when": "describe a cohort", "avoid_when": "showing a trend",
                "data_shape": ["cohort characteristics"],
                "claim_roles": ["baseline description"],
                "search_query": "029 table one", "folder_path": "figures/029",
                "r_script": "029.R", "annotation_level": "L1_curated_folder",
                "confidence": 0.88,
            },
        ]
        self.catalog.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_distribution_question_prefers_raincloud(self):
        rows = recommend.recommend("比较三组分布并保留全部观测", 3, self.catalog)
        self.assertEqual(rows[0]["num"], "017")

    def test_flow_question_prefers_sankey(self):
        rows = recommend.recommend("展示类别的来源去向和流量", 3, self.catalog)
        self.assertEqual(rows[0]["num"], "019")

    def test_effect_interval_question_prefers_forest(self):
        rows = recommend.recommend("比较多个模型效应量和置信区间", 3, self.catalog)
        self.assertEqual(rows[0]["num"], "036")

    def test_ascii_aliases_do_not_match_inside_words(self):
        rows = recommend.recommend("baseline uncertainty", 3, self.catalog)
        self.assertEqual(rows[0]["num"], "036")

    def test_generic_plot_alias_does_not_override_intent(self):
        rows = recommend.recommend("plot uncertainty", 3, self.catalog)
        self.assertEqual(rows[0]["num"], "036")

    def test_generic_one_alias_does_not_create_table_candidate(self):
        rows = recommend.recommend("one source-to-target flow", 5, self.catalog)
        self.assertNotIn("029", [row["num"] for row in rows])


if __name__ == "__main__":
    unittest.main()
