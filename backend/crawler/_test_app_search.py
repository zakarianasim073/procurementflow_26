"""Test the SearchServlet APP listing endpoint."""
import httpx, re, json

BASE = "https://www.eprocure.gov.bd"
client = httpx.Client(verify=True, follow_redirects=True, timeout=30)
client.get(BASE)

r = client.post(
    f"{BASE}/SearchServlet",
    data={
        "action": "Search",
        "departmentId": "0",
        "office": "",
        "financialYear": "2025-2026",
        "budgetType": "",
        "procNature": "",
        "procType": "",
        "pageNo": "1",
        "size": "10",
    },
    timeout=30,
)
tp_m = re.search(r'<input[^>]*id="totalPages"[^>]*value="(\d+)"', r.text)
total = int(tp_m.group(1)) if tp_m else 0
rows = re.findall(r"<tr[^>]*>.*?</tr>", r.text, re.DOTALL)
print(f"FY 2025-2026: total_pages={total}, rows_this_page={len(rows)}")
print(f"Response length: {len(r.text)} chars")
print(f"Status: {r.status_code}")

# Show first 2 rows
count = 0
for row_html in rows:
    cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL | re.IGNORECASE)
    texts = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    texts = [re.sub(r"\s+", " ", t) for t in texts]
    if texts and texts[0].isdigit():
        print(f"\nRow {texts[0]}:")
        for i, t in enumerate(texts):
            print(f"  Col {i}: {t[:100]}")
        count += 1
        if count >= 2:
            break
client.close()
