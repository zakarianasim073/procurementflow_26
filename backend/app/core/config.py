import os
import sys
import secrets
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from dotenv import load_dotenv

# Explicitly load .env from the project root directory first
root_dir = Path(__file__).resolve().parent.parent.parent.parent
root_env = root_dir / ".env"
if root_env.exists():
    load_dotenv(dotenv_path=root_env)
else:
    load_dotenv()


def get_default_base_dir() -> str:
    override = os.environ.get("BOQ_BASE_DIR")
    if override:
        return str(Path(override).resolve())
    """Get platform-appropriate base directory"""
    if sys.platform == "win32":
        return str(Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "procurementflow-system")
    # Termux/Android: use shared storage
    sdcard = Path("/sdcard")
    if sdcard.exists():
        return str(sdcard / "tender" / ".procurementflow-system")
    return str(Path.home() / ".procurementflow-system")


def get_tenderai_dir() -> str:
    """Get tenderai output directory - user-facing reports folder (override with TENDERAI_DIR env var)"""
    override = os.environ.get("TENDERAI_DIR")
    if override:
        return str(Path(override).resolve())
    if sys.platform == "win32":
        return str(Path.home() / "Documents" / "tenderai")
    # Termux/Android: Documents/tenderai
    sdcard = Path("/sdcard")
    if sdcard.exists():
        return str(sdcard / "Documents" / "tenderai")
    return str(Path.home() / "tenderai")


_jwt_secret_file = Path(__file__).resolve().parent.parent.parent.parent / ".jwt_secret"


_DEV_ENVIRONMENTS = ("development", "dev", "local", "test")


def get_persistent_jwt_secret() -> str:
    """Load the JWT signing secret.

    JWT_SECRET env var always wins. The .jwt_secret file fallback (generated on
    first boot) is a development convenience only — outside dev environments a
    missing JWT_SECRET aborts startup rather than silently using or creating a
    file-based secret (SEC-01/T-003).
    """
    env_secret = os.environ.get("JWT_SECRET", "").strip()
    if env_secret:
        return env_secret
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    if environment not in _DEV_ENVIRONMENTS:
        raise RuntimeError(
            f"JWT_SECRET environment variable is required when ENVIRONMENT={environment!r} "
            "(file-based .jwt_secret fallback is development-only)"
        )
    if _jwt_secret_file.exists():
        return _jwt_secret_file.read_text().strip()
    new_secret = secrets.token_urlsafe(48)
    _jwt_secret_file.write_text(new_secret)
    return new_secret


