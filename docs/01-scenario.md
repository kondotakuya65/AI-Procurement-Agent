# 01 — Project scenario

## One-line pitch

A buyer gives one goal — *“Procure 500 units of SKU-1001 cost-effectively”* — and a LangGraph agent searches vendors, checks FinOps history, reviews contract price drift, drafts a negotiation email, then **waits for human approval**.

## Why an agent (not another RAG chat)

| FinOps-RAG | Procurement-Agent |
| --- | --- |
| One question → one answer | One goal → **multi-step plan** |
| Retrieve + compute + explain | **Select tools**, keep state, branch |
| Accountant asks | Buyer **approves** before send |

## Demo story

1. Open the agent UI.  
2. Enter: *“Find a cost-effective vendor for 500 units of SKU-1001 and draft a negotiation email.”*  
3. Watch Thought → Action → Observation stream.  
4. Agent compares fixture vendors vs FinOps historical price (live or mock).  
5. If price drift / better option → draft email.  
6. UI pauses with **Approve / Edit / Reject**.  
7. On Approve, write to outbox (no real email in MVP).

## Success criteria

- Clone runs with mock LLM + mock FinOps (no keys required for CI).  
- At least one golden path shows correct tool order.  
- HITL interrupt is mandatory before “send”.  
- Visible reasoning log (not a black-box spinner).

## Out of scope (MVP)

- Real email SMTP  
- Live web vendor crawl (optional stretch)  
- Full ERP / SAP integration  
