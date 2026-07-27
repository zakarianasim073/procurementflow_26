# SOR API Contract

**Router**: `/api/v1/sor`  
**Tags**: `sor`  
**Auth**: Optional JWT

---

## Endpoint Catalog

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/sor/agencies` | List SOR agencies with stats |
| GET | `/sor/lookup` | Look up single rate by code |
| POST | `/sor/load-pdf` | Load SOR rates from PDF (admin) |

---

## Request/Response Schemas

### `GET /sor/agencies`

**Response (200)**
```json
{
  "agencies": [
    {
      "id": "bwdb",
      "name": "BWDB",
      "total_rates": 1024,
      "has_csv": true
    },
    {
      "id": "pwd",
      "name": "PWD",
      "total_rates": 2018,
      "has_csv": true
    },
    {
      "id": "lged",
      "name": "LGED",
      "total_rates": 1503,
      "has_csv": true
    }
  ]
}
```

---

### `GET /sor/lookup`

**Query Parameters**
| Param | Type | Required | Pattern | Default |
|-------|------|----------|---------|---------|
| `code` | string | Yes | — | — |
| `agency` | string | No | `^(BWDB\|PWD\|LGED)$` | BWDB |
| `zone` | string | No | `^(A\|B\|C\|D)$` | — |
| `description` | string | No | — | — |

**Response (200)**
```json
{
  "code": "40-200-00",
  "description": "Excavation in all kinds of soil",
  "unit": "m3",
  "zone_a": 185.00,
  "zone_b": 192.00,
  "zone_c": 210.00,
  "zone_d": 205.00,
  "rate": 192.00,
  "zone": "B",
  "agency": "BWDB"
}
```

**Matching Logic** (SOR Service)
1. Exact code match (case-insensitive)
2. Prefix match (code starts with)
3. Fuzzy match on description (threshold 0.42, rapidfuzz)
4. Returns zone-specific rate based on `zone` param (defaults to A)

**Errors**
- `404` Rate not found

---

### `POST /sor/load-pdf`

**Query Parameters**
| Param | Type | Required | Pattern |
|-------|------|----------|---------|
| `agency` | string | Yes | `^(BWDB\|PWD\|LGED)$` |
| `zone` | string | No | `^(A\|B\|C\|D)$` |
| `file` | string | Yes | Path to PDF |

**Response (200)**
```json
{
  "success": true,
  "loaded": 1024,
  "agency": "BWDB"
}
```

**Notes**
- Admin-only in practice (requires file system access)
- PDF parsing uses `pdfplumber` table extraction
- BWDB: `_parse_bwdb_boq_tables()` handles multi-column layout
- LGED/PWD: `extract_from_pdf_tables.py` with format detection

---

## Agency Code Patterns (Disjoint)

| Agency | Pattern | Regex | Example |
|--------|---------|-------|---------|
| BWDB | Dash-separated | `^\d{2}-\d{3}-\d{2}` | `40-200-00` |
| PWD | Dotted (2-digit prefix) | `^\d{2}\.\d` | `26.50.1` |
| LGED | Dotted (1-digit prefix 2-9) | `^[2-9]\.\d{2}` | `4.09.01.01` |

**Edge Cases** (handled in `boq_processor.py`):
- PWD: 7 dash codes (`02-1-2`), 16 EM codes (`EM3.1.2`), 7 `PWD ` prefixed
- LGED: 1 trivial code `1`, 19 codes starting with `1.`

---

## Zone Mapping (Division → Agency Zone)

| Division | BWDB | PWD | LGED |
|----------|------|-----|------|
| Dhaka, Mymensingh | A | A | A |
| Chattogram, Sylhet | B | B | B |
| Khulna, Barishal | **C** | **C** | **D** |
| Rajshahi, Rangpur | **D** | **D** | **C** |

**LGED swaps C↔D vs BWDB/PWD**

**BWDB Full District Lists** (from SOR PDF p11):
- **Zone A (12)**: Dhaka, Narayanganj, Manikganj, Narsingdi, Gazipur, Mymensingh, Munshiganj, Kishoreganj, Tangail, Jamalpur, Sherpur, Netrakona
- **Zone B (9)**: Chattogram, Rangamati, Khagrachari, Cox's Bazar, Bandarban, Sylhet, Sunamganj, Habiganj, Moulvibazar
- **Zone C (27)**: Khulna, Satkhira, Bagerhat, Jashore, Narail, Barishal, Jhalokathi, Pirojpur, Patuakhali, Barguna, Bhola, Faridpur, Rajbari, Madaripur, Shariatpur, Gopalganj, Kushtia, Chuadanga, Meherpur, Magura, Jhenaidah, Cumilla, Brahmanbaria, Chandpur, Feni, Noakhali, Lakshmipur
- **Zone D (16)**: Rangpur, Kurigram, Gaibandha, Lalmonirhat, Nilphamari, Thakurgaon, Panchagarh, Dinajpur, Rajshahi, Naogaon, Nawabganj, Natore, Bogura, Joypurhat, Sirajganj, Pabna

**API Usage**: Pass `zone` as string `"B"` (uniform) or JSON `{"BWDB":"B","PWD":"B","LGED":"B"}` for mixed zones.

---

## Error Schema

```json
{
  "detail": "Rate not found",
  "status_code": 404,
  "error_code": "SOR_RATE_NOT_FOUND"
}
```

---

## Caching

- `GET /agencies`: `public, max-age=3600` (SOR data rarely changes)
- `GET /lookup`: `public, max-age=3600, stale-while-revalidate=86400`

---

## React Query Mapping

```typescript
export const sorKeys = {
  agencies: () => ['sor', 'agencies'] as const,
  lookup: (code: string, agency: string, zone?: string) => 
    ['sor', 'lookup', { code, agency, zone }] as const,
};

export function useSorAgencies() {
  return useQuery({
    queryKey: sorKeys.agencies(),
    queryFn: () => apiFetch<SorAgenciesResponse>('/sor/agencies'),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

export function useSorRate(code: string, agency = 'BWDB', zone?: string) {
  return useQuery({
    queryKey: sorKeys.lookup(code, agency, zone),
    queryFn: () => apiFetch<SorRateResponse>(`/sor/lookup?code=${encodeURIComponent(code)}&agency=${agency}${zone ? `&zone=${zone}` : ''}`),
    enabled: !!code,
    staleTime: 60 * 60 * 1000,
  });
}
```

---

## Rate Limit

| Endpoint | Limit |
|----------|-------|
| `/agencies` | 60/min |
| `/lookup` | 120/min |
| `/load-pdf` | 5/min |

---

## Versioning

- `v1`: Current (CSV + DB dual source, zone-aware lookup)
- `v2` (planned): Multi-agency composite rates, historical rate versions, rate change notifications