class Settings(BaseSettings):
    APP_NAME: str = "Procurement Flow Specialist BD"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: List[str] = []

    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse comma-separated env var into list"""
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return []
        if isinstance(v, str):
            return [i.strip() for i in v.split(',') if i]
        return v

    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET: str = get_persistent_jwt_secret()
    JWT_REFRESH_SECRET: str = os.environ.get("JWT_REFRESH_SECRET", "").strip()
    JWT_PREVIOUS_SECRETS: List[str] = []
    # T-016 (SEC-03): short access expiry; sessions continue via refresh rotation
    JWT_EXPIRE_HOURS: int = 1
    JWT_REFRESH_EXPIRE_DAYS: int = 30
    # Server-side refresh persistence/rotation/reuse-detection; false restores
    # the legacy stateless refresh behavior (rollback path)
    REFRESH_TOKEN_ROTATION: bool = True
    # T-018 (AGT-01): agent execution timeouts and iteration limits prevent CPU
    # exhaustion from misbehaving agents. Individual agents can override via
    # timeout_seconds and max_iterations class attributes.
    AGENT_TIMEOUT_SECONDS: int = 300  # 5 min default per agent
    AGENT_MAX_ITERATIONS: int = 50    # Max iterations per agent.run()
    # T-019 (AGT-02): e-GP crawl rate limiting prevents IP bans from overload.
    # Global token bucket: 10 req/sec refill, 30 token burst (coordinated via Redis).
    EGP_RATE_REQUESTS_PER_SEC: float = 10.0
    EGP_RATE_BURST: int = 30
    # Exponential backoff on 429/5xx: max 3 retries, base 1s with jitter
    EGP_BACKOFF_MAX_RETRIES: int = 3
    EGP_BACKOFF_BASE_SECONDS: float = 1.0
    # Circuit breaker: 5 consecutive failures → cool-down 5 min
    EGP_CIRCUIT_FAILURE_THRESHOLD: int = 5
    EGP_CIRCUIT_COOL_DOWN_SECONDS: int = 300

    # T-017 / W-006 (OBS-01, ADR-012): OpenTelemetry + Prometheus observability.
    # ENABLED BY DEFAULT — Prometheus metrics are always collected; trace export
    # to an OTLP collector happens only when OTEL_EXPORTER_OTLP_ENDPOINT is set.
    OTEL_ENABLED: bool = True
    OTEL_SERVICE_NAME: str = "procureflow-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    EGP_CIRCUIT_COOL_DOWN_SECONDS: int = 300
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    FRONTEND_URL: str = "http://localhost:5173"
    REDIS_URL: str = os.environ.get("REDIS_URL", "").strip()
    OPENCLAW_BASE_URL: str = "http://localhost:18789"
    OPENCLAW_ENABLED: bool = True
    BASE_DIR: str = ""
    TENDERAI_DIR: str = ""
    # W-008 (ADR-015): PPR win-probability ML model registry root. Empty ->
    # defaults to <runtime_dir>/ppr_ml/registry. Override to point at a shared
    # volume when running Celery workers across multiple hosts.
    MODEL_REGISTRY_PATH: str = ""

    # Phase 2: Storage Backend Configuration
    STORAGE_BACKEND: str = os.environ.get("STORAGE_BACKEND", "local")  # local, s3, minio
    UPLOADS_DIR: str = os.environ.get("UPLOADS_DIR", "uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))

    # S3/MinIO Configuration
    # MinIO is the production S3 implementation; one private bucket contains
    # uploads/outputs/templates/embeddings/exports prefixes.
    S3_BUCKET: str = Field(
        default_factory=lambda: os.environ.get(
            "S3_BUCKET",
            os.environ.get("MINIO_BUCKET", "procurementflow-tenders"),
        )
    )
    S3_ENDPOINT: str = os.environ.get("S3_ENDPOINT", "")
    S3_ACCESS_KEY: str = os.environ.get("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.environ.get("S3_SECRET_KEY", "")
    S3_REGION: str = os.environ.get("S3_REGION", "us-east-1")

    # Storage Quotas
    STORAGE_QUOTA_PER_TENANT_GB: int = int(os.environ.get("STORAGE_QUOTA_PER_TENANT_GB", "100"))
    CLEANUP_JOB_ENABLED: bool = os.environ.get("CLEANUP_JOB_ENABLED", "true").lower() in ("true", "1", "yes")
    CLEANUP_JOB_INTERVAL_DAYS: int = int(os.environ.get("CLEANUP_JOB_INTERVAL_DAYS", "30"))

    # Audit Logging
    AUDIT_LOGGING_ENABLED: bool = os.environ.get("AUDIT_LOGGING_ENABLED", "true").lower() in ("true", "1", "yes")
    # W-009 (ADR-001): Redis-backed brain knowledge cache. Redis is the shared
    # cross-replica cache; PostgreSQL remains the durable backing store. When
    # Redis is unavailable the system degrades to PostgreSQL-only automatically.
    KNOWLEDGE_CACHE_ENABLED: bool = True
    KNOWLEDGE_CACHE_TTL_HOT: int = 3600  # hot entry types (tender_document, boq_text, tds_text)
    KNOWLEDGE_CACHE_TTL_COLD: int = 86400  # everything else
    KNOWLEDGE_CACHE_L1_TTL_MS: int = 10  # in-process L1 TTL (hot-key absorb)
    KNOWLEDGE_CACHE_L1_MAX: int = 2000  # L1 capacity (was the in-memory LRU cap)
    # T-034 (ENT-07): PostgreSQL read replica. When set, read-heavy analytics
    # and dashboard queries route to the replica; falls back to primary when empty.
    # Alembic and write paths always use DATABASE_URL (never the replica).
    READ_REPLICA_URL: str = ""
    # Alert threshold: log a WARNING when the replica lag exceeds this many seconds.
    REPLICA_LAG_WARN_SECONDS: int = 30
    # T-013 (API-01): deprecation window — true restores the old synchronous
    # /boq/compare response instead of the async 202 + job_id flow (ADR-004).
    BOQ_SYNC_FALLBACK: bool = False
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "").strip()

    # W-016: Database pool sizing based on deployment topology.
    # PgBouncer connections are aggregators; each transaction goes through a single pool connection,
    # so we reduce the app-side pool to avoid over-subscription. Direct connections should use
    # larger pools for optimal parallelism within this single-process backend.
    POOL_SIZE: int = int(os.environ.get("POOL_SIZE", "5"))  # legacy default; 20 when via_pgbouncer=False
    MAX_OVERFLOW: int = int(os.environ.get("MAX_OVERFLOW", "10"))  # legacy default; 40 when via_pgbouncer=False
# Fix defaults in production PGBOUNCER_URL mode
    @field_validator(
        'POOL_SIZE', 'MAX_OVERFLOW', mode='before'
    )
    @classmethod
    def _fix_pg_pool(cls, v, info):
        # In Pydantic v2, we can't access other fields during validation easily
        # Check PGBOUNCER_URL from environment directly
        pgbouncer_url = os.environ.get("PGBOUNCER_URL", "").strip()
        using_pgbouncer = bool(pgbouncer_url)
        
        if using_pgbouncer:
            # In production with PgBouncer, reduce pools to 5/10
            if info.field_name == 'POOL_SIZE':
                return int(os.environ.get("POOL_SIZE", "5"))
            if info.field_name == 'MAX_OVERFLOW':
                return int(os.environ.get("MAX_OVERFLOW", "10"))
        
        # Legacy fallback: via_pgbouncer=False => 20/40
        if info.field_name == 'POOL_SIZE' and v == 5:
            return 20
        if info.field_name == 'MAX_OVERFLOW' and v == 10:
            return 40
        return v
    SYSTEM_USER_PASSWORD: str = os.environ.get("SYSTEM_USER_PASSWORD", "").strip() or secrets.token_urlsafe(32)
    REQUIRE_API_AUTH: bool = True
    PUBLIC_API_PREFIXES: List[str] = [
        "/api/health",
        "/api/ready",
        "/api/live",
        "/api/metrics",  # T-017 Prometheus scrape endpoint
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v2/enterprise/capabilities",
        "/api/openapi.json",
        "/api/docs",
        "/docs",
        "/openapi.json",
        # ENT-02: SSO login flow endpoints must be reachable without an
        # existing session (you cannot hold a bearer token before logging in).
        # The router's own dependencies (get_current_user) enforce auth where
        # required (e.g. IdP config management); the login callbacks do not.
        "/api/v2/sso/oidc/init",
        "/api/v2/sso/oidc/callback",
        "/api/v2/sso/saml/acs",
        "/api/v2/sso/logout",
    ]

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("JWT_PREVIOUS_SECRETS", mode="before")
    @classmethod
    def parse_jwt_previous_secrets(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [secret.strip() for secret in v.split(",") if secret.strip()]
        return v



_REQUIRED_PRODUCTION_VARS = ("DATABASE_URL", "JWT_SECRET", "JWT_REFRESH_SECRET", "REDIS_URL")


def validate_production_settings() -> None:
    """Fail fast outside dev when a required variable is unset (INF-03/T-008).

    Names every missing variable in one error instead of failing late and
    cryptically at first use.
    """
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    if environment in _DEV_ENVIRONMENTS:
        return
    missing = [name for name in _REQUIRED_PRODUCTION_VARS if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s) for ENVIRONMENT={environment!r}: "
            + ", ".join(missing)
            + " — see DEPLOY.md 'Configuration' and .env.example"
        )
    # SEC-04: JWT_SECRET and JWT_REFRESH_SECRET must be independent.
    secret = os.environ.get("JWT_SECRET", "").strip()
    refresh = os.environ.get("JWT_REFRESH_SECRET", "").strip()
    if secret and refresh and secret == refresh:
        raise RuntimeError(
            "JWT_SECRET and JWT_REFRESH_SECRET must be different values "
            "in production (SEC-04)."
        )


def get_settings() -> Settings:
    s = Settings()
    if not s.BASE_DIR:
        s.BASE_DIR = get_default_base_dir()
    if not s.TENDERAI_DIR:
        s.TENDERAI_DIR = get_tenderai_dir()
    # DEV convenience: in dev, if JWT_REFRESH_SECRET is empty, derive it from
    # JWT_SECRET with a suffix so refresh tokens work without extra config.
    if not s.JWT_REFRESH_SECRET and s.ENVIRONMENT in _DEV_ENVIRONMENTS:
        s = s.__class__(**{**s.__dict__, "JWT_REFRESH_SECRET": s.JWT_SECRET + "-refresh"})
    return s


validate_production_settings()
settings = get_settings()
# Normalize ALLOWED_ORIGINS: if loaded as a comma-separated string, split into a list
if isinstance(settings.ALLOWED_ORIGINS, str):
    settings.ALLOWED_ORIGINS = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(',') if origin]
