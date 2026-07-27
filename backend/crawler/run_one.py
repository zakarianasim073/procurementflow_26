from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from .run_all import run_single_plugin


def main():
    if len(sys.argv) < 2:
        print("usage: python -m crawler.run_one <plugin> [json-config-or-filepath]")
        sys.exit(1)
    plugin = sys.argv[1]
    config = {}
    if len(sys.argv) > 2:
        raw = sys.argv[2]
        if raw.startswith("{"):
            config = json.loads(raw)
        else:
            config = json.loads(Path(raw).read_text(encoding="utf-8"))
    result = asyncio.run(run_single_plugin(plugin, config=config))
    print(
        f"RESULT plugin={plugin} status={result.status} "
        f"pages={result.pages_done} items={result.items_done} "
        f"skipped={result.items_skipped} failed={result.items_failed} "
        f"error={result.error}",
        flush=True,
    )


if __name__ == "__main__":
    main()
