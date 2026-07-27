# 05 — Compose with FinOps-RAG (stretch)

Run both portfolio apps side-by-side without port clashes.

| App | API | UI |
| --- | --- | --- |
| AI-FinOps-RAG | **8000** | **3000** |
| AI-Procurement-Agent | **8100** | **3001** |

## FinOps compose

1. Start FinOps-RAG (ingest fixtures, API healthy on `:8000`).  
2. In this repo `.env`:

```bash
FINOPS_MODE=live
FINOPS_API_URL=http://localhost:8000
```

3. Check: `GET http://localhost:8100/api/integrations` → `compose_ready: true` when FinOps `/api/health` is reachable.  
4. Agent tools `query_finops_rag` / `review_invoice` call FinOps HTTP; on failure they fall back to mock fixtures.

`FINOPS_MODE=mock` keeps clone-and-run demos offline.

## Live / hybrid vendor search

```bash
VENDOR_SEARCH_MODE=fixtures   # default — deterministic catalog
VENDOR_SEARCH_MODE=live       # simulated live overlay (or VENDOR_LIVE_URL)
VENDOR_SEARCH_MODE=hybrid     # merge catalog + live, re-rank
```

Optional real feed:

```bash
VENDOR_LIVE_URL=http://localhost:9000/offers
# Expected: GET ?sku=SKU-1001&quantity=500 → {"offers":[...VendorOffer fields...]}
```

Without `VENDOR_LIVE_URL`, live/hybrid use `fixtures/vendors/live_overlay.json` (e.g. Orbit Industrial @ $9.80) so recruiters can demo hybrid ranking without SerpAPI keys.
