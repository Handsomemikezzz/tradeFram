from __future__ import annotations

from contextlib import asynccontextmanager

import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import audit, data, data_health, hot_stocks, limit_up_breaks, monitoring, p0b, portfolio, research, reviews, screeners, system, trading
from .seed import init_db
from .utils import http_exception_handler, validation_exception_handler, ok


def backup_database() -> None:
    import sys
    import datetime
    
    # Safeguard: Skip backup during unit tests
    is_test_run = "pytest" in sys.modules or any("test" in arg for arg in sys.argv)
    if is_test_run:
        return
        
    db_file = "paper_trading.db"
    if not os.path.exists(db_file):
        return
        
    backup_dir = "data/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"paper_trading_backup_{timestamp}.db")
    
    try:
        shutil.copy2(db_file, backup_file)
        print(f"\n[BACKUP] Safely backed up active database to: {backup_file}\n")
        
        # Housekeeping: Keep only the latest 3 backups
        backups = sorted(
            [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("paper_trading_backup_") and f.endswith(".db")],
            key=os.path.getmtime
        )
        if len(backups) > 3:
            for old_backup in backups[:-3]:
                os.remove(old_backup)
                print(f"[BACKUP] Removed stale historical backup: {old_backup}")
    except Exception as e:
        print(f"[BACKUP] Database backup failed: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    backup_database()
    init_db()
    yield


app = FastAPI(title="定盘 · 心静交易 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Mount local uploads directory
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/api/v1/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/v1/reviews/upload")
def upload_image(file: UploadFile = File(...)):
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
        raise HTTPException(status_code=400, detail="Only images are allowed")
    
    # Generate unique filename
    filename = f"img_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save the file
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return ok({"url": f"/api/v1/uploads/{filename}"})


for router in [system.router, data.router, data_health.router, research.router, reviews.router, monitoring.router, hot_stocks.router, screeners.router, limit_up_breaks.router, trading.router, portfolio.router, audit.router, p0b.router]:
    app.include_router(router, prefix="/api/v1")

