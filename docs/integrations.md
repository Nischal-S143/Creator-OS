# Integrations

Every provider sits behind an adapter in `apps/api/app/integrations`. "Tested" below means run against the real service.

| Provider | State | Credentials needed |
| --- | --- | --- |
| YugabyteDB | Connected as the restricted app role; tested | `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `ADMIN_DATABASE_URL`, root certificate |
| Gemini | Live call and fake-client tests pass | `GEMINI_API_KEY`, `GEMINI_MODEL` |
| Meko | App client tested live, including two-brand leakage | `MEKO_API_KEY`, `MEKO_MCP_URL` |
| Login | Local JSON file; no external provider | None |
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
- Auth: `Authorization: Bearer <key>` plus a `User-Agent` header, per the [API keys docs](https://docs.mekodata.ai/reference/api-keys/). A live connection on 31 October 2026 reached Meko MCP 3.2.4 with 42 tools, and an invalid key got 401.
- **A key is account-wide: it can reach every datapack on the account, and the docs describe no way to limit it.** Meko therefore does not separate clients for us. The backend must, and the key must never leave the server.
- Keys also expose destructive and unrelated tools, such as `memory_delete_all`, `datapack_delete` and `amp_*`. The adapter must allowlist only the tools agents need.
- Before implementing: read each tool's live schema, and do not rely on this list.
- `datapack_id` is optional on memory tools: per the live schema, `memory_search` falls back to the caller's default datapack, and it searches across agents, so `agent_id` does not separate brands. The adapter must require a backend-resolved `datapack_id` on every call and refuse calls without one.
- Meko extracts memories from the input side of a conversation turn, so that side holds only the agent and its task, never document text. Metadata must be a JSON string.
- The free Meko plan refused new datapacks on 31 October 2026 with `FREE_TIER_DATAPACK_LIMIT`. Per-brand datapacks, which real client data needs, require a plan that allows them.
- `MEKO_SHARED_DATAPACK_ID` uses one datapack, such as the default, for all brands in development, with a brand tag filter. It is refused elsewhere.
- The backend resolves brand-to-datapack mapping. The frontend never supplies a datapack ID.

## Authentication

Email and password accounts live in `data/auth/accounts.json`, by project decision. All business data, including a matching `users` row, lives in YugabyteDB. The API signs its own ES256 tokens with `data/auth/signing_key.pem`, and tokens last 1 hour.

The login code sits behind a small interface, so a hosted provider or database table can replace it. Because accounts are in one local file, it supports only one API process on one server.

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
