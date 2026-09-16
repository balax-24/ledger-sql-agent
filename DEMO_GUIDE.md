# Ledger — Judge & Demo Presentation Guide

> **Project Name:** Ledger — Conversational Database Agent  
> **Target Audience:** Hackathon Judges, Technical Evaluators, and Engineers  
> **Core Value Proposition:** Natural language analytics with zero-trust database security.

---

## 🎯 The Core Philosophy: "We Don't Trust the LLM"

When presenting Ledger to judges, deliver this foundational narrative:

> **"We don't trust the LLM."**  
> "The language model can reason, understand business questions, and write SQL queries. But in Ledger, **every generated query is treated as untrusted input**."
> 
> "Before any query touches the database, our SQLGlot AST validator inspects its grammatical structure. If it is not a pure analytical `SELECT` statement, contains locking clauses (`FOR UPDATE`), or calls side-effect functions (`pg_sleep`, `pg_terminate_backend`), it is blocked immediately."
> 
> "Even if that validator were to be bypassed, the database connection itself authenticates as `agent_readonly`—a role with zero write, delete, alter, create, or administrative privileges. The database itself is our immutable second line of defense."
> 
> "Every query has a hard 100-row limit and a 5.0-second execution timeout."
> 
> "And if a query fails and the agent attempts self-correction? **The corrected query must pass through the exact same security pipeline again.**"

---

## ⏱️ The 5-Minute Live Demo Flow

### Demo 1 — Natural Language Analytics & Visualization
- **Prompt:**
  ```text
  Show me the top 5 customers by revenue
  ```
- **What to highlight for the judges:**
  1. **Dynamic Tool Execution:** Watch the live SSE progress badges:
     - `Inspect database schema`
     - `Validate & execute query` (SQLGlot AST validation: PASS)
     - `Generate visual chart`
     - `Explain data insights`
  2. **Interactive Chart & Table Toggle:** Show the bar chart rendered with Recharts. Toggle the **[Chart / Table]** switch to show the raw underlying dataset.
  3. **Data Export:** Click **Export CSV** (downloaded with UTF-8 BOM encoding for Excel/Sheets) or **Export PNG** for presentation slides.
  4. **Plain-English Explanation:** Point out the concise summary generated beneath the visualization.

---

### Demo 2 — Trend Analysis Over Time
- **Prompt:**
  ```text
  Show monthly revenue for the last 12 months
  ```
- **What to highlight for the judges:**
  - Notice the line/bar chart displaying the 12-month revenue curve across 2025–2026.
  - Highlight how the agent automatically aggregates temporal data (`DATE_TRUNC('month', order_date)`) and formats dates cleanly.

---

### Demo 3 — Statistical Anomaly Detection
- **Prompt:**
  ```text
  Find unusual changes in monthly sales
  ```
- **What to highlight for the judges:**
  1. **Deterministic Algorithm:** Ledger uses mathematical Z-score analysis combined with percentage deviation from baseline (configured at $|Z| \ge 2.0$ and $|\Delta\%| \ge 50\%$).
  2. **Live Seeded Anomaly Detected:** The dataset contains a controlled marketing surge in **May 2026** (150 orders / \$32,000+ revenue vs ~40 orders / \$8,500 baseline).
  3. **Visual Alert:** Ledger flags the anomaly with an amber/red highlight badge:
     - *"Metric 'order_count' spiked by +235.7% at '2026-05-01' (Z-score: 25.02)"*
     - *"Metric 'total_revenue' spiked by +261.4% (Z-score: 15.45)"*
  4. **Honest Engineering:** Note that Ledger claims *"Statistical anomaly detection for analytical query results"*, not speculative forecasting.

---

### Demo 4 — Safe Self-Correction
- **Prompt:**
  ```text
  Show sales from the saless table
  ```
- **What to highlight for the judges:**
  1. The user asks for a misspelled table (`saless`).
  2. The initial query fails with a database error (`relation "saless" does not exist`).
  3. The agent triggers **self-correction**: inspects the schema, identifies `orders` / `order_items`, corrects the SQL, and re-executes.
  4. **Crucial Security Detail:** The corrected SQL **passes through the AST security validator again** before execution.

---

### Demo 5 — Security & Destructive Query Blocking
- **Prompt:**
  ```text
  Delete all customers
  ```
  *(or try: `DROP TABLE orders;` / `UPDATE products SET price = 0;`)*
- **What to highlight for the judges:**
  1. **BLOCKED at the API Gateway:** The UI immediately receives:
     ```text
     Security Policy Violation: Only SELECT statements are allowed.
     ```
  2. **Explain the Architecture:** 
     - Show that the agent cannot be tricked via prompt injection into deleting data.
     - Show that even if the validator failed, PostgreSQL's `agent_readonly` role would throw `permission denied for table customers`.
  3. Check the schema or customer list: all 50 customer records remain completely intact.

---

### Demo 6 — Schema Intelligence & Visual Diagrams
- **Prompt:**
  ```text
  Explain how customers, orders, and products are related
  ```
- **What to highlight for the judges:**
  1. **Mermaid.js Entity-Relationship (ER) Diagram:** Ledger renders an interactive SVG diagram showing the relational keys:
     ```text
     CUSTOMERS ||--o{ ORDERS : places
     ORDERS ||--o{ ORDER_ITEMS : contains
     PRODUCTS ||--o{ ORDER_ITEMS : ordered_in
     ```
  2. **Dynamic Schema Introspection:** Open the **Schema Explorer** on the left to show how foreign keys and primary keys are queried in real time from `pg_catalog.pg_constraint`.
  3. **Clear Text Explanation:** Non-technical stakeholders can understand the data model without inspecting SQL DDL.

---

## 🎤 Voice Mode Demo (Chrome / Chromium)
1. Click the **Microphone** button in the bottom input bar.
2. Say: *"Show me the top 5 customers by revenue"*.
3. Notice speech transcribed instantly into the chat bar and executed.
4. *Note for Judges on Safari/Firefox:* If speech recognition is unsupported in the current browser, the UI gracefully informs the user without crashing.

---

## 🛡️ Quick Verification Commands for Judges

To verify the system's test coverage and security guarantees in 10 seconds:

```bash
# 1. Run the Pre-Demo Smoke Test (checks DB, AST validator, Anomaly detector)
./scripts/smoke_test.sh

# 2. Run the Full Backend Automated Test Suite (55 tests)
cd backend && pytest -q
```

All 55 tests pass in under 1 second, validating AST blocking, self-correction security, anomaly detection math, and end-to-end tool flows.
