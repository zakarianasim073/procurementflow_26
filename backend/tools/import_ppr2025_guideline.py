"""Import the user-supplied PPR 2025 guideline into PostgreSQL knowledge."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
import re
import sys
import uuid

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.db.base import get_session_factory
from app.models.intelligence import KnowledgeEntry

SOURCE_PATH = Path(r"D:\A1\procurementflow_final_v3\PPR2025 guideline.txt")
ENTRY_TYPE = "ppr2025_guideline_section"
SOURCE_TYPE = "ppr2025_guideline_source"


def clean_text(value: str) -> str:
    return value.replace("\ufffd", "'").replace("\x00", "").strip()


def build_sections(text: str, max_chars: int = 4200) -> list[dict]:
    paragraphs = [clean_text(part) for part in re.split(r"\r?\n\s*\r?\n", text) if clean_text(part)]
    sections: list[dict] = []
    buffer: list[str] = []
    size = 0
    for paragraph in paragraphs:
        if buffer and size + len(paragraph) > max_chars:
            content = "\n\n".join(buffer)
            sections.append({"title": buffer[0].splitlines()[0][:300], "content": content})
            buffer, size = [], 0
        buffer.append(paragraph)
        size += len(paragraph) + 2
    if buffer:
        sections.append({"title": buffer[0].splitlines()[0][:300], "content": "\n\n".join(buffer)})
    return sections


async def upsert_entry(db, *, entry_type: str, checksum: str, title: str, content: str, data: dict) -> KnowledgeEntry:
    entry = (
        await db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.entry_type == entry_type,
                KnowledgeEntry.checksum == checksum,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if entry is None:
        entry = KnowledgeEntry(
            id=str(uuid.uuid4()),
            entry_type=entry_type,
            checksum=checksum,
            title=title,
            source="user_supplied_file",
            source_file=str(SOURCE_PATH),
            procurement_type="Works",
            tags={"regulation": "PPR2025", "document_type": "guideline", "works_only": True},
            data=data,
            content=content,
            summary=content[:500],
            is_archived=False,
        )
        db.add(entry)
    else:
        entry.title = title
        entry.content = content
        entry.data = data
        entry.source_file = str(SOURCE_PATH)
        entry.is_archived = False
    return entry


async def main() -> None:
    raw = SOURCE_PATH.read_text(encoding="utf-8", errors="replace")
    text = clean_text(raw)
    source_checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    sections = build_sections(text)
    session_factory = get_session_factory()
    async with session_factory() as db:
        await upsert_entry(
            db,
            entry_type=SOURCE_TYPE,
            checksum=source_checksum,
            title="PPR 2025 Guideline — supplied source",
            content=text,
            data={
                "document_code": "PPR2025-GUIDELINE",
                "source_file": str(SOURCE_PATH),
                "character_count": len(text),
                "section_count": len(sections),
                "source_checksum": source_checksum,
            },
        )
        for index, section in enumerate(sections, 1):
            checksum = hashlib.sha256(f"{source_checksum}:{index}:{section['content']}".encode("utf-8")).hexdigest()
            await upsert_entry(
                db,
                entry_type=ENTRY_TYPE,
                checksum=checksum,
                title=section["title"],
                content=section["content"],
                data={
                    "document_code": "PPR2025-GUIDELINE",
                    "section_index": index,
                    "section_ref": f"G-{index:04d}",
                    "source_checksum": source_checksum,
                },
            )
        await db.commit()
    print(f"Imported source + {len(sections)} searchable sections; checksum={source_checksum}")


if __name__ == "__main__":
    asyncio.run(main())
