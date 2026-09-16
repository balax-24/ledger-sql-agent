# 🎙️ Ledger — Hackathon Presentation & Live Demo Playbook

> **Everything you need to deliver a winning, flawless, and stress-free hackathon presentation.**

---

## ⚡ 1. Critical Answer: Do You Need to Execute SQL in Supabase?

### **Short Answer: NO, you do NOT need to execute it in Supabase.**

### **Why?**
Your project runs **completely self-contained inside Docker**:
1. When you run `docker compose up`, Docker spins up a local PostgreSQL container (`ledger-postgres` on port `5433`).
2. The schema (`backend/schema.sql`) and all 1,003 orders, 50 customers, 35 products, and 1,668 order items (`backend/seed_data.sql`) **are already executed and seeded in this local container**.
3. The backend is configured by default to connect to this local database.
4. The comment `-- Run this once in the Supabase SQL editor` at the top of `schema.sql` was only a template note for cloud deployment.

### **Why Local Docker is 100x Better for Your Live Demo:**
* **Zero Wi-Fi Latency:** Queries execute in **2ms - 10ms** locally instead of 200ms - 800ms across the internet.
* **No Hackathon Wi-Fi Blocker:** Many university/venue networks block port `5432` or throttle database connections. Local Docker is completely immune to this.
* **Controlled Environment:** Your local database is pre-configured with the exact mathematical anomaly (+235.7% spike, Z = 25.02 in May 2026) that matches your code and tests.

> 💡 *Note: You only need to run `schema.sql` and `seed_data.sql` in Supabase if you specifically deploy the backend to cloud servers (like Vercel/Railway) pointing to Supabase. For tomorrow's live judge presentation on your laptop, **use local Docker.**

---

## 🚀 2. Pre-Presentation Setup Checklist (Do This 5 Minutes Before)

Open your terminal in the project root:

### Step 1: Start Docker Containers
```bash
docker compose up -d
```
*(If you ever need a clean fresh start: `docker compose down -v && docker compose up --build -d`)*

### Step 2: Verify Health in 2 Seconds
```bash
curl -s http://localhost:8000/api/health
```
**Expected output:**
```json
{"status":"healthy","database":"connected","model":"available","model_name":"gemini-3.5-flash-lite","row_limit":100}
```

### Step 3: Run the Pre-Demo Smoke Test (Optional Confidence Check)
```bash
./scripts/smoke_test.sh
```
All checks will show green checkmarks (`✓ ALL CRITICAL SMOKE TESTS PASSED!`).

