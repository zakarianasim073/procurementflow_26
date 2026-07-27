# ProcureFlow Backend Test Suite

## Run everything

```powershell
cd backend
& "C:\Program Files\Python310\python.exe" -m pytest tests\ -q          # ~2 min
```

With core-module coverage (pytest-cov conflicts with the cryptography PyO3 module — use coverage directly):

```powershell
& "$env:APPDATA\Python\Python310\Scripts\coverage.exe" run --source=app.sor,app.core,app.services,app.agents -m pytest tests\ -q
& "$env:APPDATA\Python\Python310\Scripts\coverage.exe" report --include="app/sor/sor_service.py,app/services/pdf_parser.py,app/core/*.py,app/agents/pricing/sor_zone_matcher.py,app/services/intelligence_base.py"
```

## Layout

| File | What it locks |
|---|---|
| `test_golden_sor.py` | **ADR-003 contract** — `find_rate()` match ladder (exact → prefix → suffix → fuzzy 0.42), agency suffix detection, compound A&B codes, all 4 zones, LGED↔PWD C/D swap. 46 + 3 cases from `golden/sor_golden.json` |
| `test_golden_boq.py` | BOQ PDF parser output (64 items, codes/units/quantities) for the real e-GP fixture `golden/fixtures/boq_1290886.pdf` |
| `test_unit_core.py` | `normalize_package_no` (ADR-016 join key), district→zone mapping incl. C↔D swap symmetry, agency detection from code patterns, SOR normalizers |
| `test_api_smoke.py` | health/live/ready, auth login+token+/me, SOR agencies shape, no-500 guarantees |
| `test_jwt_secret_env.py` | T-003: JWT secret env enforcement |
| `test_sql_parameterization.py` | T-005: SQL audit green + bound params |
| `test_upload_validation.py` | T-006: 413/415 + safe ZIP extraction |
| others | Pre-existing agent/brain/API contracts |

## Golden files — the behavioral contract

`golden/sor_golden.json` and `golden/boq_golden.json` freeze current behavior.
**Never regenerate to make a red test green.** Regenerate only inside a ticket
that explicitly changes SOR/BOQ behavior, and review the JSON diff in that PR:

```powershell
& "C:\Program Files\Python310\python.exe" tests\golden\generate_golden.py
```

SOR golden tests load from the committed CSVs (`app/sor/*/rates.csv`) — hermetic,
no database required.

## Fixtures (conftest.py)

- `brain` — started AgentBrain with mock DB session
- `registry`, `echo_agent`, `square_agent`, `fail_agent` — agent-runtime harnesses
- `MockAsyncSession` — in-memory async session stub
- API tests build their own `TestClient(app)` (module-scoped, lifespan-managed)

## Known pre-existing failures (13)

Redis-dependent, brain-infra, and public-prefix API-security tests fail without
infra / pending the public-prefix lockdown ticket. Tracked in the debt register —
do not "fix" them by weakening assertions.
