"""One-off probe: can we scrape nature.com over plain HTTP, and what's the HTML shape?

Not part of the tool. Throwaway recon to de-risk the scraper before writing it.
"""
import os
import re
import sys
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html"})
    proxy = os.environ.get("HTTPS_PROXY")
    if proxy:
        req.set_proxy(proxy.replace("http://", ""), "https")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def title(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return (m.group(1).strip()[:120] if m else "(no title)")


listing = "https://www.nature.com/nature/research-articles?year=2024&page=1"
print(f"== LISTING: {listing}")
try:
    st, html = fetch(listing)
    print(f"status={st} len={len(html)} title={title(html)!r}")
    ids = re.findall(r"/articles/(s\d{5}-\d{3}-\d{4,6}-[0-9a-z]+)", html)
    uniq = list(dict.fromkeys(ids))
    print(f"article ids found: {len(uniq)} ; sample: {uniq[:5]}")
except Exception as e:
    print(f"LISTING FAILED: {type(e).__name__}: {e}")
    uniq = []

if uniq:
    art = f"https://www.nature.com/articles/{uniq[0]}"
    print(f"\n== ARTICLE PAGE: {art}")
    try:
        st, html = fetch(art)
        print(f"status={st} len={len(html)} title={title(html)!r}")
        imgs = re.findall(r'https://media\.springernature\.com/[^"\']+', html)
        imgs = list(dict.fromkeys(imgs))
        print(f"springernature image urls: {len(imgs)}")
        for u in imgs[:4]:
            print("  IMG", u[:140])
        caps = re.findall(r'<figcaption[^>]*>(.*?)</figcaption>', html, re.S)
        print(f"figcaption blocks: {len(caps)}")
        if caps:
            txt = re.sub(r"<[^>]+>", " ", caps[0])
            txt = re.sub(r"\s+", " ", txt).strip()
            print("  CAP0:", txt[:200])
    except Exception as e:
        print(f"FIGURES FAILED: {type(e).__name__}: {e}")
