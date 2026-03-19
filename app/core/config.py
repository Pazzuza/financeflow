import os
import secrets
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.APP_NAME: str = os.getenv("APP_NAME", "FinanceFlow")
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))
        )

        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./financeflow.db")
        # For PostgreSQL: "postgresql://user:pass@localhost/financeflow"

        # Cookie settings
        self.COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self.COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax").lower()
        self.COOKIE_PATH: str = os.getenv("COOKIE_PATH", "/")

        # Auto-create DB tables on startup (idempotent).
        self.DB_AUTO_CREATE: bool = os.getenv("DB_AUTO_CREATE", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        # SECRET_KEY: if missing, generate one at startup.
        # In stateless deployments (Render/Railway), writing to disk is unreliable.
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "").strip() or secrets.token_hex(32)


settings = Settings()
