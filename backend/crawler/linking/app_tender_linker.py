from sqlalchemy import create_engine, text
import re
from rapidfuzz import fuzz

DB_URL = "postgresql+psycopg2://procureflow:procureflow@localhost:5432/procureflow"
engine = create_engine(DB_URL)

def normalize(s: str) -> str:
    return re.sub(r"[\s\-_/]+", "", (s or "").upper())

def build_app_tender_links(min_confidence: int = 80):
    with engine.begin() as conn:
        app_rows = conn.execute(text("""
            SELECT raw_data->>'app_id' AS app_id, raw_data->>'pkg_id' AS pkg_id,
                   raw_data->>'package_no' AS package_no, raw_data->>'organization' AS organization,
                   raw_data->>'pe_office' AS pe_office FROM raw_app_packages
        """)).fetchall()
        tender_rows = conn.execute(text("""
            SELECT raw_data->>'tender_id' AS tender_id, raw_data->>'reference_no' AS reference_no,
                   raw_data->>'organization' AS organization, raw_data->>'procuring_entity_name' AS pe_name
            FROM raw_tenders
        """)).fetchall()

    links = []
    for app in app_rows:
        app_org_norm = normalize(app.organization)
        app_pe_norm = normalize(app.pe_office)
        candidates = [t for t in tender_rows if normalize(t.organization) == app_org_norm or normalize(t.pe_name) == app_pe_norm]
        best_match, best_score = None, 0
        for t in candidates:
            score = fuzz.partial_ratio(normalize(app.package_no), normalize(t.reference_no))
            if score > best_score:
                best_match, best_score = t, score
        if best_match and best_score >= min_confidence:
            links.append({
                "app_id": app.app_id, "pkg_id": app.pkg_id, "app_package_no": app.package_no,
                "tender_id": best_match.tender_id, "tender_reference_no": best_match.reference_no,
                "match_confidence": best_score, "match_method": "fuzzy_partial",
            })

    with engine.begin() as conn:
        for link in links:
            conn.execute(text("""
                INSERT INTO app_tender_link (app_id, pkg_id, app_package_no, tender_id, tender_reference_no, match_confidence, match_method)
                VALUES (:app_id, :pkg_id, :app_package_no, :tender_id, :tender_reference_no, :match_confidence, :match_method)
                ON CONFLICT (app_id, pkg_id, tender_id) DO NOTHING
            """), link)
    return len(links)

if __name__ == "__main__":
    print(f"Created {build_app_tender_links()} app-tender links")