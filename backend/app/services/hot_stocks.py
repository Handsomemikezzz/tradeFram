from __future__ import annotations

import logging
import re
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

import requests
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models as m
from ..data_layer.providers.akshare import _configure_akshare_proxy_bypass
from ..utils import CN_TZ, new_id
from .indicators import moving_average_snapshot_for_code

logger = logging.getLogger(__name__)

PRIMARY_HOT_RANK_SOURCE = "EastmoneyHotRank"
FALLBACK_HOT_RANK_SOURCE = "BaiduHotSearch"
HOT_RANK_SOURCES = (PRIMARY_HOT_RANK_SOURCE, FALLBACK_HOT_RANK_SOURCE)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://guba.eastmoney.com/",
}


class HotStockError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def _today() -> date:
    return datetime.now(CN_TZ).date()


def _direct_requests_session() -> requests.Session:
    _configure_akshare_proxy_bypass()
    session = requests.Session()
    session.trust_env = False
    session.headers.update(_BROWSER_HEADERS)
    return session


def _normalize_code(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    if text.startswith(("SH", "SZ", "BJ")):
        text = text[2:]
    digits = re.sub(r"\D", "", text)
    return digits.zfill(6) if digits else text.zfill(6)


def _parse_tencent_quote_line(line: str) -> dict[str, Any] | None:
    if "=" not in line:
        return None
    _, payload = line.split("=", 1)
    payload = payload.strip().strip('";\n')
    parts = payload.split("~")
    if len(parts) < 5:
        return None
    code = _normalize_code(parts[2])
    try:
        price = float(parts[3]) if parts[3] else None
        prev_close = float(parts[4]) if parts[4] else None
    except ValueError:
        return None
    change_percent = None
    if price is not None and prev_close not in {None, 0}:
        change_percent = round((price - prev_close) / prev_close * 100, 2)
    return {
        "code": code,
        "name": parts[1],
        "price": price,
        "change_percent": change_percent,
    }


def _fetch_tencent_quotes(session: requests.Session, codes: list[str]) -> dict[str, dict[str, Any]]:
    quotes: dict[str, dict[str, Any]] = {}
    if not codes:
        return quotes

    for start in range(0, len(codes), 40):
        chunk = codes[start : start + 40]
        symbols = []
        for code in chunk:
            prefix = "sh" if code.startswith("6") else "sz"
            symbols.append(f"{prefix}{code}")
        response = session.get(f"https://qt.gtimg.cn/q={','.join(symbols)}", timeout=15)
        response.raise_for_status()
        for line in response.text.splitlines():
            parsed = _parse_tencent_quote_line(line)
            if parsed:
                quotes[parsed["code"]] = parsed
    return quotes


def _fetch_eastmoney_hot_rank_emappdata(limit: int) -> list[dict[str, Any]]:
    """Eastmoney rank list + Tencent quotes. Avoids unstable push2.eastmoney.com."""
    session = _direct_requests_session()
    payload = {
        "appId": "appId01",
        "globalId": "786e4c21-70dc-435a-93bb-38",
        "marketType": "",
        "pageNo": 1,
        "pageSize": max(limit, 30),
    }
    response = session.post(
        "https://emappdata.eastmoney.com/stockrank/getAllCurrentList",
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    rank_rows = response.json().get("data") or []
    if not rank_rows:
        raise RuntimeError("eastmoney rank list empty")

    selected = rank_rows[:limit]
    codes = [_normalize_code(item.get("sc", "")) for item in selected]
    quotes = _fetch_tencent_quotes(session, codes)

    rows: list[dict[str, Any]] = []
    for item in selected:
        code = _normalize_code(item.get("sc", ""))
        quote = quotes.get(code, {})
        rows.append(
            {
                "当前排名": int(item.get("rk", 0) or 0),
                "代码": code,
                "股票名称": quote.get("name") or code,
                "最新价": quote.get("price"),
                "涨跌幅": quote.get("change_percent"),
            }
        )
    return rows


def _fetch_eastmoney_hot_rank_akshare(limit: int) -> list[dict[str, Any]]:
    _configure_akshare_proxy_bypass()
    import akshare as ak  # type: ignore

    frame = ak.stock_hot_rank_em()
    rows = frame.head(limit).to_dict(orient="records")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "当前排名": row.get("当前排名"),
                "代码": _normalize_code(row.get("代码")),
                "股票名称": row.get("股票名称"),
                "最新价": row.get("最新价"),
                "涨跌幅": row.get("涨跌幅"),
            }
        )
    return normalized


