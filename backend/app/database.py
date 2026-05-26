from __future__ import annotations

import os
import sys
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./paper_trading.db")

# Nuclear Fail-Safe: Automatically intercept any test executions (pytest or manual python tests/* scripts)
# and redirect SQLite connections to paper_trading_test.db to prevent accidental table drops.
is_test_run = "pytest" in sys.modules or any("test" in arg for arg in sys.argv)
if is_test_run and "paper_trading.db" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("paper_trading.db", "paper_trading_test.db")
    print(f"\n[SAFEGUARD] Test environment detected! Safely redirected database to: {DATABASE_URL}\n")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
