import json
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://procureflow:procureflow@localhost:5432/procureflow"
OUTPUT_DIR = Path("output/raw")

TABLE_FILE_MAP = {
    "raw_tenders": "raw_tenders.jsonl",
    "raw_awards": "raw_awards.jsonl",
    "raw_experience": "raw_experience.jsonl",
    "raw_app_packages": "raw_app_packages.jsonl",
    "raw_debarment": "raw_debarment.jsonl",
    "raw_offline_tenders": "raw_offline_tenders.jsonl",
    "raw_offline_awards": "raw_offline_awards.jsonl",
}

def import_table(engine, table: str, filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        print(f"skip {table}: {filename} not found")
        return 0
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        with engine.begin() as conn:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                conn.execute(
                    text(f"INSERT INTO {table} (source, raw_data, crawled_at) VALUES (:source, :raw_data, :crawled_at)"),
                    {"source": rec["source"], "raw_data": json.dumps(rec["raw_data"], default=str), "crawled_at": rec["crawled_at"]},
                )
                count += 1
    print(f"imported {count} rows into {table}")
    return count

if __name__ == "__main__":
    engine = create_engine(DB_URL)
    total = sum(import_table(engine, t, f) for t, f in TABLE_FILE_MAP.items())
    print(f"Total imported: {total}")