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

### C1 — State + skeleton
- [ ] `ProcurementState`, node stubs, compile  

### C2 — Happy path
- [ ] parse → search → history → compare → draft → summary  

### C3 — Re-plan / errors
- [ ] Zero vendors → similar SKU suggestion  
- [ ] Tool failure retry / degrade  

### C4 — HITL
- [ ] Interrupt before send; resume approve/edit/reject  

## Phase D — API + streaming

### D1 — Runs API
- [ ] create run, get status, resume  

### D2 — SSE traces
- [ ] Stream thought / action / observation  

## Phase E — UI

### E1 — Workspace
- [ ] Goal box, trace log, state side panel  

### E2 — HITL panel
- [ ] Draft preview + Approve / Edit / Reject  

## Phase F — Quality + stretch

### F1 — Eval + CI
- [ ] Golden tool-order tests, mocked LLM  

### F2 — Reflection stretch
- [ ] Reviewer LLM rewrites email if weak  

### F3 — Integrations stretch
- [ ] Optional live search flag  
- [ ] Compose alongside FinOps-RAG  

## MVP ship line

**Through E2** = portfolio-ready demo. F1 strongly recommended; F2–F3 optional.
