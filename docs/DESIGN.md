# FigGraph — Design

> A searchable index over any folder of scientific figures, exposed to AI agents.
> **codegraph is to your code what FigGraph is to your figures.**

## Problem

When an AI agent (or a researcher) needs to make a plot, the hard part is rarely the
matplotlib call — it is knowing *what good looks like*: which chart type, layout, and
encoding a top journal would use for this kind of result. That knowledge lives in
thousands of already-published figures, but those figures sit in messy folders with no
structure, no captions, and no way to ask "show me the best survival-curve panel I have."

FigGraph turns a pile of image files into a queryable index, so an agent can ground its
figure-making in real exemplars instead of generating blind.

## The codegraph parallel

FigGraph is deliberately the figure-domain analogue of codegraph. The shapes line up
one-to-one, which keeps the mental model and the UX familiar:

| codegraph | FigGraph |
|---|---|
| tree-sitter parses code → symbols | captioner reads images → figure records |
| SQLite knowledge graph of symbols & edges | SQLite store: figures + FTS5(captions) + optional vectors |
| file watcher re-indexes on save | folder watcher re-indexes on add/remove *(v2)* |
| `codegraph_*` MCP tools (search/node/impact) | `figraph_*` MCP tools (search/get/status) |
| `codegraph init -i` | `figraph index <dir>` |
| `.codegraph/` index dir in the repo | `.figraph/` index dir in the folder |

The index is **local and in-place**: point FigGraph at a folder, it writes a `.figraph/`
directory next to the images. Nothing is copied or uploaded.

## Scope & non-goals

**Core (the point):** index an arbitrary local folder of figures and make it searchable
by an agent. Works regardless of where the images came from.

**Incidental:** a `fetch` adapter that can *populate* a folder by scraping a source
(Nature first, ported from slandarer's MATLAB script). This is one optional way to fill a
folder — not the product.

**Copyright posture:** the tool ships **no figures**. It indexes whatever folder you give
it — exactly like codegraph indexing your private code. The public repo contains only
code. The `fetch` adapter is documented as personal-research-use, rate-limited, and
TOS-respecting; the default/blessed sources lean open-access (PLOS, eLife, bioRxiv).

**Not in scope:** generating figures, editing images, a hosted service, a web UI.

## Architecture

Two decoupled layers, each independently testable.

### 1. Ingest + index (`figraph index <dir>`)

Walk the folder for image files (`.png .jpg .jpeg .tif .webp`, SVG/PDF later). For each
image, build a **figure record**:

- **Text signals (free):** filename, relative path, any sidecar caption (`<name>.txt` /
  `<name>.json`), embedded metadata, and — when present — a source caption (e.g. a Nature
  figure legend captured by the `fetch` adapter).
- **Vision signal (the quality lever):** a generated description + chart-type tags, from a
  **pluggable captioner**. This is what makes caption-less images findable.

Records land in a SQLite store with an FTS5 virtual table over the combined text.
Re-running `index` is incremental: unchanged files (by path + mtime + size hash) are
skipped.

### 2. Query (`figraph search` / MCP)

Rank records by FTS5 BM25 over `caption + tags + filename`. Return image path, generated
description, chart-type tags, source (if known), and score. An agent then `Read`s the top
paths to see the actual figures and pick the best template to emulate.

## Pluggable captioner

A single `Captioner` interface with graceful degradation, so the tool runs anywhere:

| backend | when | notes |
|---|---|---|
| `local` *(default if GPU)* | local VLM via transformers (Florence-2 / Qwen2-VL-2B) | free, private, batch-friendly; needs model weights (~1–4 GB) |
| `api` | Claude / GPT vision | trivial setup, no local resources; per-image token cost, needs network |
| `none` | text-only | zero ML; only filename / existing captions are indexed |

Selection is config-driven with auto-fallback: prefer `local` when CUDA is available, else
`api` when a key is set, else `none` — and tell the user how to upgrade. On dl205 the
default is `local` (2× TITAN V, 12 GB).

## Chart-type taxonomy

A small controlled vocabulary the captioner tags each figure with, so searches can filter
by form as well as content: `bar, grouped-bar, line, scatter, box, violin, heatmap,
network, umap-tsne, survival, forest, volcano, microscopy, schematic, flowchart, map,
multi-panel, …`. v1 derives tags from the caption/description via keyword rules; a
dedicated classifier is a later refinement.

## Data model (SQLite)

```
figures(id, path, mtime, size_hash, source, caption, description, tags, indexed_at)
figures_fts  -- FTS5(caption, description, tags, filename) external-content over figures
-- v2: embeddings(figure_id, vector)  for CLIP visual/semantic search
```

## Distribution: Claude Code plugin

The repo ships a Claude Code **plugin** folder that registers the `figraph` MCP server, so
the agent gets native `figraph_search` / `figraph_get` / `figraph_status` tools after a
single `/plugin install` — the same way codegraph's tools appear. The MCP server is a thin
wrapper over the same query layer the CLI uses.

## CLI surface (v1)

```
figraph index <dir>        # build/refresh the .figraph index for a folder
figraph search <query>     # rank figures by relevance (-k N, --tag, --json)
figraph status             # index size, backend, coverage
figraph serve              # run the MCP server (stdio)
figraph fetch nature ...   # (incidental) populate a folder from Nature
```

## Roadmap

- **v1 (this build):** `index` / `search` / `status`, pluggable captioner, FTS5, MCP
  server, Claude Code plugin, polished README + MIT license, Nature `fetch` adapter.
- **v2:** `figraph watch` folder daemon (live re-index); CLIP embeddings + `figraph
  similar` (visual / text→image search); perceptual-hash dedup; more open-access adapters.

## Repository layout

```
FigGraph/
├── README.md                 # polished, public-facing
├── LICENSE                   # MIT
├── pyproject.toml
├── .gitignore                # ignores .figraph/, model weights, scraped images
├── docs/DESIGN.md            # this file
├── figraph/
│   ├── cli.py                # index / search / status / serve / fetch
│   ├── store.py              # SQLite schema + FTS5
│   ├── index.py              # folder walk + incremental ingest
│   ├── search.py             # query → ranked results
│   ├── captioner/            # base + local_vlm + api + nullcap
│   ├── mcp_server.py         # figraph_* MCP tools
│   └── adapters/nature.py    # incidental scraper (slandarer port)
├── plugin/.claude-plugin/    # Claude Code plugin manifest + MCP registration
└── tests/
```

## Decisions locked

- Name **FigGraph** (CLI `figraph`); host **private** under `FFI-Research-Institute`, flip
  public when v1 is stable.
- Core is the **local-folder index**; the scraper is an incidental, copyright-safe adapter.
- Captioner **pluggable**, `local` VLM default on dl205.
- Scope **Nature flagship + Nature-branded research journals, 2023–2025** for QQ's own
  library (no Nature Communications); the tool itself is source-agnostic.
