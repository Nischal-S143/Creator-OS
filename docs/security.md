# Security

The API must stay local-only until login and tenant isolation exist. This file tracks the audit from 31 October 2026 and the controls required later.

## Open findings

| ID | Severity | Finding | Status |
| --- | --- | --- | --- |
| C1 | High | Credentials exposed in chat | Admin password rotated. New Gemini key installed; the old key must be deleted in Google. The new keys were also pasted in chat |
| C2 | High | App used the `admin` database account | Fixed for local development; 7 role tests pass. The admin login still sits in the development `.env` |
| C3 | High | `POST /api/v1/ai/test` has no login or rate limit | Partly fixed: refused without `INTERNAL_API_KEY`. Rate limits are still open, and the browser proxy cannot reach it |
| C4 | High | No login, roles or membership checks | Fixed; tested with isolation and browser tests |
| C5 | Medium | `sslmode=require` does not verify the server | Open; needs root certificate |
| C6 | Medium | Raw Gemini error text returned to callers | Fixed; tested |
| C7 | Medium | Dependencies unpinned | Lockfile added; `pyproject.toml` ranges remain open |
| C8 | Low | `/health/db` returns the full database version | Fixed; tested |
| C9 | Low | `/docs` and `/openapi.json` are public | Fixed outside development; tested |
| C10 | Low | `.env` ignore rule was untested | Fixed; tested. Pre-commit hook is local, not shared |
| C11 | Low | No virtual environment | Fixed |

Also open:

- The GitHub repo is public by decision. Everything pushed, including this file and commit author details, is visible to anyone.
- Accounts in a local JSON file limit the API to one process and one server, and a lost file loses every login. Back it up, or move it before production.
- Sign-up does not verify email ownership yet, so someone could register another person's address and later receive that person's invitation.
- There is no password reset yet. The login lockout resets when the API restarts, and it locks by email, so someone can deliberately lock another user out for 15 minutes.
- The Meko key is account-wide, so a bug in our datapack mapping could expose one client's memory to another. Use an allowlist of tools and the two-brand leakage test.
- The replacement Gemini key and the Meko key were pasted into chat. Rotate them before real client data or a public launch.
- The development `.env` holds an admin login alongside the runtime login. It should move out once setup is stable.

## Rules

- Passwords are stored only as scrypt hashes. The `data/` folder must never be committed.
- Never commit `.env`, log secrets, or send Gemini or Meko keys to the browser.
- Never trust frontend tenant, brand or datapack IDs.
- Never publish without valid human approval.
- Secret scanning uses `detect-secrets`, with `.secrets.baseline` listing reviewed placeholders. It does not read PDFs.

## Controls required before each feature

| Feature | Required control |
| --- | --- |
| Any customer AI feature | Per-tenant budgets, rate limits, usage records, concurrency caps |
| Document upload and social content | Treat as untrusted; no tools on that model call; file type and size checks; signed, expiring URLs |
| Learning and memory | Evidence and human approval for every lesson, so hostile content cannot plant false lessons |
| Meko | Backend-resolved datapacks and an automated two-brand leakage test |
| Approval | Hash of text and media stored with the approval and compared at publish time |
| Publishing | Agents hold no tokens; service re-checks organization, brand, account, Guardian, approval, version, schedule, token and idempotency key |
| Social OAuth | State validation, PKCE where supported, KMS-backed token encryption, minimum scopes, webhook signature checks |
| Cross-Brand | Opt-in, minimum cohorts, suppression, audit logs, leakage and re-identification tests |
| Production | Rate limiting, backups and restore tests, retention and deletion, independent penetration test |

The audit was a manual review plus Bandit and `pip-audit` scans. It was not a penetration test and did not cover cloud settings.
