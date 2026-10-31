# TODO

Phases follow the project brief. Each phase needs a plan and approval first, and is finished only when its tests pass.

## Phase 0: Project setup

- [x] Monorepo structure, `.gitignore`, `.env.example`
- [x] `CLAUDE.md`, `README.md`, docs
- [x] Approval of this plan
- [x] Local Celery worker on Memurai, without Docker
- [x] Backend lint, format, security, dependency and test command (`scripts/check.ps1`)
- [x] First commit
- [x] Web run, lint and test commands (with the Next.js app)

## Phase 1: SaaS foundation

- [x] Finish restricted-role tests; drop leftover test schema
- [ ] `verify-full` with root certificate
- [x] Restrict AI test endpoint, generic errors, reduced health output, docs off in production
- [x] Gemini unit tests
- [x] Reorganize `apps/api/app` to the documented layout
- [x] `users`, `memberships`; revise `0001` with `plan`, `status` and composite keys
- [x] Login and sign-up with JSON file accounts
- [ ] Email verification and password reset
- [ ] Per-brand assignment for managers and client approvers
- [x] Tenant context and row-level security
- [x] RBAC matrix
- [x] Organization, member and brand APIs
- [x] Next.js app, shadcn/ui, sign-up and sign-in screens, organization, brand and member screens
- [x] Adversarial tenant-isolation tests

## Milestone: integrated vertical slice (needs Phases 2 and 3)

Signup, organization, brand, guidelines upload, Gemini profile, human approval, YugabyteDB, Meko, campaign, LangGraph context, three ideas, saved results, Next.js display.

## Phase 2: AI integrations

- [ ] Gemini usage and cost logging; per-agent models
- [x] Meko MCP client and live tool discovery
- [x] Datapack mapping and two-brand leakage test
- [x] Integration tests

## Phase 3: Brand Brain

- [x] Onboarding, document ingestion, profile extraction and approval
- [ ] Preferences, decision history, feedback, memory retrieval and correction

## Phases 4 to 12

- [x] 4: Audience Intelligence (pasted comments only)
- [x] 5: Campaign Flight Simulator (no forecasts)
- [ ] 6: Content production
- [ ] 7: Brand Guardian
- [ ] 8: Human approval
- [ ] 9: Publishing
- [ ] 10: Creative Autopsy
- [ ] 11: Cross-Brand Intelligence
- [ ] 12: Production readiness

## Decisions needed

- [x] GitHub repo stays public
- [x] No Docker for local development; production packaging is decided in Phase 12
- [x] Use a local JSON file for login instead of Supabase; business data stays in YugabyteDB
- [x] Add Market Gap and Ad Creation as extra agents; Ad Creation does not launch ads
- [x] Use the human-approved Learning Ledger for the learning step
- [x] Keep PDFs out of Git
- [ ] First publishing platform
