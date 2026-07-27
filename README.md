# ProcureFlow Enterprise

Bangladesh's AI Procurement Operating System. Transforms public procurement from a document-driven process into an AI-assisted decision-making platform.

## Quick Start

```powershell
# 1. Copy env template and fill in real values
Copy-Item .env.example .env
# Edit .env with your DATABASE_URL, JWT_SECRET, JWT_REFRESH_SECRET, REDIS_URL

# 2. Start PostgreSQL 17 (port 5433) and Redis (port 6379)

# 3. Run migrations
cd backend
alembic upgrade head

# 4. Start the server
Start-Process -WindowStyle Hidden -FilePath "C:\Program Files\Python310\python.exe" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "D:\A1\procurementflow_final_v3\procurementflow\backend"
```

## Architecture

- **Backend**: FastAPI (Python 3.10/3.12) on port 8000
- **Database**: PostgreSQL 17 on port 5433 via asyncpg + SQLAlchemy 2.0
- **Cache/Retry**: Redis on port 6379
- **Object Storage**: MinIO/S3-compatible (optional)
- **Agents**: 51 AI agents for tender intelligence, BOQ comparison, competitor analysis, eligibility checks, etc.
- **Crawler**: Enterprise e-GP crawler framework with plugin system (APP, eTender, Award, eExperience, Debarment)
- **SOR Engine**: 3 agencies (BWDB: 1024 rates, PWD: 2018 rates, LGED: 1503 rates) with zone-aware matching

## Key Domains

- **BOQ Comparison**: Upload or brain-based BOQ comparison against all 3 SOR agencies
- **Tender Acquisition**: Automated e-GP document download and extraction
- **Brain Knowledge**: Stores extracted BOQ/TDS text for AI-powered comparison
- **Agent Runtime**: 51 registered agents with circuit breakers, timeouts, and iteration limits
- **Audit/Retention**: Enterprise-grade audit logging, data retention policies, and webhook management

## Production

See [DEPLOY.md](DEPLOY.md) for production deployment guide.

## License

Proprietary — Zakaria Mohammad Nasim
