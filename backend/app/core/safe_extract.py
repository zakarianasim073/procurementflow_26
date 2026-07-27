"""Guarded ZIP extraction (SEC-05 / T-006).

Protects every ZIP ingestion path (e-GP document bundles, agent-acquired
archives) against:
- path traversal ("../", absolute paths, drive letters in member names)
- zip bombs (per-archive uncompressed-size cap and compression-ratio cap)
- member floods (member-count cap)

All limits are configurable via environment variables so legitimate large
tender bundles (drawings PDFs) can be accommodated without code changes.
"""

from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

ZIP_MAX_MEMBERS = int(os.getenv("UPLOAD_ZIP_MAX_MEMBERS", "2000"))
ZIP_MAX_TOTAL_UNCOMPRESSED = int(os.getenv("UPLOAD_ZIP_MAX_TOTAL_MB", "2000")) * 1024 * 1024
ZIP_MAX_RATIO = float(os.getenv("UPLOAD_ZIP_MAX_RATIO", "200"))


class UnsafeZipError(ValueError):
    """Raised when a ZIP archive fails a safety check; nothing is extracted."""


def _validate_member(member: zipfile.ZipInfo, dest_dir: Path) -> None:
    name = member.filename
    if not name or name != name.strip():
        raise UnsafeZipError(f"suspicious member name: {name!r}")
    pure = Path(name)
    if pure.is_absolute() or (len(name) > 1 and name[1] == ":"):
        raise UnsafeZipError(f"absolute path in archive: {name!r}")
    if ".." in pure.parts:
        raise UnsafeZipError(f"path traversal in archive: {name!r}")
    resolved = (dest_dir / pure).resolve()
    if not resolved.is_relative_to(dest_dir.resolve()):
        raise UnsafeZipError(f"member escapes destination: {name!r}")


def safe_extract_zip(
    zip_path: Path | str,
    dest_dir: Path | str,
    *,
    max_members: int = ZIP_MAX_MEMBERS,
    max_total_uncompressed: int = ZIP_MAX_TOTAL_UNCOMPRESSED,
    max_ratio: float = ZIP_MAX_RATIO,
) -> List[Path]:
    """Extract a ZIP archive after validating every member.

    Raises UnsafeZipError (before extracting anything) if the archive fails a
    safety check, or zipfile.BadZipFile for corrupt archives. Returns the list
    of extracted file paths.

    Sync (zipfile) — call from sync contexts or via run_in_executor.
    """
    zip_path = Path(zip_path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        if len(members) > max_members:
            raise UnsafeZipError(f"{zip_path.name}: {len(members)} members exceeds cap of {max_members}")

        total_uncompressed = 0
        total_compressed = 0
        for member in members:
            _validate_member(member, dest_dir)
            total_uncompressed += member.file_size
            total_compressed += member.compress_size

        if total_uncompressed > max_total_uncompressed:
            raise UnsafeZipError(
                f"{zip_path.name}: uncompressed size {total_uncompressed} exceeds "
                f"cap of {max_total_uncompressed} bytes"
            )
        # Ratio check only when meaningfully compressed data exists — tiny
        # archives of empty files legitimately have degenerate ratios.
        if total_compressed > 0 and total_uncompressed / total_compressed > max_ratio:
            raise UnsafeZipError(
                f"{zip_path.name}: compression ratio "
                f"{total_uncompressed / total_compressed:.0f}x exceeds cap of {max_ratio:.0f}x"
            )

        extracted: List[Path] = []
        for member in members:
            zf.extract(member, dest_dir)
            target = dest_dir / member.filename
            if target.is_file():
                extracted.append(target)

    logger.info("Safely extracted %s: %d files to %s", zip_path.name, len(extracted), dest_dir)
    return extracted
