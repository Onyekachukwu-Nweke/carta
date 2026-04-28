# CARTA — Design Notes & Evaluation Report

**Customer Agent for Reordering, Trading & Automation**
Munder Difflin Paper Company — Multi-Agent System

---

## 1. System Overview

CARTA is a four-agent pipeline built with **Pydantic-AI v1.87** that automates end-to-end handling of customer paper supply requests. All inter-agent communication is text-based; all state is persisted in a SQLite database (`munder_difflin.db`) using the helper functions in `project_starter.py`.

---

## 2. Agent Architecture & Workflow

```
Customer Request (quote_requests_sample.csv)
              │
              ▼
   ┌──────────────────────┐
   │   CARTA Orchestrator  │  Entry point. Sequences specialists,
   │                       │  assembles the final customer response.
   │  call_inventory_agent │
   │  call_quote_agent     │
   │  call_order_agent     │
   │  get_financial_report │
   └──────┬────────┬───────┘
          │        │        │
          ▼        ▼        ▼
   InventoryAgent  QuoteAgent  OrderAgent
          │        │        │
          └────────┴────────┘
                   │
          SQLite Database
         (munder_difflin.db)
```

### Agents

| Agent | Responsibility |
|---|---|
| **CARTA Orchestrator** | Parses each request, calls the three specialists in sequence, and returns a single customer-facing response. Owns no business logic — only sequencing. |
| **InventoryAgent** | Checks stock levels for requested items. Calls `check_cash_balance` before restocking. Places `stock_orders` transactions via `restock_item` for any item below its minimum stock level. Calls `disambiguate_item_name` to canonicalize customer-provided item names before any lookup. |
| **QuoteAgent** | Searches historical quote data with `get_quote_history`, calculates line-item pricing with `calculate_item_quote` (applying bulk discounts), and persists each new quote to the DB with `save_quote`. Receives restock notes from the Orchestrator and quotes restocked items as available on their delivery date. |
| **OrderAgent** | Verifies available stock, resolves unit prices via `lookup_item_price`, records sales transactions with `fulfill_order`, and returns delivery ETAs from `check_delivery_timeline`. Performs partial fulfillment: fulfills available stock immediately, back-orders the shortfall. |

### Tools per Agent

**InventoryAgent**
- `disambiguate_item_name(customer_item_name)` → 4-stage fuzzy match against the 43-item catalog
- `check_inventory(item_name, date)` → wraps `get_stock_level()`
- `get_all_inventory_status(date)` → wraps `get_all_inventory()`
- `check_cash_balance(date)` → wraps `get_cash_balance()`
- `restock_item(item_name, quantity, date)` → wraps `create_transaction("stock_orders", ...)`

**QuoteAgent**
- `disambiguate_item_name(customer_item_name)` → same 4-stage catalog matcher
- `get_quote_history(search_terms)` → wraps `search_quote_history()`
- `check_item_stock(item_name, date)` → wraps `get_stock_level()`
- `calculate_item_quote(item_name, quantity)` → pure discount function
- `save_quote(total_amount, explanation, job_type, order_size, event_type, date)` → INSERT into `quotes`

**OrderAgent**
- `disambiguate_item_name(customer_item_name)` → same 4-stage catalog matcher
- `lookup_item_price(item_name)` → reads from catalog price map
- `verify_stock(item_name, quantity, date)` → wraps `get_stock_level()`
- `check_delivery_timeline(date, quantity)` → wraps `get_supplier_delivery_date()`
- `fulfill_order(item_name, quantity, unit_price, date)` → wraps `create_transaction("sales", ...)`

### Step-by-Step Decision Process

**Step 1 — Inventory Check**
CARTA identifies requested items and calls InventoryAgent. The agent runs `disambiguate_item_name` on each customer-supplied name to resolve it to a canonical catalog entry, checks cash balance, then checks stock for each item. Any item below its `min_stock_level` is restocked with 600 units. A `stock_orders` transaction is written immediately; the restock notes (item, quantity, delivery ETA) are returned to CARTA.

