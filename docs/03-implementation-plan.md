# 03 — Implementation plan

Fine-grained checklist (one or few commits each).

## Phase A — Foundation

### A1 — Scaffold ✅ (this commit)
- [x] README, license, `.gitignore`, `.env.example`  
- [x] Docs (scenario, architecture, plan, decisions)  
- [x] FastAPI health skeleton + smoke test  
- [x] Next.js shell + favicon (port 3001)  
- [x] docker-compose (API 8100 / UI 3001 / Postgres 5433)  
- [x] Fixtures directory placeholders  

**Accept:** `GET /api/health` OK; UI loads and shows health.

### A2 — Fixtures ✅
- [x] Vendor catalog JSON (SKU-1001 offers, alternatives)  
- [x] Historical price fixtures for mock FinOps + INV-104 review cases  
- [x] Golden scenario definitions + `app.fixtures` loader + tests  

**Accept:** pytest fixture suite green; Coastal $9.95 ranks first for qty 500; INV-104 → Reject.  

### A3 — LLM adapter ✅
- [x] `ollama` / `openai` / `anthropic` / `mock` via `app.llm.provider`  
- [x] Shared settings + `LLM_TIMEOUT_SECONDS`  
- [x] Unit tests with mocked HTTP  

**Accept:** `get_llm_client()` selects provider; missing API keys raise; mock drafts email text.

## Phase B — Tools

### B1 — Tool contracts ✅
- [x] Pydantic tool I/O + `ToolResult` (`app.tools.contracts`)  
- [x] HITL resume payload (`approve` / `edit` / `reject`)  

**Accept:** Models validate; golden tool names match `ToolName` enum.

### B2 — search_vendors ✅
- [x] Fixture-backed search + ranking (`app.tools.search_vendors`)  

**Accept:** qty 500 → Coastal $9.95 best; unknown SKU → `EMPTY`; MOQ filters apply.

### B3 — FinOps client ✅
- [x] `query_finops_rag`, `review_invoice`  
- [x] Live HTTP + mock fallback / retries (`FINOPS_MODE=live|mock`)  

**Accept:** mock SKU-1001 → $10; INV-104 → Reject; live failure → `mock_fallback`.

### B4 — draft_email ✅
- [x] Professional draft prompt wrapper (`app.tools.draft_email`)  
- [x] Subject/body parse + deterministic fallback  

**Accept:** mock LLM drafts Alpha negotiation email; empty LLM → template fallback.

## Phase C — LangGraph

### C1 — State + skeleton ✅
- [x] `ProcurementState`, node stubs, compile (`app.agent`)  
- [x] In-memory checkpointer ready for HITL  

**Accept:** `compile_procurement_graph().invoke(...)` walks all nodes; trace length == NODE_ORDER.

### C2 — Happy path ✅
- [x] parse → search → history → compare → draft → summary (real tools)  

**Accept:** golden goal → Coastal $9.95 best, Alpha $10.80 negotiate, email draft + HITL pending.

### C3 — Re-plan / errors ✅
- [x] Zero vendors → similar SKU suggestion (`replan_sku` → search again)  
- [x] Tool failure retry / FinOps degrade  
- [x] Invoice-only goals → `review_invoice` branch  

**Accept:** SKU-9999 → SKU-1001-ALT + Gamma offer; INV-104 goal → Reject without vendor search.

### C4 — HITL ✅
- [x] `interrupt()` before send; resume approve / edit / reject  
- [x] Approve/edit writes local `outbox/` (no SMTP)  

**Accept:** happy-path pauses with draft payload; approve → outbox JSON; reject → no file.

## Phase D — API + streaming

### D1 — Runs API ✅
- [x] `POST /api/runs`, `GET /api/runs/{id}`, `POST /api/runs/{id}/resume`  

**Accept:** create → `awaiting_hitl` with draft interrupt; resume approve → `completed` + outbox.

### D2 — SSE traces ✅
- [x] Stream thought / action / observation (`POST /api/runs/stream`, resume/replay)  

**Accept:** SSE emits parse→search→…→interrupt; resume stream ends `completed`.

## Phase E — UI

### E1 — Workspace ✅
- [x] Goal box, live trace log, state side panel  

**Accept:** UI streams SSE traces; state panel shows best/negotiate/draft preview.

### E2 — HITL panel ✅
- [x] Draft preview + Approve / Edit / Reject (SSE resume)  

**Accept:** paused run shows HITL panel; Approve writes outbox; Reject completes without file.

## Phase F — Quality + stretch

### F1 — Eval + CI ✅
- [x] Golden tool-order tests, mocked LLM (`app.eval` + pytest)  
- [x] GitHub Actions CI (backend pytest + frontend build)  

**Accept:** all golden scenarios pass offline; CI workflow present.

### F2 — Reflection stretch ✅
- [x] Reviewer LLM rewrites email if weak (`EMAIL_REFLECTION`, writer→reviewer)  

**Accept:** weak draft → rewrite; strong mock draft → PASS; flag can disable.

### F3 — Integrations stretch
- [ ] Optional live search flag  
- [ ] Compose alongside FinOps-RAG  

## MVP ship line

**Through E2** = portfolio-ready demo. F1 strongly recommended; F2–F3 optional.
