"""Scrape figures + legends + metadata from nature.com over plain HTTP.

Ported from slandarer's MATLAB approach: walk a journal's research-articles
listing year by year, open each article, pull every main figure's high-res PNG
plus its full legend. Resumable and rate-limited.

One JSONL row is written per figure to <out>/metadata.jsonl:
    {journal, year, article_id, doi, title, fig_num, fig_title, legend,
     image_url, local_path}

Usage:
    python -m figraph.scrape --journals nature --years 2024 --pages 1 --out figures
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import httpx
import lxml.html

# nature.com journal code -> display name. Nature flagship + Nature-branded
# research journals down to (but excluding) Nature Communications. Codes for the
# sub-journals are verified empirically before the full run (a wrong code yields
# an empty listing, which is easy to catch).
# Nature flagship + Nature-branded research journals with 2024 JCR IF >= 20
# ("大子刊"), plus two sub-20 keepers for the AI4Science route: Nature Machine
# Intelligence (~18, the AI-for-science flagship) and Nature Neuroscience (19.5,
# brain imaging). Already-scraped Nature Physics (~17) is kept too.
JOURNALS = {
    "nature": "Nature",
    "nmeth": "Nature Methods",
    "nbt": "Nature Biotechnology",
    "nm": "Nature Medicine",
    "ng": "Nature Genetics",
    "nmat": "Nature Materials",
    "nnano": "Nature Nanotechnology",
    "nphoton": "Nature Photonics",
    "nphys": "Nature Physics",
    "nchem": "Nature Chemistry",
    "ni": "Nature Immunology",
    "natmachintell": "Nature Machine Intelligence",
    "neuro": "Nature Neuroscience",
    "nenergy": "Nature Energy",
    "natcatal": "Nature Catalysis",
    "nclimate": "Nature Climate Change",
    "natsustain": "Nature Sustainability",
    "natcancer": "Nature Cancer",
}

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ID_RE = re.compile(r"/articles/(s\d{5}-\d{3}-\d{4,6}-[0-9a-z]+)")
FIGNUM_RE = re.compile(r"_Fig(\d+)_HTML", re.I)


def _get(client: httpx.Client, url: str, *, binary: bool = False, retries: int = 3):
    for attempt in range(retries):
        try:
            r = client.get(url)
            r.raise_for_status()
            return r.content if binary else r.text
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def hires(src: str) -> str:
    """Turn a thumbnail image URL into the full-resolution one."""
    if src.startswith("//"):
        src = "https:" + src
    return re.sub(r"/(lw|m)\d+/", "/full/", src, count=1)


def iter_article_ids(client, journal, year, max_pages):
    """Yield article ids from a journal's research-articles listing for a year."""
    seen = set()
    page = 1
    while max_pages is None or page <= max_pages:
        url = (f"https://www.nature.com/{journal}/research-articles"
               f"?year={year}&page={page}")
        try:
            html = _get(client, url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                break  # Nature 404s when paging past the last page (not empty)
            raise
        ids = [i for i in ID_RE.findall(html) if i not in seen]
        if not ids:
            break
        for i in ids:
            seen.add(i)
            yield i
        page += 1
        time.sleep(0.5)


def parse_article(client, article_id):
    """Return (title, doi, [figure dicts]) for one article."""
    html = _get(client, f"https://www.nature.com/articles/{article_id}")
    doc = lxml.html.fromstring(html)

    def meta(name):
        v = doc.xpath(f'//meta[@name="{name}"]/@content')
        return v[0] if v else None

    title = meta("citation_title") or ""
    doi = meta("citation_doi") or ""

    figures = []
    for fig in doc.xpath("//figure"):
        srcs = [s for s in fig.xpath(".//img/@src")
                if "MediaObjects" in s and FIGNUM_RE.search(s)]
        if not srcs:
            continue
        src = srcs[0]
        num = int(FIGNUM_RE.search(src).group(1))
        cap = fig.xpath(".//figcaption")
        fig_title = re.sub(r"\s+", " ", cap[0].text_content()).strip() if cap else ""
        desc = fig.xpath('.//*[contains(@class,"figure-description")]')
        body = re.sub(r"\s+", " ", desc[0].text_content()).strip() if desc else ""
        legend = (fig_title + " " + body).strip()
        figures.append({"fig_num": num, "fig_title": fig_title,
                        "legend": legend, "image_url": hires(src)})
    figures.sort(key=lambda f: f["fig_num"])
    return title, doi, figures


def load_done(meta_path: Path) -> set[str]:
    done = set()
    if meta_path.exists():
        for line in meta_path.read_text("utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["article_id"])
    return done


def scrape(journals, years, out: Path, max_pages, delay):
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "metadata.jsonl"
    done = load_done(meta_path)
    print(f"resume: {len(done)} articles already done")

    headers = {"User-Agent": UA, "Accept": "text/html,image/*"}
    limits = httpx.Limits(max_connections=12, max_keepalive_connections=6)
    n_fig = 0
    with meta_path.open("a", encoding="utf-8") as mf:
        for journal in journals:
            jname = JOURNALS.get(journal, journal)
            for year in years:
                # Fresh client per journal-year. A single long-lived client's
                # connection pool got saturated mid-run and then PoolTimeout'd
                # every later journal, silently dropping all of them.
                try:
                    with httpx.Client(headers=headers, timeout=30, limits=limits,
                                      follow_redirects=True) as client:
                        for aid in iter_article_ids(client, journal, year, max_pages):
                            if aid in done:
                                continue
                            try:
                                title, doi, figures = parse_article(client, aid)
                            except Exception as e:
                                print(f"  ! {aid}: {type(e).__name__}: {e}")
                                time.sleep(delay)
                                continue
                            for f in figures:
                                dest = out / journal / str(year) / f"{aid}_Fig{f['fig_num']}.png"
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                if not dest.exists():
                                    try:
                                        dest.write_bytes(_get(client, f["image_url"], binary=True))
                                    except Exception as e:
                                        print(f"  ! img {aid} Fig{f['fig_num']}: {e}")
                                        continue
                                row = {"journal": jname, "year": year, "article_id": aid,
                                       "doi": doi, "title": title, "fig_num": f["fig_num"],
                                       "fig_title": f["fig_title"], "legend": f["legend"],
                                       "image_url": f["image_url"],
                                       "local_path": str(dest.relative_to(out))}
                                mf.write(json.dumps(row, ensure_ascii=False) + "\n")
                                mf.flush()
                                n_fig += 1
                            done.add(aid)
                            print(f"  {jname} {year} {aid}: {len(figures)} figs "
                                  f"(total {n_fig})")
                            time.sleep(delay)
                except Exception as e:
                    print(f"  !! {jname} {year} aborted: {type(e).__name__}: {e}")
                    continue
    print(f"done: {n_fig} figures this run")


def main():
    ap = argparse.ArgumentParser(description="Scrape Nature figures + legends.")
    ap.add_argument("--journals", nargs="+", default=["nature"])
    ap.add_argument("--years", nargs="+", type=int, default=[2024])
    ap.add_argument("--out", type=Path, default=Path("figures"))
    ap.add_argument("--pages", type=int, default=None,
                    help="max listing pages per journal-year (default: all)")
    ap.add_argument("--delay", type=float, default=1.5,
                    help="seconds between article fetches")
    a = ap.parse_args()
    scrape(a.journals, a.years, a.out, a.pages, a.delay)


if __name__ == "__main__":
    main()