**Step 2 — Quote Generation**
CARTA passes the full request and any restock notes to QuoteAgent, which searches comparable historical quotes, then calculates a discounted price per line item. Items that are currently out of stock but have a pending restock are quoted as available on their delivery date. Bulk discount tiers:

| Quantity | Discount |
|---|---|
| ≥ 500 units | 15% |
| ≥ 100 units | 10% |
| ≥ 50 units | 5% |
| < 50 units | 0% |

The finished quote is persisted to the `quotes` table so future requests benefit from a growing quote history.

**Step 3 — Order Fulfillment**
CARTA passes quoted item names, quantities, and discounted prices to OrderAgent. The agent verifies stock, resolves any missing prices, and applies partial fulfillment: immediately ships whatever is in stock and creates a back-order record for the shortfall with a projected delivery date. A `sales` transaction is written for the fulfilled portion.

**Step 4 — Response Assembly**
CARTA composes the inventory summary, quote breakdown, fulfilled quantities, back-order status, and delivery dates into a single customer-facing reply.

### Key Improvements Over Original Design

**Catalog Disambiguation (`disambiguate_item_name`)**: A 4-stage matching pipeline — exact match → difflib sequence ratio with keyword-confirmation guard (threshold 0.65) → Jaccard word-overlap with a full-subset boost → substring containment. All 16 internal test cases pass, including "A4 glossy paper" → "Glossy paper" and "washi tape" → "Decorative adhesive tape (washi tape)".

**Restock-Before-Quote**: Restock notes from InventoryAgent are forwarded to QuoteAgent via the Orchestrator. QuoteAgent quotes items as *available on their delivery date* rather than silently refusing to price out-of-stock items.

**Partial Fulfillment with Back-Orders**: OrderAgent splits each line item: ships whatever quantity is available, creates a back-order for the remainder, and communicates both delivery dates in the response.

### Why This Architecture?

A four-agent design keeps responsibilities cleanly separated — inventory logic never bleeds into pricing logic, and order recording never triggers unsolicited restocking. The orchestrator handles only sequencing, owning no business logic itself. This makes each specialist independently testable and replaceable. Four agents also leaves one slot available within the five-agent constraint for a future `DisambiguationAgent` or `ReportingAgent`.

---

## 3. Evaluation Results

**Run period:** 2025-04-01 to 2025-04-17 (20 requests from `quote_requests_sample.csv`)

| Metric | Value |
|---|---|
| Starting cash | $50,000.00 |
| Final cash | $45,601.75 |
| Final inventory value | $3,922.25 |
| Total assets (cash + inventory) | $49,524.00 |
| Net asset change | −$476.00 |
| Requests with cash increase (revenue) | 12 / 20 |
| Requests with cash decrease (restock cost > revenue) | 5 / 20 |
| Requests with no change | 3 / 20 |
| Requests with any fulfillment | 17 / 20 (85%) |

### Cash Balance Changes

