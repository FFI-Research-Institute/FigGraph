# FigGraph — Claude Code plugin

Gives your agent native `figraph_recommend` / `figraph_search` / `figraph_status` tools over a local
figure index (the way codegraph exposes `codegraph_*`).

## Install

```bash
# the MCP server lives in the figraph package
pip install "figraph[mcp] @ git+https://github.com/FFI-Research-Institute/FigGraph.git"
```

```text
/plugin marketplace add FFI-Research-Institute/FigGraph
/plugin install figraph
```

The server reads the index from your project: `FIGRAPH_DB` (default
`$CLAUDE_PROJECT_DIR/figraph.db`) and `FIGRAPH_DIR` (default
`$CLAUDE_PROJECT_DIR/figures`). Build that index first with `figraph index`.

## Tools

- `figraph_recommend(question, k=5)` — chart families ranked from the scientific question and evidence role.
- `figraph_search(query, k=10, tag=None)` — ranked figures with local image paths.
- `figraph_status()` — index location and size.
