"""Wrapper quanh thu vien vnstock (v4.x, dung `vnstock.api`) - nguon du lieu
chung khoan VN mien phi, khong can tai khoan broker. Neu ve sau tich hop broker
API thuc (SSI/DNSE), chi can them module tool tuong tu file nay, khong doi cach
agent goi tool."""

from datetime import date, timedelta
from functools import lru_cache
from typing import Any

import pandas as pd
from vnstock.api.company import Company
from vnstock.api.financial import Finance
from vnstock.api.listing import Listing
from vnstock.api.quote import Quote
from vnstock.api.trading import Trading

DEFAULT_SOURCE = "VCI"


class StockDataError(Exception):
    """Loi khi lay du lieu chung khoan (mang, rate limit, ma khong ton tai...)."""


@lru_cache(maxsize=128)
def _quote(symbol: str) -> Quote:
    return Quote(symbol=symbol.upper(), source=DEFAULT_SOURCE)


@lru_cache(maxsize=128)
def _company(symbol: str) -> Company:
    return Company(symbol=symbol.upper(), source=DEFAULT_SOURCE)


# Chi so tai chinh: nguon KBS tra ve dang gon (moi dong 1 chi tieu, moi cot 1 ky),
# trong khi VCI tra ve cot trung lap kho xu ly.
@lru_cache(maxsize=128)
def _finance(symbol: str, period: str) -> Finance:
    return Finance(symbol=symbol.upper(), source="KBS", period=period)


@lru_cache(maxsize=8)
def _trading() -> Trading:
    return Trading(source=DEFAULT_SOURCE)


# Danh sach nhom chi co nguon KBS tra ve duoc (VCI/MSN nem NotImplementedError)
@lru_cache(maxsize=2)
def _listing() -> Listing:
    return Listing(source="KBS")


def get_group_symbols(group: str = "VN30") -> list[str]:
    """Danh sach ma trong mot nhom: VN30, VN100, HNX30, HOSE, UPCOM, VNMidCap..."""
    try:
        symbols = _listing().symbols_by_group(group=group.upper())
    except Exception as exc:
        raise StockDataError(f"Khong lay duoc danh sach nhom {group}: {exc}") from exc
    return [str(s).upper() for s in symbols]


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = ["_".join(str(p) for p in col if p) for col in out.columns]
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].astype(str)
    return out.where(out.notna(), None).to_dict(orient="records")


def get_current_price(symbol: str) -> dict[str, Any]:
    """Gia dong phien gan nhat + bien dong so voi phien truoc. vnstock khong cung
    cap tick real-time, nen trong gio giao dich day la gia cap nhat gan nhat."""
    try:
        end = date.today()
        start = end - timedelta(days=14)
        df = _quote(symbol).history(start=start.isoformat(), end=end.isoformat(), interval="1D")
    except Exception as exc:  # thu vien ben ngoai raise nhieu loai loi khac nhau
        raise StockDataError(f"Khong lay duoc gia cho {symbol}: {exc}") from exc

    if df is None or df.empty:
        raise StockDataError(f"Khong co du lieu gia cho ma {symbol}")

    df = df.sort_values("time")
    last = df.iloc[-1]
    price = float(last["close"])
    prev_close = float(df.iloc[-2]["close"]) if len(df) > 1 else None
    change = round(price - prev_close, 2) if prev_close is not None else None
    pct_change = round(change / prev_close * 100, 2) if change is not None and prev_close else None

    return {
        "symbol": symbol.upper(),
        "date": str(last["time"])[:10],
        "close": price,
        "open": float(last["open"]),
        "high": float(last["high"]),
        "low": float(last["low"]),
        "volume": int(last["volume"]),
        "change": change,
        "pct_change": pct_change,
        "unit": "nghin VND/co phieu",
    }


def get_history(symbol: str, days: int = 90, interval: str = "1D") -> list[dict[str, Any]]:
    """OHLCV lich su cho `days` ngay gan nhat. interval: 1D, 1W, 1M."""
    try:
        end = date.today()
        start = end - timedelta(days=days)
        df = _quote(symbol).history(start=start.isoformat(), end=end.isoformat(), interval=interval)
    except Exception as exc:
        raise StockDataError(f"Khong lay duoc lich su gia cho {symbol}: {exc}") from exc

    return _df_to_records(df)


def get_company_overview(symbol: str) -> dict[str, Any]:
    """Tong quan doanh nghiep: von hoa, so luong co phieu, danh gia, nganh..."""
    try:
        df = _company(symbol).overview()
    except Exception as exc:
        raise StockDataError(f"Khong lay duoc thong tin cong ty cho {symbol}: {exc}") from exc

    records = _df_to_records(df)
    return records[0] if records else {}


def get_financial_ratios(symbol: str, period: str = "year", limit: int = 4) -> list[dict[str, Any]]:
    """Chi so tai chinh (EPS, BVPS, P/E, P/B, ROE...) cho `limit` ky gan nhat.
    period: 'year' hoac 'quarter'. Tra ve list moi phan tu la 1 ky."""
    if period not in ("year", "quarter"):
        raise StockDataError("period chi nhan 'year' hoac 'quarter'")
    try:
        df = _finance(symbol, period).ratio()
    except Exception as exc:
        raise StockDataError(f"Khong lay duoc chi so tai chinh cho {symbol}: {exc}") from exc

    if df is None or df.empty or "item_id" not in df.columns:
        return []

    period_cols = [c for c in df.columns if c not in ("item", "item_id", "item_en")][:limit]
    out: list[dict[str, Any]] = []
    for col in period_cols:
        entry: dict[str, Any] = {"period": str(col), "symbol": symbol.upper()}
        for _, row in df.iterrows():
            value = row[col]
            entry[str(row["item_id"])] = None if pd.isna(value) else value
        out.append(entry)
    return out


def get_price_board(symbols: list[str]) -> list[dict[str, Any]]:
    """Bang gia nhieu ma cung luc - re hon goi get_current_price nhieu lan."""
    if not symbols:
        return []
    tickers = [s.upper() for s in symbols]
    try:
        df = _trading().price_board(tickers)
    except Exception as exc:
        raise StockDataError(f"Khong lay duoc bang gia cho {tickers}: {exc}") from exc

    return _df_to_records(df)
