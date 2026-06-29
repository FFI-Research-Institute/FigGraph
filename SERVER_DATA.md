# Server-Only Data — nature_fig (FigGraph)

This repository contains **code and lightweight files only**. The figure database
and the Python virtualenv are kept on the server and excluded from git.

- Server: `dl205` (`120.79.191.248`)
- Repo path on server: `/data/qqzhang/project/nature_fig`
- Approx. size on server: `42G`
- GitHub: `git@github.com:FFI-Research-Institute/FigGraph.git`

## Kept on the server (not in git)

- `figraph.db` — SQLite FTS5 figure index (~140 MB)
- `.venv/` — Python environment (rebuild with `requirements.txt` / `pyproject.toml`)
- scraped figure images and intermediate crawl outputs

## Fetching data to a fresh clone

After cloning the code from GitHub (replace `dl205` with your SSH host for the server):

```
rsync -avP dl205:/data/qqzhang/project/nature_fig/figraph.db ./figraph.db
```

Rebuild the environment locally instead of copying `.venv/`.
