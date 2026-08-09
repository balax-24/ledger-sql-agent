import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    gemini_api_key: str = os.environ["GEMINI_API_KEY"]
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    database_url: str = os.environ["DATABASE_URL"]
    frontend_origin: str = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    query_row_limit: int = 500
    query_timeout_seconds: float = 5.0
    max_tool_iterations: int = 6  # hard stop so a confused model can't loop forever


settings = Settings()
