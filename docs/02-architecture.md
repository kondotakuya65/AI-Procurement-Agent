# 02 — Architecture

## High-level

```text
Next.js UI  --SSE-->  FastAPI runs API  -->  LangGraph
                                              | tools
                    +-------------------------+------------------+
                    |                         |                  |
              search_vendors           FinOps HTTP/mock     draft_email
              (fixtures)               query + review
```

## LangGraph state (sketch)

```json
{
  "goal": "Procure 500 units of SKU-1001",
  "sku": "SKU-1001",
  "quantity": 500,
  "vendors": [],
  "historical_price": null,
  "best_vendor": null,
  "best_price": null,
  "email_draft": null,
  "hitl_status": "pending",
  "messages": [],
  "trace": []
}
```

## Tools

| Tool | Input | Output |
| --- | --- | --- |
| `search_vendors` | sku, qty | ranked vendor offers |
| `query_finops_rag` | natural question | FinOps answer + facts |
| `review_invoice` | invoice_id | Accept/Reject + drift alerts |
| `draft_email` | vendor, sku, price, intent | subject + body |

## HITL

Graph **interrupts** after `draft_email`. Resume payload:

```json
{ "decision": "approve" | "edit" | "reject", "edited_draft": "..." }
```

Approve → persist outbox artifact. Reject → end with summary. Edit → optionally re-run reflection stretch.

## FinOps coupling

- `FINOPS_API_URL=http://localhost:8000` when FinOps-RAG is running.  
- `FINOPS_MODE=live|mock` — mock returns fixture historical prices so this repo demos alone.
