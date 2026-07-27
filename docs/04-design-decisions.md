# 04 — Design decisions

## LangGraph (not CrewAI) for MVP
Explicit state, cycles, and HITL interrupts map cleanly to LangGraph. CrewAI can appear later as an optional multi-agent reflection experiment.

## Compose with FinOps; don’t fork it
Procurement tools call FinOps HTTP APIs. A **mock FinOps** mode keeps this repo clone-and-run without starting FinOps-RAG.

## Deterministic vendor search first
Fixture catalog > live overlay / optional `VENDOR_LIVE_URL` for demos and eval.
`VENDOR_SEARCH_MODE=fixtures|live|hybrid` — SerpAPI not required for the stretch demo.

## Compose FinOps on :8000
Agent stays on **8100** / **3001**. Set `FINOPS_MODE=live` and see `GET /api/integrations`.

## HITL before any “send”
Enterprise safety. MVP writes `outbox/` or DB rows; no SMTP.

## SSE before WebSockets
Enough for Thought/Action/Observation streaming; lower complexity.

## Same LLM env knobs as sibling repos
`LLM_PROVIDER=ollama|openai|anthropic|mock` — recruiters already know the pattern.

## Ports
- Agent API: **8100**  
- Agent UI: **3001**  
- FinOps API/UI (sibling): 8000 / 3000  

Avoids collisions when both projects run locally.
