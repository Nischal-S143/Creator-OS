# CreatorOS implementation plan

Based on `CreatorOS_Final_Blueprint_Research_Security_Audit.pdf`. Status: superseded by `TODO.md`, which follows the phase order in the project brief. Kept for its per-step test ideas.

Scope: the complete CreatorOS, covering every module in the blueprint across 11 phases and 80 steps. Phases 1 to 5 prove the core loop first; Phases 6 to 11 complete the platform. Nothing is cut.

## Working rules

1. One step at a time, in order. A step is done only when its test passes.
2. Each step reports what changed, the test command and the actual result.
3. If a test fails, fix it before moving on. If it can't be fixed, stop and report it.
4. Stop at each phase gate for review.
5. Tests that touch the database or Gemini run against the real development services. Social platforms use a fake publisher until step 4.7.
6. Every migration, tenant table and service keeps the blueprint rules: tenant checks, no hardcoded secrets, Pydantic validation of model output.

## Agent team

A LangGraph supervisor runs these as defined workflow nodes with fixed inputs, outputs and allowed tools. They do not call each other freely. All are built on the shared foundation from Phases 1 to 3.

| Agent | Job | Output | Cannot | Built in |
| --- | --- | --- | --- | --- |
| Research | Authorized public research, competitor themes, audience questions | Brief with sources and limitations | Treat unverified claims as fact | Step 7.1 |
| Market Gap | Compare research against competitors and the brand's content to find unmet topics | Ranked gaps with evidence and confidence | Claim a gap is proven; invent market numbers | Step 7.6 |
| Scripting | Hooks, scripts, captions, CTAs, platform versions | Versioned draft | Approve its own work | Step 8.1 |
| Ad Creation | Ad copy, creative variants and formats from an approved brief | Ad variants ready for review | Launch ads or spend money | Steps 8.8, 8.9 |
| Media Upload | Prepare media for each platform, schedule and track posts | Scheduled job and status | Hold social tokens or post without approval of the exact version | Step 4.8 |

The Media Upload agent requests publishing, and the publishing service re-checks approval and performs the upload.

## Phase 1: Harden

Gate: all 4 high-severity audit findings closed (C1 to C4; C4 closes in Phase 2, see note).

| Step | Work | Test that must pass |
| --- | --- | --- |
| 1.1 | Initialise Git, `.gitignore`, secret scanning | `git check-ignore .env` confirms it; gitleaks finds nothing staged |
| 1.2 | Move code to `apps/api`, add virtual environment, `pyproject.toml` and lockfile | Existing 9 integration tests pass from the new location |
| 1.3 | Switch `psycopg2` to `psycopg` 3 | 9 tests pass; `/health/db` returns 200 |
| 1.4 | Rotate DB password and Gemini key (you); use `verify-full` with the root certificate | Connection succeeds; a connection with a wrong certificate is refused |
| 1.5 | Create `creatoros_migrator` and non-owner `creatoros_app` roles | App role can read and write data; it cannot create tables or roles |
| 1.6 | Restrict AI test endpoint, return generic errors, reduce `/health/db`, disable docs in production | Unauthenticated AI call refused; no upstream text or DB version in responses; docs 404 in production mode |
| 1.7 | Add Gemini unit tests with a fake client | Retry, timeout, non-retryable error, invalid JSON and no-key-in-errors cases pass |
| 1.8 | Add `CLAUDE.md`, README, Bandit and `pip-audit` in one check script | Script exits clean from a fresh environment |

Note: C4 (no login or roles) is a Phase 2 deliverable. Until it closes, the API stays local only.

## Phase 2: Foundation

Gate: cross-tenant tests pass on the real cluster.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 2.1 | Add `users` and `memberships`; link `owner_id` to users; add organization `plan` and `status` | Migration up, down and up again; constraints reject bad references |
| 2.2 | Validate OIDC access tokens | Valid token accepted; expired, tampered, wrong-issuer and wrong-audience refused |
| 2.3 | Add per-request tenant context and row-level security on every tenant table | Non-member gets 403; missing tenant returns 0 rows; cross-tenant read, insert, update and delete fail |
| 2.4 | Add the role permission matrix | Table-driven test covers every role and action |
| 2.5 | Add organization, member and brand APIs | Full API tests, including another tenant's IDs returning 404 |
| 2.6 | Add `usage_records`, per-tenant AI budget and rate limits | Tokens recorded per call; over-budget and over-rate calls refused before Gemini is called |
| 2.7 | Add append-only `audit_logs` | Actions are logged; the app role cannot update or delete log rows |
| 2.8 | Create Next.js app with login and organization and brand screens, plus shared `shared-types`, `api-client` and `ui` packages | Type-check and lint pass; browser test covers sign-in to creating a brand |
| 2.9 | Start platform app review (you, with material from me) | Application submitted; not a code test |

