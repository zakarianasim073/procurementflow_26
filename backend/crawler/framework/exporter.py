from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataExporter:
    @staticmethod
    def to_jsonl(records: List[dict], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")

    @staticmethod
    def to_csv(records: List[dict], output_path: Path):
        if not records:
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = set()
        for rec in records:
            fieldnames.update(rec.keys())
        fieldnames = sorted(fieldnames)
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record)

    @staticmethod
    def to_json(records: List[dict], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, default=str, ensure_ascii=False, indent=2)

    @staticmethod
    def flatten_nested(data: Dict[str, Any], prefix: str = "", sep: str = "_") -> Dict[str, Any]:
        flat = {}
        for key, value in data.items():
            full_key = f"{prefix}{sep}{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(DataExporter.flatten_nested(value, full_key, sep))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flat.update(DataExporter.flatten_nested(item, f"{full_key}{sep}{i}", sep))
                    else:
                        flat[f"{full_key}{sep}{i}"] = item
            else:
                flat[full_key] = value
        return flat

    @staticmethod
    def export_flat(records: List[dict], output_path: Path, fmt: str = "csv"):
        flat_records = [DataExporter.flatten_nested(r) for r in records]
        if fmt == "csv":
            DataExporter.to_csv(flat_records, output_path)
        elif fmt == "json":
            DataExporter.to_json(flat_records, output_path)
        else:
            DataExporter.to_jsonl(records, output_path)
