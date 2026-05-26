from __future__ import annotations

import os

# Safeguard: Redirect all database connections to a dedicated test file during pytest runs.
# This prevents backend tests from wiping the development database (paper_trading.db).
os.environ["DATABASE_URL"] = "sqlite:///./paper_trading_test.db"
