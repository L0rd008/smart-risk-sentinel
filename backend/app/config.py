"""Configuration loaded from .env.

Owned by Member 3. The .env file is git-ignored — each developer keeps
their own DB credentials locally.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Flask configuration sourced from environment variables."""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-not-for-production")

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "smart_risk_sentinel")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    DEBUG: bool = FLASK_ENV == "development"

    @classmethod
    def db_dsn(cls) -> str:
        """Return a libpq-style DSN string for psycopg2."""
        return (
            f"host={cls.DB_HOST} port={cls.DB_PORT} "
            f"dbname={cls.DB_NAME} user={cls.DB_USER} "
            f"password={cls.DB_PASSWORD}"
        )