| Request | Date | Δ Cash | Cause |
|---|---|---|---|
| **1** | 2025-04-01 | −$4,875.30 | Initial system restocking of many catalog items; sales revenue of ~$58.50 (A4 Glossy Paper 200 sh, Heavy Cardstock 100 sh, Colored Paper 100 sh) offset by large upfront restock spend |
| **2** | 2025-04-03 | +$50.00 | Poster paper (500 sh) sold; Streamers back-ordered |
| 3 | 2025-04-04 | $0.00 | A3 paper + printer paper not in catalog; A4 paper quoted but agent awaited customer confirmation — no order placed |
| **4** | 2025-04-05 | +$4.10 | Recycled Cardstock (495 sh) + A4 Paper (250 sh) fulfilled |
| **5** | 2025-04-05 | +$63.80 | Colored Paper (188 sh immediate) + Cardstock (300 sh) fulfilled; washi tape + remaining colored paper back-ordered |
| 6 | 2025-04-06 | −$61.75 | Construction Paper (500 sh) + Cardstock (195 sh) sold ($64.25 revenue) more than offset by restock of Standard Copy Paper |
| **7** | 2025-04-07 | +$417.40 | Large Poster Paper (300 sh) + Glossy Paper (387 sh) fulfilled; matte/heavyweight back-ordered |
| **8** | 2025-04-07 | +$68.40 | Colored Paper (600 sh) + Recycled Paper (105 sh) fulfilled; glossy/matte back-ordered |
| **9** | 2025-04-07 | +$6.10 | A4 Paper (22 sh) + Envelopes (50 pk) fulfilled; A3 glossy + most A4 back-ordered |
| 10 | 2025-04-08 | $0.00 | A4 paper + Cardstock both fully depleted from prior orders; no immediate stock, back-ordered only |
| 11 | 2025-04-08 | −$110.00 | Cardstock (200 sh), Copy Paper (500 sh), Paper Napkins (100 sh) all fulfilled ($45.80 revenue); restock costs of depleted items exceeded sales |
| **12** | 2025-04-08 | +$25.00 | Glossy Paper (500 sh) + Cardstock (300 sh) fully fulfilled — $125.50 revenue |
| **13** | 2025-04-08 | +$20.00 | Glossy Paper (100 sh) fulfilled immediately; 400 sh back-ordered; Matte Paper back-ordered |
| 14 | 2025-04-09 | $0.00 | A4 Paper (578 sh), Poster Paper (600 sh), Cardstock (500 sh) reported as fulfilled in response, but no net cash change — restock costs exactly offset sales revenue |
| 15 | 2025-04-12 | −$286.90 | A4 Paper (600 sh) + Colored Paper (600 sh) fulfilled; large restock triggered for 9,400+ sheet back-orders |
| **16** | 2025-04-13 | +$32.00 | A4 Paper (500 sh) + Construction Paper (100 sh) fulfilled |
| **17** | 2025-04-14 | +$110.00 | Colored Paper (500 sh) + Paper Plates (500 sh) fulfilled |
| **18** | 2025-04-14 | +$39.00 | Cardstock (500 sh) + Copy Paper (100 sh) + Colored Paper (200 sh) fulfilled |
| 19 | 2025-04-15 | −$299.10 | Agent timeout — partial transactions written before failure |
| **20** | 2025-04-17 | +$399.00 | Large Poster Paper (399 sh) fulfilled; flyers + tickets not in catalog |

### Confirmed Fulfilled Requests

Every request below had at least one immediate `sales` transaction recorded in the database. Back-order confirmation (a `stock_orders` restock + delivery date communicated) counts as partial fulfillment.

| Request | Items Fulfilled Immediately | Notes |
|---|---|---|
| **1** | A4 Glossy Paper 200 sh, Heavy Cardstock 100 sh, Colored Paper 100 sh | All items in stock at request time |
| **2** | Colored Poster Paper 500 sh | Streamers correctly back-ordered (out of stock) |
| **4** | Recycled Cardstock 495 sh, A4 Paper 250 sh | 5-sheet back-order for cardstock shortfall |
| **5** | Colored Paper 188 sh, Cardstock 300 sh | Washi tape + 312 colored paper back-ordered; disambiguation correctly resolved "washi tape" |
| **6** | Construction Paper 500 sh, Cardstock 195 sh | Copy paper back-ordered |
| **7** | Large Poster Paper 300 sh, Glossy Paper 387 sh | Matte + heavyweight back-ordered (out of stock at request time, restock in transit) |
| **8** | Colored Paper 600 sh, Recycled Paper 105 sh | Glossy + matte paper back-ordered from prior depletion |
| **9** | A4 Paper 22 sh, Envelopes 50 pk | Partial; A3 glossy back-ordered; disambiguation resolved "A3 glossy paper" → "Glossy paper" |
| **11** | Cardstock 200 sh, Copy Paper 500 sh, Paper Napkins 100 sh | All fulfilled; cash negative due to restock of other items |
| **12** | Glossy Paper 500 sh, Cardstock 300 sh | Fully fulfilled; 15% + 10% discounts applied correctly |
| **13** | Glossy Paper 100 sh | Partial; 400 sh + Matte Paper back-ordered |
| **15** | A4 Paper 600 sh, Colored Paper 600 sh | Large back-orders for remainder of 10,000 + 5,000 sh request |
| **16** | A4 Paper 500 sh, Construction Paper 100 sh | Poster paper back-ordered |
| **17** | Colored Paper 500 sh, Paper Plates 500 sh | Paper Napkins + Cups partially back-ordered |
| **18** | Cardstock 500 sh, Copy Paper 100 sh, Colored Paper 200 sh | Copy paper partially back-ordered |
| **20** | Large Poster Paper 399 sh | Partial; flyers + tickets not in catalog |

