from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
import json
import re


def ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def norm(v) -> str:
    return "" if v is None else str(v).strip()


def normalize_package_no(value) -> str:
    """Return the canonical cross-source package linkage key."""
    if value is None:
        return ""
    raw = str(value).strip().upper()
    if not raw:
        return ""
    raw = raw.replace("\\", "/")
    raw = re.sub(r"\s+", "", raw)
    raw = re.sub(r"[^A-Z0-9/.-]", "", raw)
    if re.fullmatch(r"\d{6,}", raw):
        return ""
    if not any(ch.isdigit() for ch in raw):
        return ""
    if not any(ch.isalpha() for ch in raw) and not any(ch in raw for ch in "/-."):
        return ""
    if len(raw) > 120:
        return ""
    return raw


def to_num(v) -> float | None:
    try:
        return float(str(v).replace(",", "").replace(" ", "").strip())
    except Exception:
        return None


def write_json(path: str | Path, data) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return p


def zip_dir(source_dir: str | Path, zip_path: str | Path) -> Path:
    source = Path(source_dir)
    target = Path(zip_path)
    ensure_dir(target.parent)
    with ZipFile(target, "w", ZIP_DEFLATED) as zf:
        for file_path in source.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(source).as_posix())
    return target
