"""Import all existing JSONL files into PG17."""
import json
from pathlib import Path
import psycopg2

DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "procureflow_bd"
DB_USER = "postgres"
DB_PASS = "procurementflow"

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

conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
cur = conn.cursor()

for table, filename in TABLE_FILE_MAP.items():
    fp = OUTPUT_DIR / filename
    if not fp.exists():
        print(f"[SKIP] {table}: {filename} not found")
        continue
    count = 0
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cur.execute(
                f"INSERT INTO {table} (source, raw_data, crawled_at) VALUES (%s, %s, %s)",
                (rec["source"], json.dumps(rec["raw_data"], default=str), rec["crawled_at"]),
            )
            count += 1
    conn.commit()
    print(f"[IMPORT] {table}: {count} rows")

cur.close()
conn.close()
print("\nDone importing existing JSONL files.")
