"""Unified `figraph` command — dispatches to the subcommand modules.

    figraph scrape --journals nature --years 2024
    figraph index
    figraph search "kaplan-meier survival" -k 8
    figraph update
"""
from __future__ import annotations

import sys

from figraph import index, scrape, search, update

SUBCOMMANDS = {
    "scrape": scrape.main,
    "index": index.main,
    "search": search.main,
    "update": update.main,
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
