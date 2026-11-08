import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://agent_readonly:ledger_readonly_dev@localhost:5433/postgres",
    )
    frontend_origin: str = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    query_row_limit: int = int(os.environ.get("QUERY_ROW_LIMIT", "100"))
    query_timeout_seconds: float = float(os.environ.get("QUERY_TIMEOUT_SECONDS", "5.0"))
    max_tool_iterations: int = int(os.environ.get("MAX_TOOL_ITERATIONS", "6"))

    # Statistical anomaly detection parameters
    anomaly_z_score_threshold: float = float(os.environ.get("ANOMALY_Z_SCORE_THRESHOLD", "2.0"))
    anomaly_percent_change_threshold: float = float(os.environ.get("ANOMALY_PERCENT_CHANGE_THRESHOLD", "0.20"))


settings = Settings()