def _parse_baidu_change_percent(raw: Any) -> float | None:
    text = str(raw or "").strip().replace("％", "%")
    if not text or text in {"--", "-"}:
        return None
    try:
        return float(text.replace("%", "").replace("+", ""))
    except ValueError:
        return None


def _fetch_baidu_hot_search(limit: int) -> list[dict[str, Any]]:
    _configure_akshare_proxy_bypass()
    import akshare as ak  # type: ignore

    frame = ak.stock_hot_search_baidu(
        symbol="A股",
        date=datetime.now(CN_TZ).strftime("%Y%m%d"),
        time="今日",
    )
    if frame is None or frame.empty:
        raise RuntimeError("baidu hot search empty")

    from ..data_layer.warehouse.reader import WarehouseMarketDataStore

    warehouse = WarehouseMarketDataStore()
    name_to_code = {inst.name: inst.code for inst in warehouse.list_instruments() if inst.name}

    rows: list[dict[str, Any]] = []
    for index, row in frame.head(min(limit, len(frame))).iterrows():
        name = str(row.get("名称/代码", "")).strip()
        code = name_to_code.get(name)
        if not code:
            continue
        rows.append(
            {
                "当前排名": len(rows) + 1,
                "代码": _normalize_code(code),
                "股票名称": name,
                "最新价": None,
                "涨跌幅": _parse_baidu_change_percent(row.get("涨跌幅")),
            }
        )
    if not rows:
        raise RuntimeError("baidu hot search could not resolve stock codes")
    return rows[:limit]


def _fetch_hot_rank(limit: int) -> tuple[list[dict[str, Any]], str]:
    """Try multiple providers; return normalized rows and snapshot source label."""
    providers: list[tuple[str, Any]] = [
        (PRIMARY_HOT_RANK_SOURCE, _fetch_eastmoney_hot_rank_emappdata),
        (PRIMARY_HOT_RANK_SOURCE, _fetch_eastmoney_hot_rank_akshare),
        (FALLBACK_HOT_RANK_SOURCE, _fetch_baidu_hot_search),
    ]
    errors: list[str] = []
    for source, fetcher in providers:
        for attempt in range(2):
            try:
                rows = fetcher(limit)
                if rows:
                    logger.info("Hot rank fetched via %s (%s)", fetcher.__name__, source)
                    return rows, source
            except Exception as exc:
                message = f"{fetcher.__name__}: {exc}"
                errors.append(message)
                logger.warning("Hot rank provider failed (%s): %s", fetcher.__name__, exc)
                if attempt == 0:
                    time.sleep(1)
    raise RuntimeError("; ".join(errors[-3:]))


def _recent_limit_up_break_codes(db: Session, lookback_days: int = 5) -> set[str]:
    cutoff = _today() - timedelta(days=lookback_days)
    snapshots = (
        db.query(m.LimitUpBreakSnapshot)
        .filter(m.LimitUpBreakSnapshot.trade_date >= cutoff)
        .order_by(desc(m.LimitUpBreakSnapshot.trade_date), desc(m.LimitUpBreakSnapshot.updated_at))
        .all()
    )
    snapshot_ids = [s.id for s in snapshots]
    if not snapshot_ids:
        return set()
    items = (
        db.query(m.LimitUpBreakItem)
        .filter(m.LimitUpBreakItem.snapshot_id.in_(snapshot_ids))
        .all()
    )
    return {item.code for item in items}


