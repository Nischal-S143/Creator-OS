# Agent design

A LangGraph supervisor runs specialist agents as defined workflow steps with typed state, Pydantic outputs and fixed tools. Agents never call each other freely or bypass backend checks. None of this is built yet.

## Agents

| Agent | Responsibility | Output | Must not |
| --- | --- | --- | --- |
| Research | Authorized public research, competitor themes, audience questions | Brief with sources and limitations | Treat unverified claims as fact |
| Strategy | Use brand context to define pillars, scenarios and experiments | Structured campaign plan | Invent numeric forecasts |
| Script | Hooks, scripts, captions, CTAs, platform versions | Versioned draft | Approve its own work |
| Visual | Scene plans, image and video prompts, asset selection | Scene plan and asset references | Use assets without provenance |
| Voice | Voiceover, subtitles and audio | Audio and subtitle assets | Use unlicensed voices |
| Video | Timeline, FFmpeg assembly, platform variants, validation | Rendered assets | Skip technical validation |
| Brand Guardian | Independent review of voice, visuals, claims, policy, provenance | `PASS`, `NEEDS_REVIEW` or `BLOCKED`, with evidence and recommendations | Approve content or authorize publishing |
| Publishing | Request and track publishing | Scheduled job and status | Hold social tokens or skip approval |
| Analytics | Metrics, creative analysis, experiments, proposed lessons | Measured facts, separate hypotheses | Save durable memory without approval |

## Additions to the nine-agent list

- **Market Gap:** finds unmet topics, with evidence.
- **Ad Creation:** creates ad copy and variants. It does not launch ads or spend money.
- **Feedback review:** proposed as part of Analytics, reviewing posts at 48 hours, 7 days and 30 days and feeding a human-approved Learning Ledger.

## Requirements for every agent

- Defined responsibility, typed inputs and outputs, and a fixed list of allowed tools.
- Error handling, logging, retry rules and tests.
- Run records with correlation, tenant, brand and campaign IDs, duration, model and token usage.
- Retrieved context and uploaded content are treated as data, never instructions.

## State

Shared state follows the blueprint's `CreatorOSState`: tenant, brand and campaign IDs, brand context, insights, strategy, assets, Guardian results, approval and publishing status, performance results and learning updates.

## Durability and approval

Checkpoints are stored separately from Meko. Human approval uses LangGraph interrupts, resumed only after backend authorization. A live test on 31 October 2026 with `langgraph` 1.2.19 and `langgraph-checkpoint-postgres` 3.2.0 confirmed on YugabyteDB that a graph paused at an interrupt and resumed on a new connection. Real worker restarts and checkpoint pruning remain untested.

## Memory rule

Agents may propose memories. Only approved items are promoted to durable brand context, and every item keeps its source.
