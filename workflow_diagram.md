# CARTA — Workflow Diagram

**CARTA** (Customer Agent for Reordering, Trading & Automation)
Multi-agent system for Munder Difflin Paper Company.

---

## Agent Interaction Flow

```mermaid
flowchart TD
    Customer([Customer Request]) --> Orch[CARTA Orchestrator]

    Orch -->|"1. check_inventory_agent(items, date)"| Inv[InventoryAgent]
    Inv -->|check_inventory| DB[(SQLite DB\nmunder_difflin.db)]
    Inv -->|get_all_inventory_status| DB
    Inv -->|restock_item → stock_orders txn| DB
    Inv -->|stock report + restock summary| Orch

    Orch -->|"2. call_quote_agent(request, date)"| Quote[QuoteAgent]
    Quote -->|get_quote_history| DB
    Quote -->|check_item_stock| DB
    Quote -->|calculate_item_quote\n(bulk discount logic)| Quote
    Quote -->|line-item quote + total| Orch

    Orch -->|"3. call_order_agent(order_details, date)"| Order[OrderAgent]
    Order -->|verify_stock| DB
    Order -->|check_delivery_timeline\n(supplier lead-time logic)| Order
    Order -->|fulfill_order → sales txn| DB
    Order -->|confirmation + delivery dates| Orch

    Orch --> Response([Final Response to Customer])
```

---

## Data Flow Per Request

```
quote_requests_sample.csv  →  run_test_scenarios()
                                      │
                                      ▼
                           call_carta(request + date)
                                      │
                           ┌──────────┴───────────┐
                           ▼                       ▼
                    InventoryAgent           QuoteAgent
                    checks stock,            searches history,
                    restocks if low          applies discounts
                           │                       │
                           └──────────┬────────────┘
                                      ▼
                                 OrderAgent
                              verifies stock,
                              records sales txn,
                              returns delivery ETA
                                      │
                                      ▼
                              test_results.csv
```

---

## Bulk Discount Tiers

| Quantity     | Discount |
|-------------|---------|
| < 50 units   | 0%      |
| 50–99 units  | 5%      |
| 100–499 units| 10%     |
| ≥ 500 units  | 15%     |

---

## Supplier Lead Times

| Order Size    | Delivery Lead Time |
|--------------|-------------------|
| ≤ 10 units    | Same day           |
| 11–100 units  | 1 day              |
| 101–1000 units| 4 days             |
| > 1000 units  | 7 days             |
