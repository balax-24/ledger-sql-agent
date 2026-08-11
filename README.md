# Ledger — Secure, Conversational Database Assistant & Visualizer

**An Autonomous AI-Powered Data Analyst & Visualizer for PostgreSQL**

> "Translate natural language or voice commands to read-only SQL, automatically recommend interactive charts, detect statistical anomalies, self-correct broken queries, and visualize table relationships — with absolute security."

---

## 👥 Team & College Details
- **Team Name**: Blue Silver Avengers
- **Institution**: Sri Sairam Engineering College
- **Project Name**: Ledger
- **Hackathon**: Sairam Hackathon-2026
- **Team Members**: [Add Names Here]

---

## 📖 Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [The Ledger Solution](#2-the-ledger-solution)
3. [Key Innovations & Technical Upgrades](#3-key-innovations--technical-upgrades)
4. [System Architecture & Data Flows](#4-system-architecture--data-flows)
5. [Detailed File & Project Structure](#5-detailed-file--project-structure)
6. [Tech Stack Breakdown](#6-tech-stack-breakdown)
7. [Comprehensive Environment Configurations](#7-comprehensive-environment-configurations)
8. [API Route Reference](#8-api-route-reference)
9. [Agent Tool Specifications](#9-agent-tool-specifications)
10. [Database Schema & Seed Data Structure](#10-database-schema--seed-data-structure)
11. [Step-by-Step Demo Scenarios](#11-step-by-step-demo-scenarios)
12. [Enterprise Security & Guardrail Checklist](#12-enterprise-security--guardrail-checklist)
13. [Verification, Tests, & Validation Suite](#13-verification-tests--validation-suite)
14. [Roadmap & Future Enhancements](#14-roadmap--future-enhancements)
15. [Setup & Running Instructions (Docker & Local)](#15-setup--running-instructions-docker--local)

---

## 1. Problem Statement

Modern enterprise and educational institutions generate massive volumes of database records daily. However, extracting business intelligence or simple answers from these databases remains highly inefficient:
* **The Technical Divide**: Over 90% of business managers, department heads, and administrative staff do not know SQL. Whenever they need data (such as monthly sales trends or department performance), they must request it from a DBA or BI developer, creating days of delays.
* **Static Dashboard Bottlenecks**: Pre-built dashboards (e.g. Tableau, PowerBI) only answer questions that developers anticipated beforehand. If a user wants to explore a new follow-up question or understand *why* a particular number dipped, static charts fail.
* **Text-to-SQL Security Risks**: Basic AI text-to-SQL assistants present serious security flaws. If a user is allowed to execute arbitrary AI-generated SQL, it can lead to accidental database modification (`UPDATE`), table deletion (`DROP`), resource exhaustion (queries with no limit), or SQL injection attacks.

---

## 2. The Ledger Solution

**Ledger** bridge this technical divide. It serves as an autonomous, conversational database assistant that translates plain English or spoken words into optimized, read-only SQL, runs it, recommends the best chart type, and delivers a simple natural-language explanation.

Ledger connects directly to your SQL database, providing immediate, conversational access to information. Key features include:
* **Ask in English or Voice**: Query data by typing or using native browser voice dictation.
* **Auto-Recommends Charts**: Categorizes and plots results in Bar, Line, Pie, Area, or Scatter charts automatically.
* **Generates Schema Diagrams**: Automatically renders Mermaid.js ER (Entity-Relationship) diagrams.
* **Detects Anomalies**: Mathematically computes and highlights data anomalies (spikes/drops).
* **Self-Corrects SQL**: Automatically heals database connection syntax or schema errors under the hood.

---

## 3. Key Innovations & Technical Upgrades

Ledger includes several production-grade improvements over standard prototype AI bots:

### 3.1 Dual-Layer Database Security Shield
Security is built into Ledger's core architecture, rather than added as an afterthought:
* **Layer 1: AST parsing (sqlglot)**: When the AI agent writes a query, the backend uses the `sqlglot` library to parse it into an Abstract Syntax Tree (AST). It inspects the tree node-by-node. If any node matches an modifying keyword (such as `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, or `CREATE`), the query is blocked before it reaches the database.
* **Layer 2: PostgreSQL Role Isolation**: Ledger connects to PostgreSQL using a strictly restricted user account (`agent_readonly`). This user is granted *only* `SELECT` privileges on the public schema. PostgreSQL will block any unauthorized writes at the database engine level, even if the parser fails.
* **Automatic Row Constraints**: The backend wraps every user query in a subquery or appends a strict `LIMIT 100` clause. This guards against giant tables loading thousands of rows, preventing memory overload and keeping response times under 200ms.

### 3.2 Schema-Aware Starter Questions
Standard database bots use hardcoded sample questions. If you point them at a new database, those questions break. 
Ledger resolves this with a **dynamic schema inspector** (`GET /api/starter-questions`). On startup, the backend:
1. Inspects the active database catalog tables.
2. Identifies table names and numeric columns suitable for aggregation (e.g., `revenue`, `quantity`, `price`).
3. Ignores primary/foreign keys (`*_id`, `id`) to avoid suggesting useless metrics.
4. Templates these columns into natural questions, such as: *"Show me products by price"* or *"List orders count by order_date"*.
5. The frontend displays these questions as clickable starter cards.

### 3.3 Statistical Anomaly Detection (Z-Score Profiling)
Instead of relying on the AI model to hallucinate whether data is "good" or "bad," Ledger performs real-time mathematical analysis (`app/analysis/anomaly.py`):
* When a dataset is returned, it identifies numeric columns.
* For tables with 6 or more records (to establish statistical relevance), it calculates the **mean** and **standard deviation** using a leave-one-out method.
* Points with a Z-score greater than `2.0` (spike) or less than `-2.0` (drop) are flagged as anomalies.
* These anomalies are passed to the `explain_data` tool, allowing the AI to summarize and explain the spikes/drops using actual business context.

### 3.4 Robust SQL Self-Correction (Two-Phase Healer)
AI models occasionally hallucinate table names or make syntax errors. Ledger uses a two-phase self-correction system (`app/tools/query_tool.py`) to keep the experience smooth:
* **Phase 1: Parse Correction**: If the `sqlglot` parser fails to read the SQL due to missing syntax or malformed structures, the error is immediately caught, and a one-shot correction query is sent to Gemini to repair the AST.
* **Phase 2: Execution Correction**: If the database throws a syntax or schema error (e.g., column does not exist), the backend intercepts the `asyncpg` exception, combines it with the current database schema structure, and asks the AI to repair the SQL statement. The corrected SQL is validated and run immediately.

### 3.5 Native Speech-to-Text Voice Input
Ledger provides a hands-free query option using the HTML5 **Web Speech API**:
* A dedicated microphone button sits next to the chat bar.
* Clicking the microphone triggers a pulsing visual state, recording voice in real time.
* The voice transcription is automatically inserted into the chat bar for execution.

---

## 4. System Architecture & Data Flows

Ledger is built as a highly decoupled FastAPI backend and React frontend system:

```mermaid
flowchart TD
    User([User Prompt / Voice]) <-->|1. Plain Text Transcript| UI[React Frontend]
    UI <-->|2. JSON SSE Stream| Backend[FastAPI Web Server]
    Backend <-->|3. Structured Tool Messages| Gemini[Gemini 3.1 Flash-Lite]
    
    subgraph Backend Services
        Backend <-->|4. AST Parse Check| Validator[SQLGlot Parser]
        Backend <-->|5. Read-Only Query| DB[(PostgreSQL Database)]
        Backend <-->|6. Z-Score Calculation| Anomaly[Anomaly Profiler]
    end
```

### 4.1 Detailed Request Execution Lifecycle
1. **Input Stage**: The user enters a question: *"Show monthly orders."*
2. **Streaming Start**: The frontend initiates an EventSource connection to `/api/chat`.
3. **Agent Loop**: The backend loads the conversational history, binds the Gemini 3.1 client, and enters a tool-execution loop.
4. **Tool: `get_schema`**: The agent fetches the database schema to check available tables (`orders`, `customers`).
5. **SQL Generation**: The agent writes a raw SQL string: `SELECT date_trunc('month', order_date), COUNT(*) FROM orders GROUP BY 1`.
6. **Tool: `execute_query`**:
   - **AST Validation**: `sqlglot` validates the SQL to ensure it is read-only.
   - **Database Query**: Executed against PostgreSQL via `asyncpg`.
   - **Anomaly Check**: If the result set is $>6$ rows, Z-scores are calculated.
   - **Visual Recommendation**: Classifies data types (categorical vs. temporal) to recommend a chart (e.g., Line Chart).
7. **Tool: `explain_data`**: Summarizes the resulting numbers into natural-language bullet points.
8. **Completion**: The final output, chart payload, and follow-up suggestions are sent to the user.

---

## 5. Detailed File & Project Structure

The project layout separates frontend views from backend logic:

```
hackathon-agent/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI server configuration, lifespan events, routes, CORS
│   │   ├── config.py                # Environment configurations (settings, db credentials)
│   │   ├── database.py              # PostgreSQL asyncpg connection pool management
│   │   ├── gemini_client.py         # Google Gemini API connector & text generators
│   │   ├── agent.py                 # Multi-turn tool execution loop
│   │   ├── seed.py                  # Seed script populating mockup tables
│   │   │
│   │   ├── api/                     # API routers
│   │   │   └── chat.py              # Server-Sent Events stream routing
│   │   │
│   │   ├── tools/                   # Declarative tools for LLM
│   │   │   ├── schema_tool.py       # Retrieves schema metadata
│   │   │   ├── query_tool.py        # Validates, runs, and auto-corrects SQL
│   │   │   ├── chart_tool.py        # Builds chart payloads
│   │   │   ├── diagram_tool.py      # Generates Mermaid.js diagrams
│   │   │   └── explain_tool.py      # Analyzes metrics and provides summaries
│   │   │
│   │   └── analysis/                # Statistical layer
│   │       └── anomaly.py           # Z-score statistical anomaly detection
│   │
│   ├── tests/                       # Pytest verification suites
│   │   └── test_tools.py            # Unit tests for query parsing, anomalies, and correction
│   │
│   ├── requirements.txt             # Python dependency packages
│   ├── schema.sql                   # Database table structure & security role queries
│   └── docker-compose.yml           # Multi-container environment orchestrator
│
├── frontend/
│   ├── src/
│   │   ├── components/              # UI components
│   │   │   ├── ChatInterface.jsx    # Conversational flow, dictation controls
│   │   │   ├── EmptyState.jsx       # Starter questions grid
│   │   │   ├── SchemaSidebar.jsx    # Table explorer
│   │   │   ├── ChartRenderer.jsx    # Recharts rendering, CSV/PNG exports
│   │   │   └── MermaidRenderer.jsx  # Mermaid diagram visualizer
│   │   ├── App.jsx                  # Main dashboard layout
│   │   ├── App.css                  # Neon dark-mode styling
│   │   └── main.jsx                 # Vite application mountpoint
│   ├── package.json                 # Node packages
│   └── vite.config.js               # Vite compilation configuration & API proxying
│
├── README.md                        # Master project documentation
└── EVALUATION_GUIDE.md              # Evaluator manual
```

---

## 6. Tech Stack Breakdown

### Frontend UI:
* **React 18**: Reactive components, hooks, and component lifecycle management.
* **Vite**: Rapid compiler and hot-reloader.
* **Recharts**: Responsive SVG graphs (Bar, Line, Pie, Area, Scatter).
* **Mermaid.js**: Client-side parsing of text descriptions into interactive ER diagrams.
* **HTML5 Speech Recognition**: Integrated speech-to-text dictation.

### Backend API:
* **FastAPI**: Lightweight, asynchronous web framework.
* **sqlglot**: SQL parser used for AST verification.
* **asyncpg**: Fast PostgreSQL driver.
* **Uvicorn**: ASGI web server.

### AI Brain:
* **Google Gemini 3.1 Flash-Lite**: Fast, low-latency LLM model.
* **Google GenAI Python SDK**: Native python bindings.

---

## 7. Comprehensive Environment Configurations

Create a `.env` file in the `backend/` directory using these variables:

| Variable Name | Required | Description | Example / Default Value |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | Your API Key from Google AI Studio. | `AIzaSy...` |
| `GEMINI_MODEL` | No | Model version to load. | `gemini-3.1-flash-lite` |
| `DATABASE_URL` | **Yes** | Main connection string to PostgreSQL. | `postgres://user:pass@localhost:5432/db` |
| `FRONTEND_ORIGIN` | No | Allowed CORS origin for local UI. | `http://localhost:5173` |

No credentials or API keys are exposed to the frontend; the backend proxies all requests securely.

---

## 8. API Route Reference

Ledger exposes these JSON endpoints:

### 8.1 `GET /api/health`
* **Purpose**: Performs a diagnostics check.
* **Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "gemini_api": "available"
}
```

### 8.2 `GET /api/starter-questions`
* **Purpose**: Serves dynamically generated starter questions based on the database schema.
* **Response**:
```json
[
  "Show me products by price",
  "List orders count by order_date",
  "Total quantity of order_items"
]
```

### 8.3 `GET /api/schema`
* **Purpose**: Returns database tables, columns, and types.
* **Response**:
```json
{
  "customers": {
    "columns": {"id": "integer", "name": "text", "email": "text"}
  }
}
```

### 8.4 `POST /api/chat`
* **Purpose**: Main streaming endpoint. Accepts conversational input and returns an SSE stream of tool calls and answers.
* **Request Body**:
```json
{
  "message": "Show monthly revenue trends",
  "history": []
}
```

---

## 9. Agent Tool Specifications

Ledger registers five tools with the Gemini API to interact with the database:

1. **`get_schema`**:
   - **Input**: None
   - **Output**: Returns database tables, columns, data types, primary keys, and foreign keys.
2. **`execute_query`**:
   - **Input**: `{ "sql": "SELECT * FROM products" }`
   - **Validation**: Enforces AST validation (SELECT-only), appends `LIMIT 100`, and handles self-correction if the syntax is incorrect.
   - **Output**: Returns `{ "columns": [...], "rows": [...], "row_count": X }`.
3. **`generate_chart`**:
   - **Input**: `{ "chart_type": "line", "x_axis": "month", "y_axis": "revenue", "data": [...] }`
   - **Output**: Formats chart configurations for the frontend.
4. **`generate_flowchart`**:
   - **Input**: `{ "diagram_type": "er" }`
   - **Output**: Generates a Mermaid-formatted ER diagram string mapping tables and keys.
5. **`explain_data`**:
   - **Input**: `{ "question": "...", "query_result": "..." }`
   - **Output**: Performs Z-score anomaly calculations and returns a text-based summary of the findings.

---

## 10. Database Schema & Seed Data Structure

The seed script creates a 4-table e-commerce schema to demonstrate Ledger's capabilities:

```
+------------------+         +------------------+
|    customers     |         |     products     |
+------------------+         +------------------+
| customer_id (PK) |         | product_id (PK)  |
| name             |         | name             |
| email            |         | price            |
| city             |         +--------+---------+
| signup_date      |                  |
+--------+---------+                  | (1-to-many)
         |                            |
         | (1-to-many)                v
         |                   +------------------+
         v                   |   order_items    |
+------------------+         +------------------+
|     orders       |         | order_item_id PK |
+------------------+         | order_id (FK)    |
| order_id (PK)    |-------->| product_id (FK)  |
| customer_id (FK) |         | quantity         |
| order_date       |         | unit_price       |
| status           |         +------------------+
+------------------+
```

The seed script (`python -m app.seed`) populates these tables with ~12 months of mock records:
* **Temporal Trend**: Generates order records across the year.
* **Deliberate Anomaly**: Simulates a sudden drop in product orders in the most recent month to test the anomaly detection engine.

---

## 11. Step-by-Step Demo Scenarios

Here is a typical test path for evaluating Ledger:

### Scenario 1: Natural Language Query & Visualizations
* **User prompt**: *"Show me the top 5 customers by order count."*
* **Ledger action**: Writes a `GROUP BY` SQL query, runs it, formats the results as a Bar Chart, and explains the top customers.
* **Interactive tools**: Click **Download PNG** or **Export CSV** in the UI to download the data immediately.

### Scenario 2: Conversational Memory
* **User prompt**: *"Show their emails."*
* **Ledger action**: Resolves "their" to refer to the top 5 customers, generates a new SQL query joining `customers` and `orders`, and displays the email list.

### Scenario 3: Diagram Generation
* **User prompt**: *"Draw me the ER diagram of this database."*
* **Ledger action**: Resolves table connections using database foreign keys and renders a Mermaid.js diagram showing tables and columns.

### Scenario 4: Error Handling & Self-Correction
* **User prompt**: *"Select revenue from a_table_that_does_not_exist"*
* **Ledger action**: Detects the database error, attempts to self-correct the query, and reports the error cleanly if correction fails, preventing a crash.

---

## 12. Enterprise Security & Guardrail Checklist

Ledger includes several security protections:

- [x] **Read-Only Enforced**: The SQL parser blocks writing commands (`INSERT`, `UPDATE`, `DELETE`, `DROP`).
- [x] **No Stacked Statements**: Prevents SQL injection by blocking semicolons (`;`) that chain multiple queries.
- [x] **PostgreSQL Level Protection**: Connection strings use a restricted `agent_readonly` user.
- [x] **Row Limitations**: Automatically appends a `LIMIT 100` clause to all queries.
- [x] **Sanitized Error Logs**: Driver errors and database details are sanitized before returning to the frontend.
- [x] **Secure Key Management**: API keys live on the server and are never exposed to the browser.

---

## 13. Verification, Tests, & Validation Suite

Ledger includes unit and integration tests using `pytest`:
* **Security Tests**: Verifies that SQL parser blocks modifying queries.
* **Self-Correction Tests**: Confirms the healer resolves syntax errors.
* **Anomaly Profiling Tests**: Validates Z-score calculations.

To run the backend tests:
```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/
```
Output:
```
============================== 16 passed in 0.76s ==============================
```

---

## 14. Roadmap & Future Enhancements

Future updates planned for Ledger:
* **Gemini Native Tool Calling**: Transition to native function call schemas.
* **Persistent History**: Store past conversations in the database.
* **PDF Reports**: Export compiled charts, tables, and AI explanations to PDF.
* **Multi-DB routing**: Query across multiple databases simultaneously.

---

## 15. Setup & Running Instructions (Docker & Local)

Ensure you have your **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/apikey) and a **PostgreSQL Database** running.

### Option A — Spin Up via Docker (Recommended)
This runs the entire system in isolated containers with a single command:

1. Create a `.env` file in the `backend/` folder (copy `backend/.env.example` as a template). Make sure `GEMINI_API_KEY` is set.
2. From the root directory, run:
   ```bash
   docker-compose up --build
   ```
3. Open [http://localhost:5173](http://localhost:5173) in your browser.

---

### Option B — Local Setup (Manual)

#### 1. Setup the Database & Seed Data
1. Run the `backend/schema.sql` queries on your database instance to provision tables (`customers`, `products`, `orders`, `order_items`) and configure the `agent_readonly` database role.
2. In a new terminal, navigate to the `backend/` directory and configure the Python environment:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a `backend/.env` file containing:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.1-flash-lite
   DATABASE_URL=postgres://your_postgres_username:your_password@localhost:5432/your_database_name
   FRONTEND_ORIGIN=http://localhost:5173
   ```
4. Seed the database with realistic sample store data:
   ```bash
   python -m app.seed
   ```
5. **Security Isolation (Important)**: Replace the `DATABASE_URL` in `backend/.env` with your restricted `agent_readonly` user role string to ensure the agent runs with zero write permissions.

#### 2. Start Backend API
Make sure your virtual environment is active, or run it directly using the `.venv` path:
```bash
# Run with virtual environment activated:
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Or run directly without activating:
.venv/bin/uvicorn app.main:app --reload --port 8000
```
Verify the API is running at [http://localhost:8000/api/health](http://localhost:8000/api/health).

#### 3. Run Frontend UI
1. Open a second terminal window and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite dev server:
   ```bash
   npm run dev
   ```
3. Open [http://localhost:5173](http://localhost:5173) and start talking to your database!
