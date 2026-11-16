from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def make_engine() -> Engine:
    url = os.getenv("DATABASE_URL")
    if not url:
        user = os.getenv("DB_USER", "department_user")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "department_events")
        if not password:
            raise RuntimeError("Не задан DB_PASSWORD в .env")
        from sqlalchemy.engine import URL

        url = URL.create(
            "postgresql+psycopg", username=user, password=password,
            host=host, port=int(port), database=name,
        )
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
