# ProcureFlow fixes log

## 2026-07-27 — Phase 3 production Compose remediation

- Removed every private host-published port; only container Nginx publishes
  TCP 80 and 443.
- Pinned all infrastructure and Dockerfile base images to explicit versions.
- Added authenticated persistent Redis and propagated its protected runtime URL
  to FastAPI, Celery and Flower.
- Standardized private MinIO storage on the `procurementflow-tenders` bucket
  with documented object-category prefixes and a private bucket initializer.
- Switched PostgreSQL to a PostgreSQL 17 pgvector image and prepared required
  extensions without initializing a database or running migrations.
- Added a direct-to-PostgreSQL, profile-gated migration service.
- Corrected production domains, explicit CORS origins, HTTP-only pre-certificate
  Nginx routing, optional observability profiles, protected secret generation,
  immutable manual CI/CD workflows, and production Compose policy validation.
- No production container, datastore, migration, DNS record, or certificate was
  started or changed during this remediation.
- Added the ten MPA HTML entry files already referenced by `vite.config.ts`;
  the prior clean deployment snapshot could not produce a frontend build.
- Corrected production CORS serialization to a JSON list accepted by
  pydantic-settings while retaining only the two explicit HTTPS origins.
- Explicitly injects the protected production environment file into FastAPI,
  every Celery worker and the migration service; Compose interpolation alone
  does not populate arbitrary container environment variables.
