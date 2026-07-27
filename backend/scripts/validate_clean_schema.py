"""Validate a migrated clean database against the reviewed baseline contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import psycopg2


REQUIRED_EXTENSIONS = {"vector", "pg_trgm", "uuid-ossp"}


def _qualified_names(pattern: str, sql: str) -> set[str]:
    return {
        f"{schema}.{name}"
        for schema, name in re.findall(pattern, sql, flags=re.IGNORECASE)
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "alembic_clean"
        / "baseline"
        / "20260727_head.sql",
    )
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    baseline = args.baseline.read_text(encoding="utf-8")
    expected_tables = _qualified_names(
        r"CREATE TABLE\s+([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)",
        baseline,
    )
    expected_indexes = {
        f"{schema}.{index}"
        for index, schema in re.findall(
            r"CREATE (?:UNIQUE )?INDEX\s+([a-z_][a-z0-9_]*)"
            r"\s+ON\s+(?:ONLY\s+)?([a-z_][a-z0-9_]*)\.",
            baseline,
            flags=re.IGNORECASE,
        )
    }
    expected_constraints = set(
        re.findall(
            r"ADD CONSTRAINT\s+([a-z_][a-z0-9_]*)",
            baseline,
            flags=re.IGNORECASE,
        )
    )

    with psycopg2.connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT schemaname || '.' || tablename
                FROM pg_tables
                WHERE schemaname IN ('public', 'commercial', 'knowledge', 'tender')
                """
            )
            actual_tables = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT schemaname || '.' || indexname
                FROM pg_indexes
                WHERE schemaname IN ('public', 'commercial', 'knowledge', 'tender')
                """
            )
            actual_indexes = {row[0] for row in cursor.fetchall()}
            cursor.execute("SELECT conname FROM pg_constraint")
            actual_constraints = {row[0] for row in cursor.fetchall()}
            cursor.execute("SELECT extname FROM pg_extension")
            actual_extensions = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'knowledge_embeddings'
                  AND column_name = 'embedding_vector'
                """
            )
            vector_column = cursor.fetchone()
            cursor.execute("SELECT version_num FROM alembic_version")
            alembic_revisions = sorted(row[0] for row in cursor.fetchall())

    result = {
        "expected": {
            "tables": len(expected_tables),
            "indexes": len(expected_indexes),
            "named_constraints": len(expected_constraints),
        },
        "missing": {
            "tables": sorted(expected_tables - actual_tables),
            "indexes": sorted(expected_indexes - actual_indexes),
            "named_constraints": sorted(expected_constraints - actual_constraints),
            "extensions": sorted(REQUIRED_EXTENSIONS - actual_extensions),
        },
        "unexpected": {
            "tables": sorted(actual_tables - expected_tables),
        },
        "vector_column": vector_column,
        "alembic_revisions": alembic_revisions,
    }
    result["passed"] = (
        not any(result["missing"].values())
        and not result["unexpected"]["tables"]
        and vector_column is not None
        and alembic_revisions == ["20260727_clean_baseline"]
    )

    rendered = json.dumps(result, indent=2, default=str)
    print(rendered)
    if args.json_output:
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
