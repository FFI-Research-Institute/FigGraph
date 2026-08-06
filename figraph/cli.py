"""Unified `figraph` command — dispatches to the subcommand modules.

    figraph scrape --journals nature --years 2024
    figraph index
    figraph recommend "compare uncertainty distributions across three groups"
    figraph search "kaplan-meier survival" -k 8
    figraph annotate --budget 100
    figraph update
"""
from __future__ import annotations

import sys

from figraph import annotate, index, recommend, scrape, search, update


def _serve():
    # lazy import so the CLI works without the optional `mcp` dependency
    from figraph import mcp_server
    mcp_server.main()


SUBCOMMANDS = {
    "annotate": annotate.main,
    "scrape": scrape.main,
    "index": index.main,
    "recommend": recommend.main,
    "search": search.main,
    "update": update.main,
    "serve": _serve,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SUBCOMMANDS:
        print(f"usage: figraph <{' | '.join(SUBCOMMANDS)}> [args...]", file=sys.stderr)
        sys.exit(1)
    sub = sys.argv[1]
    sys.argv = [f"figraph {sub}", *sys.argv[2:]]
    SUBCOMMANDS[sub]()


if __name__ == "__main__":
    main()
