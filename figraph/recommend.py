"""Recommend chart families from a scientific communication question."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


DEFAULT_CATALOG = Path(os.environ.get(
    "FIGRAPH_ROUTER_CATALOG",
    "figures/collections/top_journal_reproductions_80/chart_router.jsonl",
))

GENERIC_ALIASES = {"analysis", "chart", "diagram", "one", "plot"}

INTENT_PATTERNS = {
    "comparison": ["比较", "对比", "差异", "哪个更好", "compare", "difference"],
    "distribution": ["分布", "密度", "异质性", "变异", "distribution", "density", "heterogeneity"],
    "relationship": ["关系", "相关", "关联", "association", "correlation", "relationship"],
    "composition": ["组成", "构成", "占比", "比例", "composition", "proportion", "share"],
    "time": ["时间", "趋势", "随时间", "时序", "轨迹", "over time", "temporal", "trajectory"],
    "flow": ["流向", "转移", "来源去向", "迁移", "传播", "扩散", "flow", "transition", "migration"],
    "network": ["网络", "相互作用", "通讯", "连接", "network", "interaction", "communication"],
    "hierarchy": ["层级", "嵌套", "父子", "hierarchy", "nested"],
    "spatial": ["空间", "地理", "地图", "区域", "spatial", "geographic", "map"],
    "paired_change": ["配对", "前后", "变化方向", "before after", "paired", "change from baseline"],
    "uncertainty": ["不确定性", "误差", "置信区间", "可信区间", "uncertainty", "error", "confidence interval"],
    "ranking": ["排名", "排序", "效应量", "候选筛选", "ranking", "effect size", "screening"],
    "classification": ["分类", "诊断", "预测类别", "classifier", "classification", "diagnostic"],
    "threshold": ["阈值", "筛选", "净获益", "coverage", "threshold", "net benefit", "selective"],
    "survival": ["生存", "风险比", "删失", "survival", "hazard", "censoring"],
    "set_overlap": ["交集", "重叠", "集合", "overlap", "intersection", "set"],
    "enrichment": ["富集", "通路", "基因集", "enrichment", "pathway", "GSEA"],
    "dimension_reduction": ["聚类", "降维", "细胞状态", "cluster", "embedding", "UMAP", "t-SNE"],
    "process": ["流程", "工作流", "阶段", "步骤", "workflow", "pipeline", "process"],
    "mutation": ["突变", "基因事件", "mutation", "oncoprint"],
    "table": ["基线特征", "队列特征", "table 1", "demographic", "baseline characteristics"],
    "multivariate": ["多变量", "高维", "矩阵", "multivariate", "high-dimensional", "matrix"],
    "circular": ["环形", "径向", "周期", "circular", "radial", "cyclic"],
    "raw_observations": ["全部观测", "所有点", "原始点", "个体点", "raw observations", "individual points"],
    "anatomy": ["器官", "解剖", "身体区域", "organ", "anatomy"],
}


def _contains_term(text: str, term: str) -> bool:
    """Match CJK phrases by substring and ASCII terms on word boundaries."""
    term = term.lower().strip()
    if not term:
        return False
    if term.isascii():
        return re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])",
            text,
        ) is not None
    return term in text


def load_catalog(path: Path = DEFAULT_CATALOG) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(
            f"chart router catalog not found: {path}; set FIGRAPH_ROUTER_CATALOG "
            "or pass --catalog"
        )
    rows = [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"chart router catalog is empty: {path}")
    return rows


def detect_intents(question: str) -> list[str]:
    low = question.lower()
    return [
        intent for intent, patterns in INTENT_PATTERNS.items()
        if any(_contains_term(low, pattern) for pattern in patterns)
    ]


def recommend(question: str, k: int = 5, catalog: Path = DEFAULT_CATALOG) -> list[dict]:
    low = question.lower().strip()
    if not low:
        return []
    detected = set(detect_intents(question))
    ranked = []
    for row in load_catalog(catalog):
        score = 0
        reasons = []
        direct_fields = [row.get("display_name", ""), row.get("chart_type", "")]
        direct_fields.extend(row.get("aliases", []))
        direct = [
            text for text in direct_fields
            if len(text) > 1
            and text.lower() not in GENERIC_ALIASES
            and _contains_term(low, text)
        ]
        if direct:
            score += 12 * len(set(direct))
            reasons.append("名称/别名: " + ", ".join(dict.fromkeys(direct)))

        matched_intents = sorted(detected.intersection(row.get("intents", [])))
        if matched_intents:
            score += 5 * len(matched_intents)
            reasons.append("表达任务: " + ", ".join(matched_intents))

        matched_terms = [
            term for term in row.get("intent_terms", [])
            if _contains_term(low, term)
        ]
        if matched_terms:
            score += 3 * len(matched_terms)
            reasons.append("问题短语: " + ", ".join(matched_terms))

        if score:
            ranked.append({
                "score": score,
                "num": row["num"],
                "chart_type": row["chart_type"],
                "display_name": row["display_name"],
                "folder": row["folder"],
                "matched_intents": matched_intents,
                "why": "; ".join(reasons),
                "use_when": row["use_when"],
                "avoid_when": row["avoid_when"],
                "data_shape": row["data_shape"],
                "claim_roles": row["claim_roles"],
                "search_query": row["search_query"],
                "folder_path": row["folder_path"],
                "r_script": row["r_script"],
                "annotation_level": row["annotation_level"],
                "confidence": row["confidence"],
            })
    ranked.sort(key=lambda row: (-row["score"], row["num"]))
    return ranked[:max(0, k)]


def main():
    parser = argparse.ArgumentParser(
        description="Recommend chart families from the question a figure must answer."
    )
    parser.add_argument("question")
    parser.add_argument("-k", type=int, default=5, help="number of recommendations")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = recommend(args.question, args.k, args.catalog)
    if args.json:
        print(json.dumps({
            "question": args.question,
            "detected_intents": detect_intents(args.question),
            "recommendations": rows,
        }, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("(no chart recommendation; clarify the comparison, data shape or evidence role)")
        return
    print("detected intents:", ", ".join(detect_intents(args.question)) or "none")
    for index, row in enumerate(rows, 1):
        print(f"{index}. {row['num']} {row['display_name']} [{row['chart_type']}] score={row['score']}")
        print(f"   why: {row['why']}")
        print(f"   use when: {row['use_when']}")
        print(f"   avoid when: {row['avoid_when']}")
        print(f"   search: figraph search \"{row['search_query']}\"")


if __name__ == "__main__":
    main()
