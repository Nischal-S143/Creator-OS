# TODO

Phases follow the project brief. Each phase needs a plan and approval first, and is finished only when its tests pass.

## Phase 0: Project setup

- [x] Monorepo structure, `.gitignore`, `.env.example`
- [x] `CLAUDE.md`, `README.md`, docs
- [x] Approval of this plan
- [x] Local Celery worker on Memurai, without Docker
- [x] Backend lint, format, security, dependency and test command (`scripts/check.ps1`)
- [x] First commit
- [ ] Web run, lint and test commands (with the Next.js app)

## Phase 1: SaaS foundation

- [x] Finish restricted-role tests; drop leftover test schema
- [ ] `verify-full` with root certificate
- [x] Restrict AI test endpoint, generic errors, reduced health output, docs off in production
- [x] Gemini unit tests
- [ ] Reorganize `apps/api/app` to the documented layout
- [ ] `users`, `memberships`; revise `0001` with `plan`, `status` and composite keys
- [ ] OIDC token validation
- [ ] Tenant context and row-level security
- [ ] RBAC matrix
- [ ] Organization, member and brand APIs
- [ ] Next.js app, shadcn/ui, design tokens, sign-up and sign-in, organization and brand screens
- [ ] Adversarial tenant-isolation tests

## Milestone: integrated vertical slice (needs Phases 2 and 3)

Signup, organization, brand, guidelines upload, Gemini profile, human approval, YugabyteDB, Meko, campaign, LangGraph context, three ideas, saved results, Next.js display.

## Phase 2: AI integrations

- [ ] Gemini usage and cost logging; per-agent models
- [ ] Meko MCP client and live tool discovery
- [ ] Datapack mapping and two-brand leakage test
- [ ] Integration tests

## Phase 3: Brand Brain

- [ ] Onboarding, document ingestion, profile extraction and approval
- [ ] Preferences, decision history, feedback, memory retrieval and correction

## Phases 4 to 12

- [ ] 4: Audience Intelligence
- [ ] 5: Campaign Flight Simulator
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
- [x] Use Supabase Auth
- [x] Add Market Gap and Ad Creation as extra agents; Ad Creation does not launch ads
- [x] Use the human-approved Learning Ledger for the learning step
- [x] Keep PDFs out of Git
- [ ] First publishing platform
