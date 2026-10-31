# Database

YugabyteDB YSQL is the authoritative store, accessed with SQLAlchemy 2.x, Alembic and `psycopg` 3. Migration `0001` (organizations and brands) exists but has not been applied to `public`, so it can still be revised freely.

## Roles

| Role | Used by | Access |
| --- | --- | --- |
| `admin` | `apps/api/scripts/provision_roles.py`, test schema setup | Administration only; can create roles and bypass row-level security |
| `creatoros_migrator` | Alembic | Owns application tables |
| `creatoros_app` | Running application | Reads and writes data; owns nothing; no bypass of row-level security |

The app role must never own tables, because table owners bypass row-level security by default.

`provision_roles.py` can be re-run, but each run generates new passwords for both application roles and rewrites `.env`.

## Conventions

- UUID primary keys from `gen_random_uuid()`, and UTC timestamps.
- Every tenant-owned row has `organization_id`. Every brand-owned row also has `brand_id`.
- Use composite foreign keys so a row cannot reference another tenant's parent.
- Index commonly filtered columns.
- Store media in S3, never in database binary columns.
- Approval and publishing history is immutable.
- All schema changes go through Alembic and are validated on the real cluster.

## Tenant isolation

Two layers, both required:

1. The backend resolves membership and checks ownership on every operation.
2. Row-level security policies filter on a per-transaction `app.tenant_id` setting.

A live test on 31 October 2026 confirmed on the development cluster that a tenant saw only its row, that no tenant setting returned 0 rows, and that cross-tenant inserts and updates failed. That was a small functional test, not a load test. Policies are not implemented in the app yet.

## Planned tables

| Domain | Tables | Exists |
| --- | --- | --- |
| Identity | `organizations`, `users`, `memberships` | `organizations` only |
| Brands | `brands`, `brand_profiles`, `brand_documents`, `brand_preferences`, `decision_records` | `brands` only |
| Campaigns | `campaigns`, `campaign_scenarios`, `audience_sources`, `audience_insights` | No |
| Content | `content_items`, `creative_features`, `media_assets` | No |
| Quality | `guardian_reviews`, `approvals` | No |
| Publishing | `social_accounts`, `publishing_jobs`, `publishing_logs`, `oauth_states` | No |
| Analytics | `performance_metrics`, `experiments`, `learning_records` | No |
| Operations | `agent_runs`, `agent_events`, `audit_logs`, `usage_records` | No |

Field-level detail is in the technical blueprint, section 4. Each table is added by the phase that first needs it.

## Tests

Integration tests create a throwaway schema as `admin`, migrate it as `creatoros_migrator`, run against it as `creatoros_app`, and drop it. An interrupted run can leave a `creatoros_test_*` schema behind.
