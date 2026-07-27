"""
Subprocess downloader for e-GP tender documents.
Usage: python _sub_dl.py <tender_id> <docs_dir> <uploads_dir>
"""
import sys, httpx, json, shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(BACKEND / "app"))
sys.path.insert(0, str(BACKEND))

from app.agents.credentials import get_credentials
from app.agents.egp_client import eGPClient, BASE_URL

TENDER_ID = sys.argv[1]
DOCS_DIR = Path(sys.argv[2])
UPLOADS_DIR = Path(sys.argv[3])
DOCS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

try:
    creds = get_credentials()
    client = eGPClient(email=creds.egp.email, password=creds.egp.password, timeout=30)
    client.login()
except Exception as exc:
    print(f"Sub dl: login failed: {exc}", flush=True)
    print("[]", flush=True)
    sys.exit(0)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": f"{BASE_URL}/resources/common/ViewTender.jsp?id={TENDER_ID}",
}

results = []

# 1) Notice PDF (public)
notice_url = (
    f"{BASE_URL}/GeneratePdf"
    f"?reqURL=http://www.eprocure.gov.bd/resources/common/ViewTender.jsp"
    f"&reqQuery=id={TENDER_ID}&folderName=TenderNotice&id={TENDER_ID}"
)
try:
    nr = client.client.get(notice_url, headers=headers, timeout=30)
    if nr.status_code == 200 and len(nr.content) > 500:
        p = DOCS_DIR / "notice.pdf"
        p.write_bytes(nr.content)
        results.append({"doc_type": "NIT", "path": str(p), "size_bytes": len(nr.content), "source": "egp_direct", "url": notice_url})
        shutil.copy2(str(p), str(UPLOADS_DIR / "notice.pdf"))
except Exception:
    pass

# 2) Check TenderDocView.jsp for payment status before trying ZIP
tdv_url = f"{BASE_URL}/tenderer/TenderDocView.jsp?tenderId={TENDER_ID}"
payment_pending = False
try:
    tr = client.client.get(tdv_url, headers=headers, timeout=30)
    if tr.status_code == 200:
        (DOCS_DIR / "TenderDocView.html").write_text(tr.text, encoding="utf-8")
        if "Payment Pending" in tr.text or "Pay Now" in tr.text:
            payment_pending = True
            print(f"Sub dl: Documents require payment, skipping ZIP", flush=True)
except Exception:
    pass

# 3) All-documents ZIP (skip if payment pending)
if not payment_pending:
    zip_url = f"{BASE_URL}/TenderSecUploadServlet?tenderId={TENDER_ID}&folderArchId=1&lotNo=Package&funName=zipdownload"
    try:
        zr = client.client.get(zip_url, headers=headers, timeout=45)
        if zr.status_code == 200 and len(zr.content) > 1000:
            zp = DOCS_DIR / "all_documents.zip"
            zp.write_bytes(zr.content)
            results.append({"doc_type": "ZIP", "path": str(zp), "size_bytes": len(zr.content), "source": "egp_direct", "url": zip_url})
            shutil.copy2(str(zp), str(UPLOADS_DIR / "all_documents.zip"))
            from app.core.safe_extract import UnsafeZipError, safe_extract_zip
            try:
                safe_extract_zip(zp, UPLOADS_DIR)
                for fp in sorted(UPLOADS_DIR.rglob("*")):
                    if fp.is_file() and fp.name not in ("all_documents.zip", "notice.pdf"):
                        results.append({"doc_type": "extracted", "path": str(fp), "size_bytes": fp.stat().st_size, "source": "zip_extract"})
            except UnsafeZipError as exc:
                print(f"Sub dl: rejected unsafe ZIP: {exc}", flush=True)
    except Exception:
        pass

client.close()
print(json.dumps(results, default=str), flush=True)
