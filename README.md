# CreatorOS

An AI marketing agency that remembers, thinks, creates, validates and learns. CreatorOS helps agencies manage many client brands, from understanding a brand through to approved publishing and learning from results.

**Status:** early foundation. Only the database layer and a Gemini service exist; there is no login or frontend yet. See [docs/status.md](docs/status.md).

## Repository layout

| Path | Purpose | State |
| --- | --- | --- |
| `apps/api` | FastAPI backend, Alembic migrations, tests | Started |
| `apps/web` | Next.js frontend | Not started |
| `packages` | Shared types, API client, UI | Not started |
| `infrastructure` | Docker, AWS, monitoring, CI | Not started |
| `docs` | Architecture, database, agents, integrations, security, status | Current |

## Backend setup

Requires Python 3.11 or later and access to a YugabyteDB development cluster. Your IP must be on the cluster's allow list.

```
python -m venv .venv
.venv/Scripts/python -m pip install -r apps/api/requirements.lock
.venv/Scripts/python -m pip install --no-deps -e apps/api
cp .env.example .env    # then fill in real values
```

Run from `apps/api`:

```
../../.venv/Scripts/python -m pytest -q
../../.venv/Scripts/uvicorn app.main:app --reload
../../.venv/Scripts/celery -A app.workers.celery_app worker --pool=solo --loglevel=info
```

The worker needs Memurai or Redis on `REDIS_URL`; Docker is not used locally. To run every backend check, use `scripts/check.ps1`.

Database role setup is described in [docs/database.md](docs/database.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [Agent design](docs/agent-design.md)
- [Integrations](docs/integrations.md)
- [Security](docs/security.md)
- [Status](docs/status.md) and [TODO](TODO.md)
