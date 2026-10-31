# Architecture

FastAPI is the policy layer: every user request and agent action passes through its authorization, tenant and approval checks. This document describes the target design; [status.md](status.md) says what exists today.

## System

```
Next.js (dashboard, client approvals)
        |
FastAPI (auth, RBAC, tenant policy, REST, SSE)
        |
   +----+----------------+------------------+
   |                     |                  |
LangGraph supervisor   Celery workers     Publishing service
and specialist agents  (media, analytics, (re-checks approval;
   |                    memory updates)    holds social tokens)
   |                     |                  |
Gemini, Meko          FFmpeg, S3         Social platform APIs
   |                     |                  |
   +----------- YugabyteDB ----------------+
```

## Who owns what

| Service | Owns | Does not own |
| --- | --- | --- |
| YugabyteDB | Business records, approvals, audit history, checkpoints | Agent memory retrieval |
| Meko | Agent context, approved memories, knowledge retrieval | Authoritative records |
| LangGraph | Workflow order, state, retries, human interrupts | Long-term memory |
| Gemini | Reasoning, extraction, generation, classification | Numeric forecasts |
| Celery and Redis | Long-running job execution | Authoritative job records |
| S3 | Media and documents | Metadata |

## Campaign learning loop

Understand, strategize, create, validate, approve, publish, analyze, learn. Approved lessons feed the next campaign.

## First milestone

Each step must work against real services:

1. User signs up.
2. User creates an organization and a brand.
3. User uploads brand guidelines.
4. Gemini extracts a proposed brand profile.
5. A human approves it, and it is saved in YugabyteDB.
6. Authorized context is saved in Meko.
7. User creates a campaign.
8. LangGraph retrieves brand context, and Gemini generates three structured ideas.
9. Results are saved in YugabyteDB and displayed in Next.js.

Advanced agents and the six USPs start only after this works.

## Repository structure

```
apps/api/app/      api/v1, core, db, models, schemas, repositories, services,
                   integrations (gemini, meko, social, storage), agents, graphs,
                   workers, security
apps/api/          migrations, tests
apps/web/          Next.js app, components, features, hooks, lib, types
packages/          shared-types, api-client, ui
infrastructure/    docker, aws, monitoring, ci
```

Tenant routes nest under `/api/v1/organizations/{org_id}`, so every request names its tenant and the backend checks membership first.

## Environments

Development, staging and production each get a separate database, Meko datapacks, credentials, storage bucket and OAuth callbacks. Only development exists today.

## Known constraints

- The current cluster is a sandbox: 1 node, no fault tolerance, 2 vCPU, 4 GB memory, 10 GB disk. It suits development only.
- The sandbox refuses new objects past 180 tablets, and each copy of the schema uses about 60. Interrupted test runs can leave `creatoros_test_*` schemas that use this up. The full product needs a larger cluster or colocated tables.
- Publishing depends on platform app review and quotas, which sit outside our control.
