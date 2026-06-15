# FigGraph

A searchable index over a folder of scientific figures — so an AI agent (or you)
can ask *"what's the best way to visualize this?"* and get real published
exemplars back, instead of guessing.

**codegraph is to your code what FigGraph is to your figures.**

| codegraph | FigGraph |
|---|---|
| parses code → symbols | reads figures → records (image + legend + metadata) |
| SQLite graph of symbols | SQLite store + FTS5 over legends |
| `codegraph_search` | `figraph search` |
| `.codegraph/` in the repo | the index lives next to your figures |

## How it works

A scientific figure's hardest knowledge isn't the plotting call — it's knowing
which chart type, layout, and encoding a top journal would use. That knowledge is
already in thousands of published figures. FigGraph makes them queryable.

The key idea: **every Nature figure ships with its legend** — a precise,
human-written description. FigGraph indexes those legends with SQLite FTS5, so
search is accurate without needing a vision model. You search by content or form,
get back the matching figures' local paths, and open the ones worth emulating.

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Use

```bash
# 1. populate a folder with figures + legends (Nature flagship + branded journals)
python -m figraph.scrape --journals nature nmeth nm --years 2024 --out figures

# 2. build the search index from the scraped metadata
python -m figraph.index --meta figures/metadata.jsonl --db figraph.db

# 3. search — returns ranked figures with their local paths
python -m figraph.search "kaplan-meier survival hazard ratio" -k 8
python -m figraph.search "single-cell umap clusters" --tag umap-tsne
```

`scrape` is resumable and rate-limited (it appends one JSONL row per figure and
skips articles it has already fetched). Run it again with more journals or years
and it only fetches what's new.

### Keeping it fresh

Nature keeps publishing, so refresh on a schedule. This is the remote-source
analogue of codegraph's auto-reindex: a website can't be watched with inotify, so
`update` polls for newly-published articles and rebuilds the index.

```bash
python -m figraph.update            # fetch new articles for recent years, reindex
```

Wire it to cron for hands-off updates, e.g. every Monday at 03:00:

```cron
0 3 * * 1  cd /path/to/FigGraph && .venv/bin/python -m figraph.update >> update.log 2>&1
```

## Scope

The scraper covers Nature's flagship plus its branded research journals (Methods,
Medicine, Materials, Genetics, Neuroscience, Machine Intelligence, …) — down to,
but not including, Nature Communications. Journal codes live in
`figraph/scrape.py`.

## What's in git, what isn't

The repo is the tool. Scraped images, the JSONL metadata, and the SQLite index are
large, regenerable, local artifacts — they are git-ignored. FigGraph indexes
whatever folder you point it at; it ships no figures, the same way codegraph ships
no code.

## Roadmap

- **Now:** scrape → legend-based FTS5 index → search CLI → scheduled `update`.
- **Later:** pluggable vision captioner (local VLM / API) so *caption-less* folders
  become searchable too; a local folder watcher for live re-indexing; CLIP / BiomedCLIP
  embeddings for visual-similarity search; an MCP server + Claude Code plugin so an
  agent gets native `figraph_*` tools; more open-access source adapters.

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full design.

## License

MIT
