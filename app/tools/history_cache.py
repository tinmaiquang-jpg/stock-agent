"""Cache lich su gia trong Supabase + tiet luu toc do goi vnstock.

Ly do can: vnstock tier Guest chi cho 20 request/phut, ma quet VN30 can 30 request nen
lan quet dau tien da bi chan. Du lieu OHLCV theo ngay khong doi trong phien, nen cache
1 lan/ngay/ma vua giai quyet gioi han vua lam lan quet sau gan nhu tuc thoi.

Muon bo gioi han nay: dang ky API key mien phi tai https://vnstocks.com/login (60 req/phut).
"""

import logging
import threading
import time
from datetime import date
from typing import Any

from app.db.client import get_supabase
from app.tools import stock_data

logger = logging.getLogger(__name__)

# Dat duoi 20/phut cua tier Guest de con cho cac request khac (gia hien tai, bang gia...)
MAX_REQUESTS_PER_MINUTE = 16
_WINDOW_SECONDS = 60


class _RateLimiter:
    """Cua so truot don gian: chan truoc khi vuot han muc thay vi de vnstock tra loi loi."""

    def __init__(self, max_calls: int, window: float) -> None:
        self._max_calls = max_calls
        self._window = window
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._calls = [t for t in self._calls if now - t < self._window]
                if len(self._calls) < self._max_calls:
                    self._calls.append(now)
                    return
                wait = self._window - (now - self._calls[0]) + 0.1
            logger.info("Cham gioi han vnstock, cho %.1fs", wait)
            time.sleep(wait)


_limiter = _RateLimiter(MAX_REQUESTS_PER_MINUTE, _WINDOW_SECONDS)


def _read_cache(symbols: list[str], today: date) -> dict[str, list[dict[str, Any]]]:
    try:
        rows = (
            get_supabase()
            .table("ohlcv_cache")
            .select("symbol, data")
            .in_("symbol", symbols)
            .eq("fetched_date", today.isoformat())
            .execute()
            .data
        )
    except Exception as exc:
        logger.warning("Khong doc duoc cache gia: %s", exc)
        return {}
    return {row["symbol"]: row["data"] for row in rows}


def _write_cache(symbol: str, data: list[dict[str, Any]], today: date) -> None:
    try:
        get_supabase().table("ohlcv_cache").upsert(
            {"symbol": symbol, "data": data, "fetched_date": today.isoformat()},
            on_conflict="symbol",
        ).execute()
    except Exception as exc:
        logger.warning("Khong ghi duoc cache gia cho %s: %s", symbol, exc)


def get_history(symbol: str, days: int) -> list[dict[str, Any]]:
    """Lich su gia 1 ma, uu tien cache trong ngay."""
    return get_history_many([symbol], days)[symbol.upper()]


def get_history_many(symbols: list[str], days: int) -> dict[str, list[dict[str, Any]]]:
    """Lich su gia nhieu ma. Doc cache mot lan cho ca danh sach, chi goi API cho phan thieu.

    Goi tuan tu (khong song song) vi da bi gioi han theo phut - chay song song chi lam
    cham hon do phai cho o rate limiter.
    """
    symbols = [s.upper() for s in symbols]
    today = date.today()
    cached = _read_cache(symbols, today)

    missing = [s for s in symbols if s not in cached]
    if missing:
        logger.info("Cache co %d/%d ma, tai them %d ma", len(cached), len(symbols), len(missing))

    result = dict(cached)
    for symbol in missing:
        _limiter.acquire()
        try:
            data = stock_data.get_history(symbol, days=days)
        except stock_data.StockDataError as exc:
            logger.warning("Khong tai duoc %s: %s", symbol, exc)
            result[symbol] = []
            continue
        result[symbol] = data
        if data:
            _write_cache(symbol, data, today)

    return result
