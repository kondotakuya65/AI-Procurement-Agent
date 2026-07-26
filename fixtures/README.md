# Fixtures

Deterministic data for demos, mock FinOps, and golden eval. Numbers stay aligned with
[AI-FinOps-RAG](https://github.com/kondotakuya65/AI-FinOps-RAG) `fixtures/ground_truth.json`.

| Path | Purpose |
| --- | --- |
| `vendors/catalog.json` | Offers for `search_vendors` |
| `finops_mock/historical_prices.json` | SKU history, Alpha Q3 spend, QA snippets |
| `finops_mock/review_cases.json` | `review_invoice` Accept/Reject cases |
| `scenarios/golden.json` | Expected tool order + outcomes for eval |

## Demo anchors

| Fact | Value |
| --- | --- |
| Alpha contract SKU-1001 | **$10.00** |
| Alpha live quote (INV-104) | **$10.80** (~8% drift → Reject) |
| Best catalog offer (qty 500) | **Coastal Widgets $9.95** |
| Alpha 2024-Q3 spend | **$10,675.22** |

Happy-path goal: *“Find a cost-effective vendor for 500 units of SKU-1001 and draft a negotiation email.”*
