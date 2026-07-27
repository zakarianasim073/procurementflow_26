"""Fail unless the current checkout is a clean, reproducible release input."""

from __future__ import annotations

import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], text=True, encoding="utf-8", errors="replace"
    ).strip()


def main() -> int:
    revision = git("rev-parse", "--verify", "HEAD")
    branch = git("branch", "--show-current")
    changes = git("status", "--porcelain")
    if changes:
        count = len(changes.splitlines())
        print(f"FAIL: release checkout has {count} uncommitted paths", file=sys.stderr)
        return 1
    if branch not in {"main", ""}:
        print(f"FAIL: release checkout is on unexpected branch {branch!r}", file=sys.stderr)
        return 1
    print(f"PASS: clean release revision {revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
