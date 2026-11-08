# Ledger — Request Flow

How a question travels from the UI to PostgreSQL and back. See the [README](README.md#4-system-architecture--data-flows) for the full architecture.

```text
                 React 18
              /            \
         Recharts         Mermaid
               │
            SSE stream
               │
               ▼
            FastAPI
               │
         Gemini 3.1
          Flash-Lite
               │
           Tool Loop
        /       |       \
get_schema execute_query generate_chart
                   \
                explain_data
               │
          SQLGlot validation
               │
               ▼
           PostgreSQL
```
