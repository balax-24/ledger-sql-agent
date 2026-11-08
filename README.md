# Ledger — Conversational Database Agent & Visualizer

**An Autonomous Natural-Language Analytics Platform with Defense-in-Depth SQL Security**

![Ledger chart generation](assets/chart_generation.png)

> "Translate natural language or voice commands into read-only SQL, generate interactive charts, detect statistical anomalies, inspect dynamic schema relationships, and self-correct queries safely — backed by rigorous AST parsing and database-level least privilege."

---

## 👥 Team & College Details
- **Team Name**: Blue Silver Avengers
- **Institution**: Sri Sairam Engineering College
- **Project Name**: Ledger
- **Hackathon**: Sairam Hackathon-2026
- **Team Members**: Balaharish S, Atchaya Santhiya D, Vishal Bharath V, Shruthi CS

---

## 📖 Table of Contents
1. [The Problem](#1-the-problem)
2. [The Ledger Solution](#2-the-ledger-solution)
3. [Zero-Trust Database Security Architecture](#3-zero-trust-database-security-architecture)
4. [System Architecture & Data Flows](#4-system-architecture--data-flows)
5. [Key Capabilities & Features](#5-key-capabilities--features)
6. [Repository Structure](#6-repository-structure)
7. [Tech Stack](#7-tech-stack)
8. [Configuration & Environment Variables](#8-configuration--environment-variables)
9. [API Reference](#9-api-reference)
10. [Agent Tool Registry](#10-agent-tool-registry)
11. [Database Schema & Seed Dataset](#11-database-schema--seed-dataset)
12. [Testing & Verification Suite](#12-testing--verification-suite)
13. [Pre-Demo Smoke Test](#13-pre-demo-smoke-test)
14. [Live Demo Walkthrough](#14-live-demo-walkthrough)
15. [Setup & Running Instructions (Docker & Local)](#15-setup--running-instructions-docker--local)
16. [Screenshots](#16-screenshots)

---

## 1. The Problem

Modern enterprises and educational institutions generate huge volumes of transactional data, but extracting immediate business intelligence remains inefficient:
* **The SQL Knowledge Barrier**: Over 90% of business managers, department heads, and operators cannot write SQL. Answering simple questions requires submitting tickets to BI or DBA teams, causing hours or days of delay.
* **Static Dashboard Inflexibility**: Pre-configured dashboards (Tableau, PowerBI) only answer questions anticipated during design. Ad-hoc inquiries or root-cause exploration hit dead ends.
* **The Text-to-SQL Security Dilemma**: Naive LLM text-to-SQL solutions are dangerous in production. Without strict guardrails, models can execute destructive statements (`DELETE`, `UPDATE`, `DROP`), lock critical tables (`SELECT ... FOR UPDATE`), call dangerous database functions (`pg_terminate_backend`, `dblink`), or crash databases with unbounded result sets.

---

## 2. The Ledger Solution

**Ledger** bridges this divide by providing an intelligent, natural-language conversational analytics assistant that empowers non-technical stakeholders while maintaining strict architectural safeguards:

* **Conversational Interface**: Ask business questions via text or native browser voice dictation.
* **Automated Visualizations**: Classifies query results and renders interactive Bar, Line, Pie, Area, and Scatter charts with Recharts, alongside instant tabular toggles.
* **Statistical Anomaly Detection**: Mathematically flags outliers and abrupt trends using leave-one-out Z-score profiling and percentage change analysis.
* **Schema Intelligence**: Discovers table structures and relationship foreign keys dynamically from PostgreSQL system catalogs, rendering interactive Mermaid.js Entity-Relationship (ER) diagrams and flowcharts.
* **Safe Self-Correction**: Recovers from syntax or typo errors automatically, guaranteeing that any corrected SQL passes through the full security validation pipeline before execution.
* **Data Portability**: Export results instantly to clean CSV (formatted with UTF-8 BOM for Microsoft Excel) or PNG graphics.

---

## 3. Zero-Trust Database Security Architecture

The core engineering guarantee of Ledger is simple: **We do not trust the LLM.**

Generated SQL is untrusted input. Ledger enforces a multi-layered defense-in-depth model:

```text
User Question / Voice Input
           │
           ▼
FastAPI Backend Agent Loop
           │
           ▼
    Gemini LLM (writes candidate SQL)
           │
           ▼
[ Layer 1: SQLGlot AST Validation ]
  ├── Enforces exactly one statement
  ├── Accepts ONLY Select / Union AST nodes
  ├── Rejects DDL/DML (Insert, Update, Delete, Drop, Create, Alter, Truncate)
  ├── Rejects locking clauses (FOR UPDATE, FOR SHARE, Lock)
  ├── Rejects dangerous functions (pg_sleep, pg_terminate_backend, dblink, file IO)
  └── Rewrites / clamps LIMIT to 100 rows
           │ (Blocked? -> Returns sanitized error, query aborted)
           ▼
[ Layer 2: PostgreSQL Statement Timeout ]
  └── SET statement_timeout = 5000 (5.0s hard execution limit)
           │
           ▼
[ Layer 3: PostgreSQL Role Isolation (agent_readonly) ]
  ├── Engine-level privilege enforcement
  ├── GRANTED: SELECT on tables and sequences
  └── DENIED: INSERT, UPDATE, DELETE, TRUNCATE, ALTER, DROP, CREATE, SUPERUSER
           │
           ▼
[ Layer 4: Response Sanitization & Slicing ]
  ├── Hard row slice (max 100 rows)
  └── Masking of internal paths, credentials, and raw driver tracebacks
```

### Self-Correction Security Guarantee
When an initial query encounters a database error (such as a misspelled table name), the agent performs self-correction. **The corrected query is never executed directly**—it must pass through the AST validator and policy checks again.

---

## 4. System Architecture & Data Flows

```mermaid
flowchart TD
    User([User Prompt / Voice]) <-->|1. Input & Visualizations| UI[React 18 + Vite Frontend]
    UI <-->|2. Server-Sent Events SSE Stream| Backend[FastAPI Backend Application]
    Backend <-->|3. Tool Calling Protocol| LLM[Google Gemini 3.5 Flash-Lite]

    subgraph Security_Engine [Defense-in-Depth Security Engine]
        Backend -->|4. AST Parse & Security Policy| AST[SQLGlot AST Validator]
        AST -->|5. Analytical SELECT Only| DBPolicy[100-Row Limit & 5s Timeout]
    end

    DBPolicy -->|6. Restricted Connection Pool| PG[(PostgreSQL: agent_readonly)]
    PG -->|7. Raw Record Tuples| Backend

    subgraph Analytics_Layer [Statistical & Visual Pipeline]
        Backend -->|8. Z-Score & Outlier Detection| Anomaly[Anomaly Detection Engine]
        Backend -->|9. ER / Flowchart Generation| Diagram[Mermaid Diagram Generator]
    end

    Anomaly -->|10. Streamed Tool Badges & Data Payloads| UI
    Diagram -->|10. Streamed Tool Badges & Data Payloads| UI
```

A compact one-page version of this flow lives in [Architecture.md](Architecture.md).

---

## 5. Key Capabilities & Features

### 5.1 Dynamic Schema Introspection & Discovery
Unlike basic bots that hardcode static schemas into system prompts, Ledger queries `pg_catalog.pg_constraint` and `information_schema.columns` on demand. It discovers:
- Table names and column types
- Primary keys and relational foreign keys
- Relationships mapped into Mermaid ER diagrams (`CUSTOMERS ||--o{ ORDERS`)
- Dynamically generated starter questions based on live tables (`GET /api/starter-questions`)

### 5.2 Deterministic Statistical Anomaly Detection
Ledger detects outliers mathematically in `app/analysis/anomaly.py`:
- **Sample Requirement**: Analyzes numeric series with $\ge 6$ data points.
- **Metric Filtering**: Excludes ID-like keys (`id`, `*_id`).
- **Z-Score Calculation**: Calculates leave-one-out mean ($\mu$) and standard deviation ($\sigma$).
- **Dual Thresholds**: Flags points with $|Z| \ge 2.0$ AND relative change $|\Delta\%| \ge 50\%$.
- **Zero-Division Protection**: Handles constant baselines and zero-deviation series gracefully without division errors.

### 5.3 Interactive Visualizations & Data Export
- Automatic chart type selection based on data geometry:
  - Temporal trends $\to$ **Line** or **Area** chart
  - Categorical rankings $\to$ **Bar** chart
  - Proportional distributions $\to$ **Pie** chart
  - Two-dimensional numeric relations $\to$ **Scatter** plot
- Dynamic **[Chart | Table]** toggle switch in `ChartCard.jsx`.
- Clean **Export CSV** with UTF-8 BOM encoding for seamless Excel import.
- High-resolution **Export PNG** for presentation decks.

### 5.4 Voice-Driven Data Exploration
- Integrated Web Speech API in `InputBar.jsx`.
- Click-to-dictate with real-time pulsing waveform indicator.
- Browser compatibility fallback: gracefully alerts users on unsupported browsers (Firefox/Safari) without crashing.

---

## 6. Repository Structure

```text
hackathon-agent/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, CORS, /api routes, SSE streaming
│   │   ├── config.py                # Pydantic v2 BaseSettings, environment configuration
│   │   ├── db.py                    # asyncpg connection pool & reconnection management
│   │   ├── gemini_client.py         # LLMProvider interface (RealGeminiProvider, MockGeminiProvider)
│   │   ├── agent.py                 # Multi-turn tool execution loop & structured logging
│   │   ├── logger.py                # Structured logger with request ID context
│   │   ├── seed.py                  # Database seeder with controlled anomaly dataset
│   │   │
│   │   ├── tools/                   # Autonomous agent tool registry
│   │   │   ├── schema_tool.py       # Catalog introspection & foreign key discovery with TTL cache
│   │   │   ├── query_tool.py        # SQLGlot AST validation, 100-row limit, self-correction
│   │   │   ├── chart_tool.py        # Structured chart payload formatter
│   │   │   ├── diagram_tool.py      # Mermaid ER & flowchart generator
│   │   │   └── explain_tool.py      # Data summary generator
│   │   │
│   │   └── analysis/                # Mathematical engine
│   │       └── anomaly.py           # Z-score & percentage deviation anomaly detection
│   │
│   ├── tests/                       # Pytest automated test suite (57 tests)
│   │   ├── test_sql_security.py     # 22 AST validation & injection tests
│   │   ├── test_self_correction.py  # Self-correction security & re-validation tests
│   │   ├── test_anomaly_detection.py# Statistical math, Z-score, & edge case tests
│   │   ├── test_api_and_integration.py # MockGemini end-to-end integration tests
│   │   └── test_tools.py            # Tool specification & registry tests
│   │
│   ├── pytest.ini                   # Pytest configuration & asyncio mode settings
│   ├── requirements.txt             # Python production & test dependencies
│   ├── schema.sql                   # Database DDL & agent_readonly role creation
│   └── seed_data.sql                # Pre-generated seed SQL data
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx             # Conversational stream manager & message list
│   │   │   ├── EmptyState.jsx       # Starter query cards with judge demo prompts
│   │   │   ├── InputBar.jsx         # Textarea & voice dictation handler
│   │   │   ├── SchemaExplorer.jsx   # Interactive slide-over table & column drawer
│   │   │   ├── ChartCard.jsx        # Recharts visualizer, [Chart/Table] toggle, CSV export
│   │   │   ├── DiagramCard.jsx      # Mermaid SVG renderer with error boundaries
│   │   │   └── ToolActivity.jsx     # Real-time SSE tool execution badges
│   │   ├── App.jsx                  # Main application layout & header
│   │   ├── index.css                # Tailwind & custom glassmorphism styles
│   │   └── main.jsx                 # React root mountpoint
│   ├── package.json                 # Node dependencies (Vite, React 18, Recharts, Mermaid)
│   └── vite.config.js               # Vite configuration & /api reverse proxy
│
├── scripts/
│   ├── smoke_test.py                # Pre-demo diagnostic verification script
│   └── smoke_test.sh                # Executable shell runner for smoke test
│
├── docker-compose.yml               # Production Compose stack (postgres, backend, frontend)
├── Architecture.md                # One-page request-flow diagram
├── PRESENTATION_PLAYBOOK.md       # Hackathon pitch & live demo playbook
├── DEMO_GUIDE.md                    # 5-minute judge demo script & presentation flow
├── EVALUATION_GUIDE.md              # Evaluator & judge documentation
└── README.md                        # Master documentation
```

---

## 7. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18, Vite 5, Tailwind CSS | High-performance reactive UI with dark aesthetics |
| **Visualizations** | Recharts 2.12 | Responsive SVG Bar, Line, Pie, Scatter charts |
| **Diagrams** | Mermaid.js 10 | Interactive Entity-Relationship & flowchart diagrams |
| **Audio** | HTML5 Web Speech API | Client-side speech-to-text dictation |
| **Backend** | FastAPI, Uvicorn, Python 3.12+ | Async REST API & Server-Sent Events (SSE) |
| **SQL Security** | SQLGlot 25.0+ | Abstract Syntax Tree (AST) query validation |
| **Database Client** | asyncpg 0.29+ | High-throughput asynchronous PostgreSQL client |
| **Database** | PostgreSQL 16 (Alpine) | Relational store with role-based least privilege |
| **LLM Provider** | Google GenAI SDK (Gemini 3.5 Flash-Lite) | Natural language reasoning & tool selection |

---

## 8. Configuration & Environment Variables

The backend uses Pydantic v2 settings. Configure environment variables in `backend/.env`:

| Variable | Required | Default Value | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | — | Google AI Studio Gemini API Key |
| `GEMINI_MODEL` | No | `gemini-3.5-flash-lite` | Gemini model version |
| `DATABASE_URL` | **Yes** | `postgresql://agent_readonly:ledger_readonly_dev@localhost:5433/postgres` | Restricted read-only PostgreSQL connection string |
| `QUERY_ROW_LIMIT` | No | `100` | Maximum rows returned per analytical query |
| `QUERY_TIMEOUT_SECONDS` | No | `5.0` | Maximum execution time in seconds per query |
| `ANOMALY_Z_SCORE_THRESHOLD` | No | `2.0` | Z-score threshold for outlier detection |
| `ANOMALY_PERCENT_CHANGE_THRESHOLD` | No | `0.5` | Percentage change threshold ($\ge 50\%$) |
| `FRONTEND_ORIGIN` | No | `http://localhost:5173` | Allowed CORS origin |

---

> **Credentials:** `ledger_readonly_dev` is a throwaway password for the local Docker database only (set in `backend/schema.sql` and `docker-compose.yml`). Use your own strong password for any shared or hosted database, and never commit `backend/.env`.

## 9. API Reference

### `GET /api/health`
Health check diagnostics verifying database connectivity and Gemini availability.
```json
{
  "status": "healthy",
  "database": "connected",
  "model": "available"
}
```

### `GET /api/schema`
Returns all discovered tables, columns, primary keys, and foreign keys.
```json
{
  "tables": [
    {
      "name": "customers",
      "columns": [{"name": "id", "type": "integer"}, {"name": "name", "type": "text"}],
      "primary_keys": ["id"],
      "foreign_keys": []
    }
  ]
}
```

### `GET /api/starter-questions`
Returns dynamic suggested questions based on live introspected tables.
```json
{
  "questions": [
    "Show me the top 5 customers by revenue",
    "Show monthly revenue trends for the last 12 months",
    "Find unusual changes in monthly sales",
    "Draw me the ER diagram for this database"
  ]
}
```

### `POST /api/chat`
Main streaming SSE endpoint. Accepts `{ "messages": [...] }` and streams structured JSON events:
- `tool_call`: Dispatched when an agent executes a tool (`get_schema`, `execute_query`, etc.)
- `tool_result`: Dispatched with tool output metadata
- `token`: Streamed natural language explanation chunks
- `error`: Dispatched on operational failures
- `done`: Dispatched upon completion

---

## 10. Agent Tool Registry

1. **`get_schema`**: Introspects tables, columns, PKs, and FKs from PostgreSQL system catalogs.
2. **`execute_query`**: Validates SQL via SQLGlot AST, enforces 100-row limit, sets 5s timeout, executes via `agent_readonly`, and returns tabular rows.
3. **`generate_chart`**: Prepares typed chart configuration (`bar`, `line`, `pie`, `scatter`) for Recharts.
4. **`generate_flowchart`**: Generates Mermaid.js syntax for ER diagrams and business flowcharts.
5. **`explain_data`**: Performs Z-score anomaly calculations and summarizes insights in clear plain English.

---

## 11. Database Schema & Seed Dataset

The provided schema represents an enterprise e-commerce model:
- **`customers`** (50 records): Customer names, emails, cities, signup dates.
- **`products`** (35 records): Catalog items across categories with unit costs and prices.
- **`orders`** (1,003 records): Orders across 12 months (2025–2026) with statuses and order dates.
- **`order_items`** (1,668 records): Individual line items linking orders and products with quantities and unit prices.

### Controlled Seed Anomaly
The dataset features a deliberate, realistic promotional campaign spike in **May 2026**:
- Normal baseline: ~40 orders / \$8,500 monthly revenue.
- May 2026 spike: **150 orders / \$32,000+ monthly revenue (+235% surge)**.
- Ledger's anomaly detector flags this spike with $Z \ge 15.0$ and visual warning badges.

---

## 12. Testing & Verification Suite

Ledger includes a comprehensive automated test suite covering security, query limits, self-correction, anomaly statistics, and end-to-end integration:

```bash
cd backend
pytest -q
```

### Actual Test Execution Output:
```text
.........................................................                [100%]
57 passed in 1.05s
```

### Test Breakdown:
- **`test_sql_security.py` (22 tests)**: Verifies AST rejection of `DELETE`, `UPDATE`, `INSERT`, `DROP`, `ALTER`, `TRUNCATE`, `SELECT ... FOR UPDATE`, stacked queries, `pg_sleep`, filesystem access, and verifies `LIMIT 100` enforcement.
- **`test_self_correction.py` (5 tests)**: Verifies that self-correction recovers from syntax errors, blocks malicious `DELETE` and `DROP TABLE` corrections, blocks row locking, and handles failures cleanly.
- **`test_anomaly_detection.py` (9 tests)**: Verifies statistical spike detection, drop detection, normal series, datasets $<6$ rows, constant series, decimal amounts, ID column filtering, and exact seeded May 2026 anomaly (+235.7%, Z = 25.02).
- **`test_api_and_integration.py` (5 tests)**: Full end-to-end integration test using `MockGeminiProvider`, checking SSE streaming, `/api/health`, `/api/schema`, and error sanitization. `test_api_schema` needs the PostgreSQL container running (`docker compose up -d postgres`).
- **`test_tools.py` (16 tests)**: Unit tests for individual agent tools, including schema introspection, foreign-key mapping, TTL caching and Mermaid ER generation.

---

## 13. Pre-Demo Smoke Test

Before demonstrating to judges, run the automated smoke test script to verify database connectivity, schema availability, analytical queries, security rejections, and anomaly math:

```bash
./scripts/smoke_test.sh
```

### Verified Smoke Test Output:
```text
======================================================
           LEDGER PRE-DEMO SMOKE TEST SUITE
======================================================

 ✓ Database reachable and responsive
 ✓ Schema available (4 tables: customers, order_items, orders, products)
 ✓ SELECT query works (returned 50 sample rows)
 ✓ DELETE blocked by AST validator
 ✓ UPDATE blocked by AST validator
 ✓ DROP blocked by AST validator
 ✓ Dangerous function pg_sleep blocked by AST validator
 ✓ Query timeout configured (5.0s limit, 100 row limit)
 ✓ Anomaly detector works (identified May spike: +235.7% change, z-score 25.02)

------------------------------------------------------
 ✓ ALL CRITICAL SMOKE TESTS PASSED!
   Ledger is judge-ready with defense-in-depth security controls validated through automated tests.
```

---

## 14. Live Demo Walkthrough

Follow these 6 recommended prompts during your hackathon presentation (see [DEMO_GUIDE.md](DEMO_GUIDE.md) for the full script):

1. **Analytical Query & Chart**:
   `"Show me the top 5 customers by revenue"`
   *Result:* Bar chart of top spenders, interactive hover tooltips, [Chart/Table] toggle, and CSV export.
2. **Trend Analysis Over Time**:
   `"Show monthly revenue for the last 12 months"`
   *Result:* Line chart illustrating annual revenue trends.
3. **Statistical Anomaly Detection**:
   `"Find unusual changes in monthly sales"`
   *Result:* Flags the May 2026 promotional surge with mathematical Z-score (+235.7% change, Z = 25.02).
4. **Resilient Self-Correction**:
   `"Show sales from the saless table"`
   *Result:* Identifies table typo, heals query to use `orders`, and re-validates securely before executing.
5. **Security Enforcement**:
   `"Delete all customers"`
   *Result:* **BLOCKED.** Demonstrates that neither AST validator nor `agent_readonly` role permit writes.
6. **Entity-Relationship Diagram**:
   `"Explain how customers, orders, and products are related"`
   *Result:* Interactive Mermaid ER diagram mapping relational connections and plain-English breakdown.

---

## 15. Setup & Running Instructions (Docker & Local)

### Option A — Full Stack via Docker Compose (Recommended)

Requires Docker & Docker Compose:

1. Clone repository and create `backend/.env`:
   ```bash
   cp backend/.env.example backend/.env
   # Add your GEMINI_API_KEY into backend/.env
   ```
2. Build and start all services (PostgreSQL, Backend, Frontend):
   ```bash
   docker compose up --build
   ```
3. Access the application:
   - **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Option B — Local Development Setup

#### 1. Start Database Container
```bash
docker compose up -d postgres
```
*PostgreSQL will be accessible at `localhost:5433` with database `postgres` and role `agent_readonly`.*

#### 2. Configure & Start Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Verify backend/.env contains your GEMINI_API_KEY and DATABASE_URL:
# DATABASE_URL=postgresql://agent_readonly:ledger_readonly_dev@localhost:5433/postgres

# Run pre-demo smoke test
../scripts/smoke_test.sh

# Start backend server
uvicorn app.main:app --reload --port 8000
```

#### 3. Start Frontend Development Server
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 16. Screenshots

| Chart generation | ER diagram | Schema explorer |
|---|---|---|
| ![Chart generation](assets/chart_generation.png) | ![ER diagram](assets/er_diagram.png) | ![Schema explorer](assets/schema_explorer.png) |
