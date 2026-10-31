# Integrations

Every provider sits behind an adapter in `apps/api/app/integrations`. "Tested" below means run against the real service.

| Provider | State | Credentials needed |
| --- | --- | --- |
| YugabyteDB | Connected as the restricted app role; tested | `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `ADMIN_DATABASE_URL`, root certificate |
| Gemini | Live call and fake-client tests pass | `GEMINI_API_KEY`, `GEMINI_MODEL` |
| Meko | Not integrated in the app | `MEKO_API_KEY`, `MEKO_MCP_URL` |
| Supabase Auth | Chosen; not integrated | Project URL, issuer, audience |
| Redis (Memurai) and Celery | Test worker runs a task through the broker; no real jobs yet | `REDIS_URL` |
| S3 | Not integrated | Bucket and AWS credentials |
| Social platforms | Not integrated | Developer apps, per platform |

## YugabyteDB

- Connects with `sslmode=require` today; the target is `verify-full`, which needs the cluster root certificate.
- The client confirmed TLS in use, and a plaintext connection was refused. The server's `pg_stat_ssl` reports `false`, probably because of the connection manager; this is unconfirmed.

## Gemini

- Uses the official `google-genai` SDK. Model selection is configuration.
- `gemini-3.5-flash-lite` answered in about 2 to 4 s. `gemini-3.8-flash` took 95 to 143 s on a trivial prompt on 31 October 2026. Check availability before production.
- Still needed: usage and cost logging, per-agent models, fallback models.

## Meko

- Endpoint: `https://mcp.mekodata.ai/mcp`. Docs: <https://docs.mekodata.ai/>.
- A Claude Code MCP connection exposes tools including `context_search`, `memory_add`, `memory_search`, `memory_promote`, `datapack_create`, `knowledgebase_search` and `knowledgebase_upload_document`.
- That connection is a development tool, not the app's. The app needs its own key and client.
- Before implementing: read each tool's live schema, authentication and permission model, and do not rely on this list.
- Datapack separation is unconfirmed. A two-brand leakage test must pass before client memory is stored.
- The backend resolves brand-to-datapack mapping. The frontend never supplies a datapack ID.

## Authentication

Supabase Auth. FastAPI validates tokens and resolves membership and role on the server.

## Social platforms

Read on 31 October 2026; re-check before building.

| Platform | Known | Source |
| --- | --- | --- |
| Instagram | Metrics can lag up to 48 hours; missing data returns empty, not 0; story metrics last 24 hours; average Reels watch time is available, with no documented full retention curve | [Media insights](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights/) |
| Instagram | Professional accounts only; the page states both 100 and 50 posts per 24 hours; App Review needs are not stated there | [Content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| YouTube | Default 100 `videos.insert` and 100 `search.list` calls, plus 10,000 units a day for other endpoints; more needs an audit | [Quota and audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits) |
| TikTok | Unconfirmed; the docs could not be loaded | <https://developers.tiktok.com/doc/content-posting-api-get-started> |

Start with test accounts and only the scopes that have been granted.

## Local tooling

Checked on this machine: Node 22.20, npm 10.9, Python 3.11.7, FFmpeg and Memurai (Redis-compatible) present. Local development does not use Docker. On Windows, Celery's default prefork pool is unsupported, so workers run with `--pool=solo` or `--pool=threads`.