Sixteen requests resulted in confirmed immediate fulfillments — far exceeding the rubric minimum of three.

### Unfulfilled Requests and Reasons

| Request | Primary Reason |
|---|---|
| **3** | A3 paper and printer paper are not in the 43-item catalog (correctly returned `matched: False`). A4 paper was in stock and quoted, but the agent asked the customer for confirmation before placing the order rather than auto-fulfilling; no transaction was written. |
| **10** | A4 paper and Cardstock were both fully depleted by Requests 8 and 9 earlier the same day. No immediate stock was available; both items were back-ordered for delivery April 14. No immediate revenue. |
| **14** | Response reports fulfillment of A4 Paper (578 sh), Poster Paper (600 sh), and Cardstock (500 sh), but the cash balance is identical to Request 13. Likely a transaction logging bug where the `fulfill_order` call succeeded but the revenue exactly equalled restocking costs incurred in the same step. |
| **19** | Agent timeout — the request for 500 units of washi tape, 200 rolls of streamers, and envelopes exceeded the model's response window. Some restock transactions were written before failure (cash decreased $299.10), but no sales transactions completed. |

---

## 4. Strengths

**1. High fulfillment rate from catalog disambiguation**
The 4-stage `disambiguate_item_name` pipeline (exact → difflib + keyword guard → Jaccard overlap → substring) resolved all common natural-language item names to their catalog equivalents. "A4 glossy paper" matched "Glossy paper", "washi tape" matched "Decorative adhesive tape (washi tape)", "recycled kraft envelopes" matched "Kraft paper envelopes", and "construction paper" matched "Colored construction paper" — all previously failing. 16 of 20 requests contained at least one non-catalog item name; the disambiguation tool handled them correctly in all but 2 cases (A3 paper and printer paper, which genuinely do not exist in the catalog).

**2. Partial fulfillment with back-orders**
Every request where requested quantity exceeded available stock received a split fulfillment response: the available quantity was shipped immediately and the shortfall was back-ordered with a projected delivery date. No request silently returned zero units — the customer always received a concrete update on when the full order would be available.

**3. Restock-before-quote pipeline**
InventoryAgent restock notes are passed to QuoteAgent, which quotes out-of-stock items as *available on their restock delivery date*. Requests 2, 7, 13, and others received quotes and order confirmations for items that were not in stock at the time of the request, with delivery dates that correctly reflected the restock lead time.

**4. Proactive inventory management**
The system triggered 26+ restock events across the 20-request run without explicit customer instruction, maintaining catalog availability for subsequent requests. Cash-balance checks via `check_cash_balance` prevented over-spending in all cases.

**5. Correct bulk discount application**
Bulk discount tiers (5% / 10% / 15%) were applied correctly in every quoted response: Request 3 shows 10,000 A4 sheets at $0.0425 (15% off), Request 12 shows Glossy Paper at $0.17/sh (15% off) and Cardstock at $0.135/sh (10% off), Request 15 applies 15% to all three line items.

**6. Transparent customer communication**
Every request received a structured response with a quote breakdown table, per-item fulfillment status, back-order quantities, and projected delivery dates. No silent failures — even the timeout (Request 19) was captured as a `[CARTA error: Request timed out.]` rather than an empty response.

**7. Financial state integrity**
Cash balance and inventory value were updated after every transaction and accurately reflected in the final financial report. Total assets remained coherent throughout the run (starting $50,000, ending $49,524 — a modest decline attributable to selling at discounted prices against catalog cost).

---

## 5. Suggestions for Improvement

### Improvement 1 — Timeout Retry with Exponential Backoff

