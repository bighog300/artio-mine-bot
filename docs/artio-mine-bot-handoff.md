# 🧾 Handoff Document — artio-mine-bot API & Mining System

## 🎯 Project Overview

This is a **FastAPI-based backend** for a mining pipeline that:

- Fetches and processes external data (“mining”)
- Transforms and stores structured records in PostgreSQL
- Exposes API endpoints for interacting with mined data

The system is:
- Fully async (SQLAlchemy 2.x + asyncpg)
- Designed for Docker and serverless environments
- Uses dependency-injected DB sessions
- Has a modular mining pipeline

---

## 🧠 Current Architecture

### API Layer
- Entry: `api/index.py`
- Main app: `app/api/main.py`
- Routes: `app/api/routes/*`
- Dependencies: `app/api/deps.py`

### Database Layer
- Config: `app/config.py`
- Engine/session: `app/db/database.py`
- CRUD: `app/db/crud.py`

### Mining Logic
- Orchestrated via routes (likely `mine.py`)
- Pipeline:
  Fetch → Parse → Transform → Store

---

## ⚙️ Key Technical Decisions

### Async-Only Database
- Uses create_async_engine, AsyncSession, asyncpg
- DATABASE_URL must be:
  postgresql+asyncpg://...

---

### Dependency Injection Pattern

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

Important:
- No auto-commit
- No auto-rollback
- Writes must explicitly call: await db.commit()

---

### Docker-First Setup
- Uses container networking (db host ≠ localhost)
- Healthchecks enabled

---

## ⚠️ Known Constraints

- Strict DB URL validation (fails fast)
- Manual transaction management required
- Mining likely runs inside API context
- Potential N+1 queries
- Migrations not fully implemented

---

## 🚀 Strengths

- Clean async architecture
- Correct dependency injection
- Improved logging
- Docker-compatible

---

## 🛠️ Priority Improvements

1. Mining pipeline hardening (logging, retries, batching)
2. Performance (remove N+1 queries)
3. Reliability (retry + concurrency control)
4. Migrations (replace create_all)
5. Testing (pytest-asyncio)

---

## 🔄 Mining Flow

Trigger → Fetch → Parse → Transform → Store

Risks:
- Duplicate processing
- Limited observability
- Weak failure isolation

---

## ✅ Startup Checklist

- Uses postgresql+asyncpg://
- Async DB engine/session only
- No sync DB usage
- Environment variables aligned
- Health endpoint works

---

## 🧪 Run Instructions

### Docker
docker-compose up --build

### Local
uvicorn api.index:app --reload

---

## 📌 Expectations

- Do NOT introduce sync DB usage
- Always explicitly commit writes
- Keep startup lightweight
- Focus on mining improvements

---

## 💬 Suggested Next Work

- Move mining to service layer
- Add batching + deduplication
- Add metrics/logging
- Optimize DB queries
- Add background processing

---

## 🧾 TL;DR

The system is stable.

Next focus:
- Performance
- Reliability
- Mining pipeline design
