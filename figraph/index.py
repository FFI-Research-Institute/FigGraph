"""Build the FTS5 index from scraped metadata, tagging each figure's chart type.

    python -m figraph.index --meta figures/metadata.jsonl --db figraph.db
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from figraph import store

# chart-type tag -> legend substrings that imply it. Cheap, legend-only
# heuristic; the full legend is in FTS anyway, so tags are a bonus filter.
TAG_RULES = {
    "grouped-bar": ["grouped bar", "stacked bar"],
    "bar": ["bar chart", "bar plot", "barplot", "bar graph"],
    "line": ["line plot", "line chart", "time course", "trajectory", "over time"],
    "scatter": ["scatter plot", "scatterplot", "scatter diagram"],
    "box": ["box plot", "boxplot", "box-and-whisker"],
    "violin": ["violin plot"],
    "heatmap": ["heatmap", "heat map"],
    "histogram": ["histogram"],
    "survival": ["kaplan", "survival curve", "survival analysis", "hazard ratio"],
    "forest": ["forest plot"],
    "volcano": ["volcano plot"],
    "umap-tsne": ["umap", "t-sne", "tsne", "t-distributed"],
    "tree": ["phylogenetic tree", "phylogeny", "dendrogram"],
    "network": ["network diagram", "interaction network", "co-expression network"],
    "blot": ["western blot", "immunoblot", "gel electrophoresis"],
    "cytometry": ["flow cytometry", "facs", "gating"],
    "microscopy": ["micrograph", "microscopy", "fluorescence imag", "confocal",
                   "immunofluoresc", "scanning electron", "transmission electron"],
    "map": ["geographic map", "world map", "spatial map"],
    "schematic": ["schematic", "workflow", "pipeline", "study design",
                  "experimental design"],
}


def chart_tags(legend: str) -> str:
    low = legend.lower()
    hits = [tag for tag, kws in TAG_RULES.items() if any(k in low for k in kws)]
    return " ".join(hits)


def build_index(meta: Path, db: Path) -> int:
    rows = []
    for line in meta.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        r["tags"] = chart_tags(r.get("legend", ""))
        rows.append(r)
    n = store.build(str(db), rows)
    tagged = sum(1 for r in rows if r["tags"])
    print(f"indexed {n} figures into {db}  ({tagged} got a chart-type tag)")
    return n


def main():
    ap = argparse.ArgumentParser(description="Build figraph FTS5 index.")
    ap.add_argument("--meta", type=Path, default=Path("figures/metadata.jsonl"))
    ap.add_argument("--db", type=Path, default=Path("figraph.db"))
    a = ap.parse_args()
    build_index(a.meta, a.db)


if __name__ == "__main__":
    main()