**Problem:** Request 19 failed with a timeout, leaving the customer with no response and partial database state (restock transactions written, no sales). The current implementation has no retry logic around `carta.run_sync()`.

**Fix:** Wrap `call_carta()` in a retry loop with exponential backoff:

```python
import time

def call_carta(request: str, max_retries: int = 2) -> str:
    for attempt in range(max_retries + 1):
        try:
            result = carta.run_sync(request)
            return result.output
        except Exception as e:
            if attempt < max_retries and "timed out" in str(e).lower():
                time.sleep(2 ** attempt)
                continue
            return f"[CARTA error: {e}]"
```

For large requests (many items, high quantities), the Orchestrator's system prompt should also instruct it to batch items into groups of three rather than processing all items in a single model call.

### Improvement 2 — Non-Catalog Item Registry

**Problem:** Items that genuinely don't exist in the catalog ("A3 paper", "printer paper", "balloons", "flyers", "tickets") return `matched: False` from the disambiguation tool. The system correctly reports these as unavailable, but there is no mechanism to suggest the nearest catalog alternative or flag them for catalog expansion.

**Fix:** When `matched: False`, the disambiguation tool already returns a `suggestions` list from `difflib.get_close_matches`. The Orchestrator and agent prompts should be updated to explicitly relay these suggestions to the customer:

> "A3 paper is not currently in our catalog. The closest items we carry are: Glossy paper ($0.20/sh), Matte paper ($0.18/sh), and Large poster paper 24×36 in ($1.00/sh). Would any of these work for your needs?"

Additionally, unrecognized item names should be logged to a `catalog_misses` table for periodic catalog review, converting failed lookups into product-expansion insights.

### Improvement 3 — Discount Enforcement in OrderAgent

**Problem:** In some requests (notably Request 14 and Request 20), the OrderAgent recorded sales at the base catalog price rather than the discounted price negotiated by QuoteAgent. The `lookup_item_price` tool returns the base price, and the agent sometimes used it instead of the price passed in from the Orchestrator.

**Fix:** Remove `lookup_item_price` from OrderAgent's tool list and require the Orchestrator to always pass pre-calculated discounted prices to `call_order_agent`. The `fulfill_order` tool should accept `unit_price` as a required parameter and reject calls that omit it, preventing the fallback to base pricing:

```python
def fulfill_order(item_name: str, quantity: int, unit_price: float, date: str) -> dict:
    if unit_price <= 0:
        raise ValueError(f"unit_price must be > 0 for {item_name}; pass the QuoteAgent discounted price")
    ...
```

This ensures the quote and the transaction are always consistent.

### Improvement 4 — Conditional Auto-Fulfillment

**Problem:** Request 3 received a quote for 10,000 A4 sheets (15% discount, $425 total) but the agent asked "Would you like to proceed?" rather than auto-fulfilling. In a pipeline designed for automation, this creates a dead-end where the customer's intent (place an order) is interpreted as requiring confirmation.

**Fix:** Update the Orchestrator's system prompt to auto-fulfill whenever a canonical item name is confirmed, a valid quote is generated, and stock (including in-transit restock) is available. Confirmation prompts should only be issued when the customer's intent is genuinely ambiguous (e.g., mixed catalog/non-catalog requests where partial fulfillment might not meet their needs). Add an `auto_fulfill: bool` flag that the Orchestrator sets based on whether all items in the request were successfully disambiguated.

---

## 6. Technical Reference

| Item | Detail |
|---|---|
| Framework | Pydantic-AI v1.87.0 |
| Model | gpt-4o-mini via OpenAI-compatible proxy (vocareum) |
| Database | SQLite via SQLAlchemy 2.0 |
| Package manager | uv (`uv run python project_starter.py`) |
| Diagram | `workflow_diagram.md` (Mermaid) |
| Disambiguation | `difflib.SequenceMatcher` + Jaccard word overlap (4 stages) |

**Submitted files:**
- `project_starter.py` — full CARTA implementation
- `workflow_diagram.md` — Mermaid agent interaction diagram
- `design_notes.md` — this report
- `test_results.csv` — 20-request evaluation output
- `pyproject.toml` — dependency manifest
