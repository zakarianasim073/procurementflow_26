"""Discover total pages per Financial Year for APP listings."""
import httpx, re

BASE = "https://www.eprocure.gov.bd"
FYS = [
    "2014-2015","2015-2016","2016-2017","2017-2018","2018-2019",
    "2019-2020","2020-2021","2021-2022","2022-2023","2023-2024",
    "2024-2025","2025-2026","2026-2027",
]

client = httpx.Client(verify=True, follow_redirects=True, timeout=30)
client.get(BASE)

for fy in FYS:
    r = client.post(
        f"{BASE}/SearchServlet",
        data={"action":"Search","departmentId":"0","office":"","financialYear":fy,
              "budgetType":"","procNature":"","procType":"","pageNo":"1","size":"50"},
        timeout=30,
    )
    tp = re.search(r'<input[^>]*id="totalPages"[^>]*value="(\d+)"', r.text)
    pages = int(tp.group(1)) if tp else 0
    print(f"{fy}: {pages} pages ({pages * 50:,} records)")

client.close()
