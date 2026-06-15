<div align="center">

# FigGraph

**codegraph, but for your figures.**

Ask *"what's the best way to plot this?"* — and get real, published figures back,
instead of guessing.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#roadmap)
[![Built for agents](https://img.shields.io/badge/built%20for-AI%20agents-8A2BE2.svg)](#use-it-from-an-agent)

[Why](#why) · [Quickstart](#quickstart) · [How it works](#how-it-works) · [Roadmap](#roadmap)

</div>

---

## Why

The hard part of making a scientific figure is rarely the plotting call. It's knowing
*what good looks like* — which chart type, layout, and encoding a strong paper would use
for this kind of result. That knowledge already exists, scattered across thousands of
published figures. But those figures sit in folders with no structure and no way to ask
*"show me the best survival-curve panel I have."*

FigGraph turns a pile of figure files into a queryable index. Point it at a folder, then
search by what you want to show — and open the exemplars worth emulating.

It is, deliberately, the figure-domain twin of [codegraph](https://github.com/): your
code has a searchable index of every symbol; your figures should have one too.

| codegraph | FigGraph |
| --- | --- |
| parses code → symbols | reads figures → records (image + caption + metadata) |
| SQLite knowledge graph | SQLite store + FTS5 over captions |
| `codegraph_search` | `figraph search` |
| file watcher re-indexes on save | scheduled `update` re-indexes on new publications |
| `.codegraph/` lives in the repo | the index lives next to your figures |

## Quickstart

```bash
git clone https://github.com/FFI-Research-Institute/FigGraph.git
cd FigGraph
pip install -e .
```

```bash
# 1. fill a folder with figures + captions (bundled Nature adapter)
figraph scrape --journals nature nmeth nm --years 2024 --out figures

# 2. build the search index
figraph index

# 3. search — get back ranked figures and their local paths
figraph search "kaplan-meier survival hazard ratio" -k 8
figraph search "single-cell umap clusters" --tag umap-tsne
```

A search returns the figures whose captions best match, ready to open:

```
1. figures/nature/2024/s41586-024-08334-8_Fig1.png  [line scatter heatmap umap-tsne]
   Nature 2024  ·  Spatial transcriptomic clocks reveal cell proximity effects
   Fig. 1: Spatially resolved single-cell transcriptomic profiling of the brain ...
```

## How it works

The trick is that **a scientific figure usually ships with its caption** — a precise,
human-written description of exactly what it shows. FigGraph indexes those captions with
SQLite FTS5, so search is accurate *without* needing a vision model. You search by content
or by chart type; you get back real figures' local paths; you open the ones worth copying.

The bundled adapter fetches figures from Nature's flagship and branded research journals
(Methods, Medicine, Materials, Genetics, Neuroscience, Machine Intelligence, …), each with
its full legend. Folders of *caption-less* images — your own screenshots and exports —
become searchable once the vision captioner lands (see [Roadmap](#roadmap)).

## Keeping it fresh

New papers publish constantly, so refresh on a schedule. This is the remote-source
analogue of codegraph's auto-reindex — a website can't be watched with `inotify`, so
`update` polls for new articles and rebuilds the index in one step:

```bash
figraph update                 # fetch new articles for recent years, then reindex
```

Wire it to cron for hands-off updates, e.g. every Monday at 03:00:

```cron
0 3 * * 1  cd /path/to/FigGraph && figraph update >> update.log 2>&1
```

## Use it from an agent

FigGraph is built to be called by AI coding agents while they make figures: the agent
searches the index for published exemplars, looks at the top matches, and grounds its plot
in what actually works. A native MCP server (so an agent gets `figraph_*` tools, the way
codegraph exposes `codegraph_*`) is on the roadmap; today, agents call the `figraph search`
CLI directly.

## Responsible use

FigGraph stores **no figures** — it indexes a folder you already have, the same way
codegraph ships no code. The bundled Nature adapter is for personal research use: it
fetches publicly-rendered figures over plain HTTP at a polite, rate-limited pace and writes
only to your local disk. Respect each publisher's terms, and prefer open-access sources
where you can.

## Roadmap

- **Now** — `scrape` → caption-based FTS5 index → `search` → scheduled `update`.
- **Next** — pluggable vision captioner (local VLM / API) so caption-less folders become
  searchable; a local folder watcher for live re-indexing; CLIP / BiomedCLIP embeddings for
  visual-similarity search; an MCP server + Claude Code plugin; more open-access adapters
  (PLOS, eLife, bioRxiv).

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full design.

## Contributing

Issues and PRs welcome — new source adapters, captioner backends, and chart-type tagging
rules are especially useful. Keep changes small and focused.

## Star History

<a href="https://star-history.com/#FFI-Research-Institute/FigGraph&Date">
  <img src="https://api.star-history.com/svg?repos=FFI-Research-Institute/FigGraph&type=Date" alt="Star History Chart" width="600">
</a>

## License

[MIT](LICENSE)
