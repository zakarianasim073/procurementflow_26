from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_importer():
    script = Path(__file__).resolve().parents[1] / "scripts" / "import_crawl_json_to_db.py"
    spec = importlib.util.spec_from_file_location("import_crawl_json_to_db", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_crawl_importer_defaults_to_repo_crawl_output():
    module = _load_importer()
    expected = Path(__file__).resolve().parents[1] / "crawl_output"

    assert module.CRAWL_ROOT == expected.resolve()


def test_crawl_importer_accepts_crawl_root_override(tmp_path):
    module = _load_importer()

    args = module.parse_args(["--dry-run", "--crawl-root", str(tmp_path)])

    assert args.crawl_root == tmp_path
