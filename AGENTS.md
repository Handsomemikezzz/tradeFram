# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

A-share paper trading & research system: React/Vite/TS frontend + FastAPI/SQLAlchemy/SQLite backend.
No Docker, no external DB server, no real broker — local-only SQLite file (`paper_trading.db`).

### Running services

| Service | Command | Port |
|---------|---------|------|
| Backend | `source .venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000` | 8000 |
| Frontend | `npm run dev` | 3000 |

Or use `npm run start:dev` which starts both (runs `scripts/start-dev.sh`).

### Key commands

- **Lint**: `npm run lint` (runs `tsc --noEmit`)
- **Tests**: `source .venv/bin/activate && pytest -q` (109 tests, local fixtures, no network needed)
- **Build**: `npm run build`
- **Health check**: `curl http://127.0.0.1:8000/health`

### Non-obvious caveats

1. **python3-venv package**: The VM may not have `python3.12-venv` pre-installed. Run `sudo apt-get update && sudo apt-get install -y python3-venv` before creating the venv if `python3 -m venv .venv` fails.
2. **AkShare network calls**: Stock data refresh (`/api/v1/data/stocks/{code}/refresh`) calls Chinese financial APIs (Eastmoney/Sina) which can be slow or timeout from non-China networks. Tests use local fixtures and do not require network.
3. **Environment file**: `.env` is auto-created from `.env.example` by `start-dev.sh`. If running services manually, copy it yourself: `cp .env.example .env`.
4. **SQLite database**: Auto-created on first backend startup at `./paper_trading.db`. Tests use a separate `paper_trading_test.db`.
5. **One pre-existing test failure**: `test_strict_trading_time_blocks_and_demo_mode_allows` in `tests/test_v01_rc_stability.py` may fail — this is a known issue in the codebase, not an environment problem.