def generate_hot_stock_snapshot(
    db: Session,
    *,
    limit: int = 20,
    force_refresh: bool = True,
    source: str = PRIMARY_HOT_RANK_SOURCE,
) -> m.HotStockSnapshot:
    today = _today()

    existing = (
        db.query(m.HotStockSnapshot)
        .filter(
            m.HotStockSnapshot.trade_date == today,
            m.HotStockSnapshot.source == source,
            m.HotStockSnapshot.status == "SUCCESS",
        )
        .first()
    )
    if existing and not force_refresh:
        return existing

    if force_refresh:
        today_snapshots = (
            db.query(m.HotStockSnapshot)
            .filter(
                m.HotStockSnapshot.trade_date == today,
                m.HotStockSnapshot.status == "SUCCESS",
            )
            .all()
        )
        for snapshot in today_snapshots:
            db.query(m.HotStockItem).filter(m.HotStockItem.snapshot_id == snapshot.id).delete()
            db.delete(snapshot)
        db.flush()

    rank_rows, fetch_source = _fetch_hot_rank(limit)

    from ..data_layer.warehouse.reader import WarehouseMarketDataStore

    warehouse = WarehouseMarketDataStore()
    instruments = warehouse.list_instruments()
    instrument_map = {inst.code: inst for inst in instruments}
    break_codes = _recent_limit_up_break_codes(db)

    snapshot = m.HotStockSnapshot(
        id=new_id("hs"),
        trade_date=today,
        source=fetch_source,
        status="SUCCESS",
    )
    db.add(snapshot)
    db.flush()

    for row in rank_rows:
        code = _normalize_code(row.get("代码"))
        inst = instrument_map.get(code)
        name = str(row.get("股票名称") or (inst.name if inst else code))
        industry = inst.industry if inst else None
        indicator = moving_average_snapshot_for_code(code, store=warehouse)

        item = m.HotStockItem(
            id=new_id("hsi"),
            snapshot_id=snapshot.id,
            rank=int(row.get("当前排名", 0) or 0),
            code=code,
            name=name,
            price=_safe_float(row.get("最新价")),
            change_percent=_safe_float(row.get("涨跌幅")),
            industry=industry,
            ma5=indicator.ma5,
            ma20=indicator.ma20,
            trend_label=indicator.trend_label,
            is_recent_limit_up_break=code in break_codes,
        )
        db.add(item)

    db.flush()
    return snapshot


def get_or_create_today_snapshot(
    db: Session,
    *,
    limit: int = 20,
    source: str = PRIMARY_HOT_RANK_SOURCE,
    force_refresh: bool = True,
) -> tuple[m.HotStockSnapshot | None, bool, str | None]:
    """Return (snapshot, is_fallback, error_message)."""
    if not force_refresh:
        today = _today()
        existing = (
            db.query(m.HotStockSnapshot)
            .filter(
                m.HotStockSnapshot.trade_date == today,
                m.HotStockSnapshot.status == "SUCCESS",
            )
            .order_by(desc(m.HotStockSnapshot.created_at))
            .first()
        )
        if existing:
            return existing, existing.source != source, None

    error_message: str | None = None
    try:
        snapshot = generate_hot_stock_snapshot(db, limit=limit, force_refresh=True, source=source)
        db.commit()
        return snapshot, snapshot.source != source, None
    except Exception as exc:
        db.rollback()
        error_message = str(exc)
        logger.warning("Failed to generate hot stock snapshot: %s", error_message)

    preferred = (
        db.query(m.HotStockSnapshot)
        .filter(
            m.HotStockSnapshot.source == source,
            m.HotStockSnapshot.status == "SUCCESS",
        )
        .order_by(desc(m.HotStockSnapshot.trade_date), desc(m.HotStockSnapshot.created_at))
        .first()
    )
    if preferred:
        return preferred, True, error_message

    fallback = (
        db.query(m.HotStockSnapshot)
        .filter(m.HotStockSnapshot.status == "SUCCESS")
        .order_by(desc(m.HotStockSnapshot.trade_date), desc(m.HotStockSnapshot.created_at))
        .first()
    )
    if fallback:
        return fallback, True, error_message
    return None, True, error_message


def get_latest_snapshot(
    db: Session,
    *,
    source: str = PRIMARY_HOT_RANK_SOURCE,
) -> m.HotStockSnapshot | None:
    """Return latest successful snapshot without triggering external fetch."""
    preferred = (
        db.query(m.HotStockSnapshot)
        .filter(
            m.HotStockSnapshot.source == source,
            m.HotStockSnapshot.status == "SUCCESS",
        )
        .order_by(desc(m.HotStockSnapshot.trade_date), desc(m.HotStockSnapshot.created_at))
        .first()
    )
    if preferred:
        return preferred
    return (
        db.query(m.HotStockSnapshot)
        .filter(m.HotStockSnapshot.status == "SUCCESS")
        .order_by(desc(m.HotStockSnapshot.trade_date), desc(m.HotStockSnapshot.created_at))
        .first()
    )


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
