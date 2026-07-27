"""Export a deterministic schema-only baseline from an authoritative PG17 DB.

This tool never exports table data. It excludes Alembic's own version table,
removes psql-only guard commands, and prepends the production extensions.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


EXTENSIONS = """\
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

"""

VECTOR_COMPATIBILITY = """\

-- Add an indexed pgvector representation without removing the legacy
-- JSON/text embedding column still consumed by the application.
ALTER TABLE public.knowledge_embeddings
    ADD COLUMN embedding_vector public.vector(384);
CREATE INDEX ix_knowledge_embeddings_vector_hnsw
    ON public.knowledge_embeddings
    USING hnsw (embedding_vector public.vector_cosine_ops);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-dump", required=True, type=Path)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5433")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--database", default="procureflow_bd")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not os.getenv("PGPASSWORD"):
        raise SystemExit("PGPASSWORD must be provided in the process environment")

    with tempfile.TemporaryDirectory(prefix="procureflow-schema-") as temp_dir:
        raw_path = Path(temp_dir) / "schema.sql"
        command = [
            str(args.pg_dump),
            "--host", args.host,
            "--port", args.port,
            "--username", args.user,
            "--dbname", args.database,
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            "--no-comments",
            "--exclude-table=alembic_version",
            "--file", str(raw_path),
        ]
        subprocess.run(command, check=True)
        lines = raw_path.read_text(encoding="utf-8").splitlines()

    sanitized = [
        line for line in lines
        if not line.startswith("\\restrict ") and not line.startswith("\\unrestrict ")
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        EXTENSIONS + "\n".join(sanitized).strip() + VECTOR_COMPATIBILITY + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote schema-only baseline: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
