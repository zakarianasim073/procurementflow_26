"""
Subprocess document downloader for e-GP tender documents.
Bypasses in-process WinError 10060 by running in a clean Python process.
Usage: python _sub_dl_crawler.py <tender_id> <output_dir>
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents.credentials import get_credentials
from app.agents.egp_client import eGPClient, BASE_URL


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def download_docs(tender_id: str, output_dir: Path) -> list[dict]:
    """Download tender documents from e-GP. Returns list of file metadata dicts."""
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    try:
        creds = get_credentials()
        client = eGPClient(email=creds.egp.email, password=creds.egp.password, timeout=45)
        client.login()
    except Exception as exc:
        return results

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"{BASE_URL}/resources/common/ViewTender.jsp?id={tender_id}",
    }

    # 1) Notice PDF (public, no auth required)
    notice_url = (
        f"{BASE_URL}/GeneratePdf"
        f"?reqURL=http://www.eprocure.gov.bd/resources/common/ViewTender.jsp"
        f"&reqQuery=id={tender_id}&folderName=TenderNotice&id={tender_id}"
    )
    try:
        nr = client.client.get(notice_url, headers=headers, timeout=45)
        if nr.status_code == 200 and len(nr.content) > 500:
            p = output_dir / "notice.pdf"
            p.write_bytes(nr.content)
            results.append({
                "doc_type": "NIT", "filename": "notice.pdf",
                "path": str(p), "size_bytes": len(nr.content),
                "source": "egp_direct", "url": notice_url,
                "hash": file_hash(p),
            })
    except Exception:
        pass

    # 2) Check TenderDocView.jsp for payment status
    tdv_url = f"{BASE_URL}/tenderer/TenderDocView.jsp?tenderId={tender_id}"
    payment_pending = False
    try:
        tr = client.client.get(tdv_url, headers=headers, timeout=45)
        if tr.status_code == 200:
            (output_dir / "TenderDocView.html").write_text(tr.text, encoding="utf-8")
            if "Payment Pending" in tr.text or "Pay Now" in tr.text:
                payment_pending = True
    except Exception:
        pass

    # 3) All-documents ZIP (skip if payment pending)
    if not payment_pending:
        zip_url = (
            f"{BASE_URL}/TenderSecUploadServlet"
            f"?tenderId={tender_id}&folderArchId=1&lotNo=Package&funName=zipdownload"
        )
        try:
            zr = client.client.get(zip_url, headers=headers, timeout=90)
            if zr.status_code == 200 and len(zr.content) > 1000:
                zp = output_dir / "all_documents.zip"
                zp.write_bytes(zr.content)
                results.append({
                    "doc_type": "ZIP", "filename": "all_documents.zip",
                    "path": str(zp), "size_bytes": len(zr.content),
                    "source": "egp_direct", "url": zip_url,
                    "hash": file_hash(zp),
                })
                with zipfile.ZipFile(zp) as zf:
                    zf.extractall(str(docs_dir))
                for fp in sorted(docs_dir.rglob("*")):
                    if fp.is_file():
                        results.append({
                            "doc_type": "extracted", "filename": fp.name,
                            "path": str(fp), "size_bytes": fp.stat().st_size,
                            "source": "zip_extract", "hash": file_hash(fp),
                        })
        except Exception:
            pass

    client.close()
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python _sub_dl_crawler.py <tender_id> <output_dir>", flush=True)
        print("[]", flush=True)
        sys.exit(1)

    tender_id = sys.argv[1]
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    results = download_docs(tender_id, output_dir)
    print(json.dumps(results, default=str), flush=True)