### Step 4: Open Browser Tabs Ahead of Time
Open Chrome (or any Chromium browser for voice input support) with these tabs:
1. **Tab 1 (Main Demo):** [http://localhost:5173](http://localhost:5173) (The Ledger Chat UI)
2. **Tab 2 (Backup / Technical Docs):** [http://localhost:8000/docs](http://localhost:8000/docs) (FastAPI Swagger UI)
3. **Tab 3 (Health Check):** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🎬 3. The 5-Minute Presentation Flow (Word-for-Word Guide)

### ⏱️ Segment 1: The Hook & The Problem (0:00 – 0:45)
**What to say:**
> "Hi everyone, we're presenting **Ledger** — an enterprise conversational database agent built on **Gemini 3.5 Flash-Lite**.
> 
> Most AI database assistants in the industry today suffer from a massive flaw: **they give raw LLMs direct write access to production databases.** If the model hallucinates or gets prompt-injected, someone can drop a table, leak private data, or run an unbounded query that crashes the server.
> 
> In Ledger, our core engineering philosophy is simple: **We Don't Trust the LLM.**
> 
> Ledger allows non-technical business users to query data in natural language, but every query goes through a multi-layered, zero-trust security defense before it ever touches PostgreSQL."

---

### ⏱️ Segment 2: Live Demo — Natural Language & Interactive Charts (0:45 – 1:45)
**Action:** In [http://localhost:5173](http://localhost:5173), type or click the starter prompt:
```text
Show me the top 5 customers by revenue.
```

**What to say & show while it runs:**
> "Watch the live tool stream on the screen:
> 1. First, Ledger **introspects the live PostgreSQL schema** — it doesn't hallucinate table structures.
> 2. Second, it generates the SQL and passes it through our **SQLGlot AST Validator**.
> 3. Third, it executes the query as a restricted **`agent_readonly`** PostgreSQL user in 10ms.
> 4. Fourth, it automatically renders an interactive visualization."

**Key actions on UI:**
* Hover over the **Bar Chart** to show live tooltip numbers (*Apex Technologies Corp at $36,030.05*).
* Toggle the **[Chart / Table]** switch to show the underlying table rows.
* Point to the **Export CSV** button: *"Business teams can export this clean dataset immediately for Excel or Google Sheets."*

---

### ⏱️ Segment 3: Trend Analysis & Statistical Anomaly Detection (1:45 – 2:45)
**Action:** Type the second prompt:
```text
Find unusual changes in monthly sales.
```

**What to say:**
> "Ledger doesn't just display static data; it includes **built-in statistical anomaly detection**.
> 
> Rather than letting the LLM invent numbers, Ledger runs deterministic mathematical algorithms directly on query results:
> * It computes moving baseline averages and Z-scores for every numerical metric.
> * Look at this highlighted alert on the screen: **May 2026 order volume spiked by +235.7% with a Z-score of 25.02**, deviating radically from the 70-order baseline.
> * Below the chart, Ledger provides an executive analysis explaining the business impact — pointing out that this volume tripled and flagging fulfillment and marketing readiness."

---

### ⏱️ Segment 4: Safe Self-Correction (2:45 – 3:30)
**Action:** Type the typo prompt:
```text
Show sales from the saless table.
```

**What to say:**
> "What happens when a user misspells something or a schema changes?
> * Here, I deliberately asked for a nonexistent table: `saless`.
> * The database returns a relation error. Instead of crashing, Ledger's **self-correction loop** activates.
> * The agent inspects the available schema, realizes the data lives in `orders` and `order_items`, repairs the SQL query, and re-executes.
> * **Crucial security guarantee:** The repaired query is NOT blindly run — it is re-validated through the AST security validator before execution."

---

### ⏱️ Segment 5: The Security Attack Test (3:30 – 4:15)
**Action:** Type the attack prompt:
```text
Delete all customers.
```

**What to say:**
> "Now, let's try a direct attack. I'm telling the agent to 'Delete all customers'.
> * Look at the immediate response: The agent refuses, stating it only has read-only access.
> * But what if an attacker bypasses the LLM via prompt injection?
> * **Defense Layer 1:** Our SQLGlot parser inspects the syntax tree. Any `DELETE`, `UPDATE`, `DROP`, `ALTER`, or `TRUNCATE` is immediately blocked at the gateway.
> * **Defense Layer 2:** Even if the AST parser were completely bypassed, PostgreSQL itself authenticates as `agent_readonly`. If you run `DELETE FROM customers;`, PostgreSQL natively returns `permission denied for table customers`.
> * Every single customer record remains 100% intact."

---

### ⏱️ Segment 6: Entity-Relationship Diagram & Schema Explorer (4:15 – 4:45)
**Action:** Type:
```text
Explain how customers, orders, and products are related.
```

**What to say:**
> "For non-technical stakeholders, Ledger dynamically builds **interactive Mermaid.js ER diagrams** by reading PostgreSQL foreign keys from `pg_catalog.pg_constraint` in real time.
> Users can visually understand relational links without ever reading a line of DDL."

---

### ⏱️ Segment 7: Voice Input & Wrap-Up (4:45 – 5:00)
**Action:** Click the **Microphone** icon in the input bar and say:
```text
Show monthly revenue for the last 12 months
```
*(Shows instant speech-to-text transcription via Web Speech API)*

**Closing statement:**
> "To summarize: Ledger gives organizations the power of conversational intelligence with Gemini 3.5 Flash-Lite, backed by strict mathematical anomaly detection and zero-trust, defense-in-depth database security.
> 
> Thank you, and we're happy to take your questions!"

---

## 🧠 4. Judge Q&A Defense Sheet (Be Ready for These Questions)

### Q1: *"Why did you use Gemini 3.5 Flash-Lite instead of a larger model like Gemini Pro or GPT-4?"*
> **Answer:** "For database analytics, speed and deterministic execution are paramount. Gemini 3.5 Flash-Lite has exceptional structured tool-calling capabilities with sub-second response times, and it dramatically reduces operational costs. Because Ledger enforces schema introspection and AST validation deterministically in code, we don't need a heavy, slow model to guard security — our code guards security."

### Q2: *"How do you prevent SQL injection?"*
> **Answer:** "Through two independent layers:
> 1. **AST Parsing via SQLGlot:** We parse the query into an Abstract Syntax Tree. We reject multiple statements (semicolon chaining), comments (`--`, `/* */`), and enforce that the root expression is strictly a `Select`. We also block dangerous PostgreSQL functions like `pg_sleep` or administrative primitives.
> 2. **PostgreSQL Role Permissions:** The agent connects strictly as `agent_readonly`. The database itself rejects all mutations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`) at the PostgreSQL engine level."

### Q3: *"What happens if a user query returns 1,000,000 rows or runs for 10 minutes?"*
> **Answer:** "Ledger enforces strict resource bounding:
> 1. **Row Limit:** Every query has a hard limit of **100 rows** enforced at both the SQL limit clause and execution layer, preventing memory exhaustion.
> 2. **Statement Timeout:** Every query is executed with `SET statement_timeout = '5000ms'` (5 seconds). Any slow Cartesian product or heavy join is terminated automatically by PostgreSQL."

### Q4: *"How does the anomaly detection work? Is it an AI hallucination?"*
> **Answer:** "No, the anomaly detection is completely mathematical and deterministic. It runs in Python using standard statistical formulas: it calculates the baseline mean and population standard deviation across historical time periods, identifies percentage changes exceeding 50%, and flags records with a Z-score $|Z| \ge 2.0$. The LLM is only used to explain the business implications of those pre-computed statistical anomalies."

---

## 🆘 5. Emergency Troubleshooting (Just In Case)

| Problem | Fix |
| :--- | :--- |
| **Backend says "Degraded" or Gemini rate limit hit** | Wait 20 seconds. Ledger has built-in adaptive backoff that automatically sleeps and retries. |
| **Port 8000 or 5173 in use** | Run `docker compose down` and restart with `docker compose up -d`. |
| **Microphone button doesn't work** | Ensure you are using Chrome, Edge, or Brave and have granted microphone permissions. If using Firefox/Safari, type the prompt manually. |
| **Need to show test coverage immediately** | Run `cd backend && pytest -q` in your terminal — all 57 tests pass in 2 seconds. |
