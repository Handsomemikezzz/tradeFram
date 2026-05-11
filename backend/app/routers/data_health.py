from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.data_health import get_data_health_overview
from ..utils import ok

router = APIRouter()


@router.get("/data-health/overview")
def read_data_health_overview(db: Session = Depends(get_db)):
    return ok(get_data_health_overview(db))
