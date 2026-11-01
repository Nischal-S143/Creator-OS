# CreatorOS

An AI marketing agency that remembers, thinks, creates, validates and learns. CreatorOS helps agencies manage many client brands, from understanding a brand through to approved publishing and learning from results.

**Status:** foundation. Sign-up, agencies, client brands, members and roles work end to end. AI agents and the product features are not built yet. See [docs/status.md](docs/status.md).

## Repository layout

| Path | Purpose | State |
| --- | --- | --- |
| `apps/api` | FastAPI backend, Alembic migrations, tests | Started |
| `apps/web` | Next.js frontend | Started |
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

## Run the app

Start the API from `apps/api`, then the web app from `apps/web` in a second terminal. Open <http://localhost:3000>.

```
../../.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

```
npm install
npm run dev
```

The web app calls the API at `http://127.0.0.1:8000` unless `API_URL` is set. Accounts are stored in `data/auth`, and everything else in YugabyteDB.

Browser tests expect both servers running, with Chrome installed:

```
npm run test:e2e
```

## Deployment

Vercel deploys this repository as one project with two services, configured in [vercel.json](vercel.json).

| Service | Root | Public path | Reached by |
| --- | --- | --- | --- |
| `web` | `apps/web` | `/(.*)`, the whole site | The browser |
| `api` | `apps/api` | None; internal only | `web`, through a service binding |

The `web` service declares a binding on `api`, so Vercel injects the API's internal URL into `API_URL` at request time. Do not set `API_URL` as a project environment variable; the binding supplies it. `backendUrl` in `apps/web/lib/server/session.ts` reads it per request, which is why only route handlers call the API: bindings do not resolve during the build or in `proxy.ts`.

FastAPI stays internal on purpose, because the browser never calls it. `apps/web/app/api/backend/[...path]/route.ts` is its only caller, and it attaches the session token and allows only the `me` and `organizations` route areas, which keeps `POST /api/v1/ai/test` out of reach from a browser (finding C3 in [docs/security.md](docs/security.md)).

Run both services together locally with `vercel dev`, which injects the binding variables.

Neither service covers the Celery worker and Redis, which need a long-running host, or the `data/auth` account files, which a Vercel deployment cannot keep. See [docs/status.md](docs/status.md).

## Agents

CreatorOS runs specialist agents as LangGraph workflow steps, each with typed state, Pydantic-validated outputs, and a fixed list of allowed tools. Agents cannot call each other directly or bypass FastAPI's authorization, tenant and approval checks.

| Agent | Responsibility | Status |
| --- | --- | --- |
| Research | Authorized public research, competitor themes, audience questions | Working |
| Script | Hooks, scripts, captions, CTAs, platform versions | Working |
| Visual | Scene plans, image/video prompts, asset selection | Working |
| Brand Guardian | Independent review (`PASS` / `NEEDS_REVIEW` / `BLOCKED`) of voice, visuals, claims and provenance | Working |
| Ad Creation | Ad copy and variants; never launches ads or spends money | Working |
| Market Gap | Unmet-topic hypotheses with evidence, no forecasts | Working |
| Strategy | Pillars, scenarios and experiments from brand context | Not built |
| Voice, Video | Voiceover, subtitles, FFmpeg assembly, platform variants | Not built |
| Publishing | Requests and tracks publishing; re-checks approval, holds no social tokens itself | Built, not tested against a real platform |
| Analytics, Feedback | Measured metrics kept apart from AI hypotheses; feeds a human-approved Learning Ledger | Built |

Rules every agent follows:

- Gemini never invents numeric forecasts; measured facts and AI hypotheses are kept apart.
- Nothing becomes durable brand memory without human approval, and every approved item keeps its source.
- Uploaded documents and social content are untrusted data, never instructions.
- A LangGraph interrupt pauses a run for human approval and resumes only after backend authorization. Checkpoints live separately from Meko.

Full responsibilities, required outputs, and the complete agent list: [docs/agent-design.md](docs/agent-design.md).

## Meko (agent memory)

Meko is the long-term memory service agents read and write through an MCP connection at `https://mcp.mekodata.ai/mcp`, reached through one adapter, `apps/api/app/integrations/meko/client.py`.

- A Meko API key can reach every datapack on the account — Meko does not separate clients, so the backend must. Every memory call requires a backend-resolved `datapack_id`; the frontend never supplies one.
- The adapter allowlists five tools: `conversation_add_message`, `conversation_create`, `datapack_create`, `memory_add`, `memory_search`. Destructive or unrelated tools a key can otherwise reach, such as `memory_delete_all`, `datapack_delete` and `amp_*`, stay out of reach.
- Meko extracts memories from the input side of a conversation turn, so an agent's logged turn carries only its name and task on that side, never raw document text or other untrusted content.
- `MEKO_SHARED_DATAPACK_ID` puts every brand in one datapack behind a brand-tag filter, for development only; `get_meko()` raises if it is set outside `app_env == "development"`. Real client data needs one datapack per brand, which needs a Meko plan beyond the free tier (the free tier refuses new datapacks).
- Agents may only propose memories. An item becomes durable brand context after human approval, never automatically.

Environment: `MEKO_API_KEY`, `MEKO_MCP_URL`, and in development only, `MEKO_SHARED_DATAPACK_ID`. Live-test results and the full tool list: [docs/integrations.md](docs/integrations.md#meko).

## YugabyteDB (database)

YugabyteDB YSQL is the single authoritative store for business records, approvals, audit history and LangGraph checkpoints, accessed with SQLAlchemy 2.x, Alembic and `psycopg` 3.

- Two roles: `creatoros_migrator` owns every table and is the only role Alembic runs as; `creatoros_app` reads and writes but owns nothing, so table ownership can never bypass row-level security. `apps/api/scripts/provision_roles.py` (re)creates both roles and rewrites `.env` with new passwords on every run.
- Tenant isolation is two layers, both required: the backend checks membership and ownership on every operation, and row-level security policies filter on a per-transaction `app.tenant_id` setting. A live test on the development cluster confirmed cross-tenant reads, inserts and updates all fail; see `apps/api/tests/test_tenant_isolation.py`.
- `content_versions` and `guardian_reviews` are insert/read only for `creatoros_app`, and an approval can change only while pending — both enforced by the database, not just application code.
- Connects with `sslmode=require` today; the target is `verify-full`, which needs the cluster root certificate. Automatic prepared statements stay off, because YugabyteDB's connection manager can switch backends mid-connection and lose them.
- The current cluster is a 1-node development sandbox (2 vCPU, 4 GB memory, 10 GB disk) capped at 180 tablets. Interrupted test runs can leave `creatoros_test_*` schemas behind that eat into that cap.

Migrate with:

```
../../.venv/Scripts/alembic upgrade head
```

Roles, conventions and the planned table list: [docs/database.md](docs/database.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [Agent design](docs/agent-design.md)
- [Integrations](docs/integrations.md)
- [Security](docs/security.md)
- [Status](docs/status.md) and [TODO](TODO.md)
