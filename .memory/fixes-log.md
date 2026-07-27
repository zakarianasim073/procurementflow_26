# ProcureFlow fixes log

## 2026-07-27 — Phase 3.5 crawler restoration and CPU production image

- Restored the previously untracked `backend/crawler` package from the reviewed
  original development working tree after confirming it did not exist in any
  repository branch, tag, submodule, or sparse-checkout.
- Added an HTTPS/public-host outbound policy, DNS private-address rejection,
  TLS certificate verification, safe download paths and ZIP extraction, and
  structured-log redaction for crawler credentials and document content.
- Split the production CPU dependency entry point from the optional GPU profile,
  pinned direct ML/observability dependencies, installed CPU-only PyTorch,
  Tesseract OCR, and Chromium for the real crawler runtime, and changed the
  backend container to a non-root runtime user.
- Added crawler security tests and Docker-context exclusions for local documents,
  outputs, models, caches, tests, and secrets. No database schema, API contract,
  Works-only rule, production service, DNS, certificate, or credential changed.
- Restored the tracked `backend/loadtest` package from authoritative original
  repository commit `39513fbe7582e7aaf6b9a315ca60c0cd6585ec26`; its test had
  been copied into the deployment snapshot without the implementation.
- Preserved the repository-root/backend filesystem relationship inside the
  container at `/workspace/backend`, which application runtime-path discovery
  requires on Linux, and placed Playwright browsers in a shared non-root path.
- Added the missing pinned `pypdf` runtime dependency discovered by importing
  the actual FastAPI application inside the CPU image.
- Mitigated the React Router 6 open-redirect advisories without a breaking
  Router 7 upgrade by restricting login, OIDC, and SAML post-authentication
  navigation to normalized same-origin application paths.
- Upgraded direct PDF, JWT, multipart-upload, dotenv, and pdfminer-consuming
  dependencies to their current patched compatible releases after the
  production-image vulnerability scan; removed the unused legacy PyPDF2
  distribution.
- Pinned the production image build tooling to `pip==26.1.2` and
  `setuptools==83.0.0`, clearing the compatible build-tool findings from the
  final dependency audit without changing the application framework.
- Removed the remaining TLS-certificate bypasses from the portal explorer and
  material-price crawler so all production HTTP clients verify certificates.
- Declared the production Compose `procurementflow-net` bridge explicitly;
  all-profile rendering previously failed because services referenced an
  undefined top-level network.

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

## 2026-07-27 — Phase 3.6 deterministic lifecycle fixes

- Made repeated FastAPI lifespan runs preserve router-registration state so
  TestClient sessions cannot register the complete API graph repeatedly.
- Made application telemetry setup idempotent across repeated lifespan runs.
- Added application-side UUID generation to the shared ORM primary-key mixin,
  fixing inserts into knowledge-graph and other UUID-backed models.
