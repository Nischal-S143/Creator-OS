# Implementation status

Last updated 31 October 2026. Phase 0 is complete for the backend, and Phase 1 is in progress. `scripts/check.ps1` last passed with 51 of 51 tests on the real cluster and local broker.

| Component | State | Evidence |
| --- | --- | --- |
| Git and secret scanning | Working locally; nothing pushed | Planted secret blocked by hook |
| Database connection, pool, `/health/db` | Working | Integration tests |
| Restricted roles | Working | 7 role tests |
| Migration `0001` | Tested in throwaway schema | Not applied to `public` |
| Gemini service | Working | Fake-client tests and a live call |
| AI test endpoint | Refused without `INTERNAL_API_KEY` | Tests and a live call |
| Celery worker | Working on Memurai, without Docker | Real-worker test |
| Row-level security, LangGraph checkpointing | Feasibility only | Throwaway tests; not in the app |
| Auth, Meko, frontend | Not started | None |

## Known loose ends

- Pending from the project owner: root certificate (`verify-full`), new Gemini key, Supabase project.
- The GitHub repo stays public by decision, so everything pushed must be safe to publish.
- Local development runs without Docker. Production packaging is decided in Phase 12.
- The test client warns that `httpx` use is deprecated in favour of `httpx2`. It is harmless today.
- `docs/IMPLEMENTATION_PLAN.md` is superseded by `TODO.md`.
