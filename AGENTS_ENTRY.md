# ENTRY POINT — Read This First

Any AI model entering this codebase MUST read the following in order before taking any action:

## Mandatory Reading Order

### 1. Memory Index
📄 `.memory/index.md`
- All past discoveries, architecture decisions, known issues
- Critical findings (e.g., agent-db-disconnect, unified-schema-package-no)

### 2. Fixes Log  
📄 `.memory/fixes-log.md`
- Every bug fix, schema change, improvement with exact file paths and line numbers
- Date-stamped entries with rationale and code snippets
- Always check this before editing any file — your fix may already exist

### 3. AGENTS.md
📄 `AGENTS.md` (project root)
- Project structure, key domains, SOR, BOQ, e-GP client knowledge
- Works-only policy, zone mapping, agent architecture

### 4. CLAUDE.md (User Memory)
📄 `C:/Users/znasi/.claude/CLAUDE.md` (system-level)
- User preferences, e-GP knowledge, SOR zone mapping, BOQ parsing notes
- Personal context about the project creator

## Golden Rules

1. **Works only** — Goods, Services, and Supply procurement types are out of scope. All scanning, analysis, and intelligence must filter for `category == "Works"`.
2. **Fix log first** — Before editing any file, check `.memory/fixes-log.md` to see if the issue was already resolved.
3. **No breaking changes** — This is a production codebase with 32K+ NPP records, 115K procurement tenders, 66K awards. Always backward-compatible.
4. **Every fix MUST be logged** — Any code change, schema alteration, or bug fix adds an entry to `.memory/fixes-log.md`.
5. **Restart after agent edits** — Clear `__pycache__/` after editing agent files. Server restart needed.
6. **`session.begin_nested()` for batch operations** — Always wrap individual DB inserts in savepoints to prevent one bad row from killing the batch.

## DB Connection
- PostgreSQL 17, port 5433, database `procureflow_bd`
- Default env: `app.core.config` settings
- `get_session()` returns `AsyncSession` via `sessionmaker`
- SQLAlchemy async with `asyncpg` driver