## Phase 3: Vertical slice

Gate: two-brand Meko leakage test passes, and context persists across separate runs.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 3.1 | Add Docker Compose with Redis and Celery, with job status stored in YugabyteDB | A job runs, retries a transient failure and records its status |
| 3.2 | Add storage adapter with tenant-scoped keys and signed URLs | Wrong-tenant key refused; signed URL expires; bad file type refused |
| 3.3 | Add brand document upload and text extraction | Sample PDF extracted; malformed file fails cleanly |
| 3.4 | Add Gemini brand profile extraction, with versioned profiles and approval | Output validated; injected text in a document changes no instructions; only allowed roles approve |
| 3.5 | Add Meko adapter, with tools discovered from the live server and brand-to-datapack mapping | Write and read back; frontend cannot choose a datapack |
| 3.6 | Run the Meko two-brand leakage test | Brand B can never retrieve Brand A's content |
| 3.7 | Add campaigns and a LangGraph flow producing three ideas, with checkpoints | Three valid ideas; run resumes after a worker restart |
| 3.8 | Add `agent_runs`, `agent_events` and live progress over SSE | Run state survives a dropped browser connection; events show correlation IDs |
| 3.9 | Add brand preferences, decision records, client feedback and rejected ideas, memory corrections and the Brand Brain screen | Approved preference is recalled with its source; outdated knowledge can be corrected |
| 3.10 | Add dashboard screens and run history | Browser test covers the blueprint's section 20 flow end to end |

## Phase 4: Approve and publish

Gate: publishing is impossible without approval of the exact version.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 4.1 | Add versioned content items and text generation | New edit creates a new version; old versions cannot change |
| 4.2 | Add text and claims Guardian | Seeded violations detected with evidence; Guardian cannot approve |
| 4.3 | Add approval requests with a hash of text and media | Changed content invalidates approval; only allowed roles decide |
| 4.4 | Add `social_accounts` with KMS-encrypted tokens | Token never appears in logs, responses or agent state |
| 4.5 | Add `SocialPublisher` contract and fake publisher | Contract test suite passes |
| 4.6 | Add publishing service with outbox, idempotency and reconciliation | Duplicate job posts once; uncertain result reconciles before retry; every bypass attempt refused |
| 4.7 | Add first real adapter, on a test account | A real test post publishes after approval; depends on platform access |
| 4.8 | Add Media Upload agent: media checks per platform, scheduling, status tracking | Wrong format is caught before upload; agent holds no token; unapproved request refused |

## Phase 5: Learn

Gate: an approved lesson is recalled with its source in a new campaign.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 5.1 | Add `performance_metrics` and `feedback_checkpoints`, scheduled at 48 hours, 7 days and 30 days | Publishing creates checkpoints once; re-running creates no duplicates |
| 5.2 | Add metric collection | Empty data stored as unavailable, not 0; expired token handled without failing the run |
| 5.3 | Add baseline comparison in code | Known inputs give exact expected results; small samples give `insufficient_data` |
| 5.4 | Add Gemini report with facts and hypotheses kept separate | Invented figures rejected; hostile comment text cannot alter output rules |
| 5.5 | Add Learning Ledger with approval, review date and replacement | Unapproved lesson never reaches agents; expired lesson is flagged; another brand cannot see it |
| 5.6 | Promote approved lessons to Meko and feed agents | New campaign uses the lesson and shows its source |
| 5.7 | Add report screens, notifications and learning scorecard | Browser test covers publish to approved lesson |
| 5.8 | Run full end-to-end and security pass, including an updated audit | Blueprint section 16 scenarios pass; no open high-severity findings |

## Phase 6: Audience Intelligence

Gate: a human can approve an audience topic as a campaign opportunity.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 6.1 | Add `audience_sources` and authorized comment ingestion | Only connected accounts and granted scopes are read |
| 6.2 | Normalize, remove duplicates and filter spam | Seeded duplicates and spam removed |
| 6.3 | Classify topic, intent and sentiment; cluster repeated questions | Labelled sample meets an agreed accuracy; hostile comments change no instructions |
| 6.4 | Score opportunities by frequency, relevance and content gap | Known inputs give exact expected scores |
| 6.5 | Add insight screens and convert an approved topic into a campaign | Browser test covers insight to campaign |

## Phase 7: Campaign Flight Simulator and Research

