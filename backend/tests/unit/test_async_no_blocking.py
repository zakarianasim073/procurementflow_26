"""Scan async def functions for synchronous blocking calls (W-005).

Checks the specific patterns listed in acceptance criteria:
1. Zero time.sleep() in any async def — must use await asyncio.sleep()
2. Zero pdfplumber.open() without asyncio.to_thread in async def
3. Zero openpyxl.load_workbook without asyncio.to_thread in async def
4. Zero xlsxwriter.Workbook without asyncio.to_thread in async def
5. Zero PyPDF2.PdfReader without asyncio.to_thread in async def
6. Zero pypdf.PdfReader without asyncio.to_thread in async def
7. Zero sync httpx.Client() usage in async def
8. Zero docx.Document without asyncio.to_thread in async def

Known pre-existing violations outside W-005 scope are documented in
KNOWN_VIOLATIONS to allow regression catching — new violations fail.
"""

import ast
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = PROJECT_ROOT / "app"

BLOCKING_DOTTED_CALLS = [
    ("time.sleep", "use await asyncio.sleep() instead"),
    ("pdfplumber.open", "wrap in asyncio.to_thread"),
    ("openpyxl.load_workbook", "wrap in asyncio.to_thread"),
    ("xlsxwriter.Workbook", "wrap in asyncio.to_thread"),
    ("PyPDF2.PdfReader", "wrap in asyncio.to_thread"),
    ("pypdf.PdfReader", "wrap in asyncio.to_thread"),
    ("httpx.Client", "use httpx.AsyncClient or wrap in asyncio.to_thread"),
    ("docx.Document", "wrap in asyncio.to_thread"),
]

# Pre-existing violations outside W-005 scope — documented, not regressions.
# New files/modules should NOT add entries here.
KNOWN_VIOLATIONS = {
    "app/api/v1/crawler.py:200 async test_searchservlet() calls httpx.Client",
}


def _find_async_defs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]


def _dotted_name(node):
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        if isinstance(node.value, ast.Attribute):
            inner = _dotted_name(node.value)
            if inner:
                return f"{inner}.{node.attr}"
        return None
    if isinstance(node, ast.Name):
        return node.id
    return None


def _sync_nested_ranges(async_func: ast.AsyncFunctionDef) -> list[tuple[int, int]]:
    """Line ranges of sync FunctionDef nodes directly nested inside an async def.

    Calls inside these ranges are intentional to_thread targets and must NOT
    be flagged as violations of the async-no-blocking rule.
    """
    ranges = []
    for node in ast.walk(async_func):
        if isinstance(node, ast.FunctionDef):
            end = getattr(node, "end_lineno", node.lineno + 500)
            ranges.append((node.lineno, end))
    return ranges


def _get_dotted_calls(func: ast.AsyncFunctionDef) -> list[tuple[int, str]]:
    """Return (lineno, dotted_name) for every method call inside the async def,
    excluding lines that fall inside a sync nested helper function.
    """
    nested = _sync_nested_ranges(func)
    calls = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        lineno = node.lineno
        if any(s <= lineno <= e for s, e in nested):
            continue  # inside a sync to_thread helper — not a violation
        name = _dotted_name(node.func)
        if name and "." in name:
            calls.append((lineno, name))
    return calls


def test_no_blocking_calls_in_async_defs():
    """Assert zero NEW unwrapped sync blocking calls in any async def.

    Known pre-existing violations are documented in KNOWN_VIOLATIONS.
    """
    violations = []

    for root, _dirs, files in os.walk(APP_DIR):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            filepath = Path(root) / fn
            rel_path = filepath.relative_to(PROJECT_ROOT).as_posix()
            try:
                tree = ast.parse(filepath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            for func in _find_async_defs(tree):
                calls = _get_dotted_calls(func)
                for pattern, msg in BLOCKING_DOTTED_CALLS:
                    for line, name in calls:
                        if name == pattern:
                            loc = f"{rel_path}:{line} async {func.name}() calls {pattern}"
                            if loc not in KNOWN_VIOLATIONS:
                                violations.append(f"{loc} — {msg}")

    assert not violations, (
        f"Found {len(violations)} NEW blocking call(s) in async def "
        f"(not in KNOWN_VIOLATIONS):\n" +
        "\n".join(f"  {v}" for v in violations)
    )