Gate: campaign strategies are comparable and explainable.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 7.1 | Add Research agent with source capture | Each claim links to a source; limitations stated |
| 7.2 | Add campaign brief and three generated scenarios | Scenarios validate and use brand context |
| 7.3 | Add scoring for fit, relevance, feasibility, differentiation, cost, risk and evidence | Known inputs give exact expected scores |
| 7.4 | Add baseline statistical forecast, shown as ranges | Calibration measured; too little history shows no forecast; Gemini never supplies the numbers |
| 7.5 | Add comparison screen, scenario selection and decision records | Browser test covers brief to selected scenario; decision is stored |
| 7.6 | Add Market Gap agent and a screen to turn an approved gap into a campaign | Each gap cites evidence; a seeded gap is found; a topic competitors already cover is not reported as a gap |

## Phase 8: Full content production

Gate: a validated video asset is produced and passes through Guardian and approval.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 8.1 | Add script agent: hooks, captions, CTAs, platform versions | Output validated per platform |
| 8.2 | Add scene breakdown and image and video generation adapters | Fake and real provider pass the same contract tests; provenance stored |
| 8.3 | Add voice, transcription and subtitle adapters | Subtitle timing matches a known sample |
| 8.4 | Add FFmpeg rendering, thumbnails and platform variants | Output checked for codec, resolution, frame rate, duration, audio and size |
| 8.5 | Add Content Studio: script editor, timeline, assets, preview, versions | Browser test covers edit to new version |
| 8.6 | Extend Guardian to visuals, logo and color use, platform rules, licensing | Seeded violations detected with evidence |
| 8.7 | Add client portal for reviewing exact versions | Client approver sees only assigned brands |
| 8.8 | Add Ad Creation agent: copy, creative variants and ad formats from an approved brief | Variants validate against format limits; each links to its brief and brand context |
| 8.9 | Extend Guardian and approval to ads: unsupported claims and advertising rules | Seeded violations detected with evidence; no variant is marked ready without approval |

## Phase 9: Creative Autopsy and experiments

Gate: a supported analysis leads to a measurable experiment.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 9.1 | Extract scenes, frames, speech, captions and on-screen text | Known sample video gives expected results |
| 9.2 | Classify hook, scene purpose, pacing and CTA into `creative_features` | Labelled sample meets an agreed accuracy |
| 9.3 | Align features with available watch-time metrics | Report separates measured facts from hypotheses |
| 9.4 | Add `experiments`: hypothesis, variants, success metric, outcome | Result feeds a proposed lesson; low sample is labelled |
| 9.5 | Add remaining platform adapters, one at a time | Each passes contract tests and a test-account post; depends on platform access |

## Phase 10: Cross-Brand Intelligence

Gate: an aggregate insight is available with no raw client leakage.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 10.1 | Add client opt-in and contribution policy | Non-participating brands contribute nothing |
| 10.2 | Add separate aggregation service using derived statistics only | Service has no access to raw client tables |
| 10.3 | Enforce minimum cohort sizes and suppress rare values | Below-threshold groups never appear |
| 10.4 | Run leakage and re-identification tests | Attempts to recover source-client data fail |
| 10.5 | Add approval, retrieval audit and Agency Intelligence screens | Every contribution and retrieval is logged |

## Phase 11: Production launch

Gate: the production acceptance checklist passes.

| Step | Work | Test that must pass |
| --- | --- | --- |
| 11.1 | Add billing, plans and usage metering | Plan limits enforced; invoices match usage records |
| 11.2 | Complete agency dashboard: clients, status, approvals, usage, costs, agent activity | Browser test covers each panel |
| 11.3 | Add OpenTelemetry tracing, structured logs, metrics and alerts | One run traces end to end; logs contain no secrets |
| 11.4 | Build Docker images, AWS infrastructure, secrets and staging | Staging deploy and smoke tests pass |
| 11.5 | Add CI/CD with reviewed migrations and rollback | A bad deploy rolls back automatically in staging |
| 11.6 | Test backups, restore, data deletion and load | Restore succeeds; load target met |
| 11.7 | Final security audit and production promotion | No open high-severity findings; independent penetration test recommended |

## Needed from you

| When | What |
| --- | --- |
| Step 1.4 | Rotate the DB password and Gemini key; download the cluster root certificate |
| Step 2.2 | Confirm the login provider (blueprint default: Supabase Auth) and create the project |
| Step 2.9 | Developer accounts for the first platform |
| Step 3.2 | AWS S3 access, or approval for local MinIO during development |
| Step 3.5 | Meko API key and development datapack access |
| Step 4.4 | AWS KMS access |
| Step 4.7 | A test social account |
| Step 8.2 | Your choice of image and video generation providers, with API keys |
| Step 8.3 | Your choice of voice provider, with an API key |
| Step 9.5 | Developer access for each further platform |
| Step 11.1 | Billing provider and pricing |
| Step 11.4 | AWS production account and domain |
