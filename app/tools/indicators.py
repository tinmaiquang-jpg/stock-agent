"""Chi bao ky thuat tinh tu OHLCV - thuan pandas, khong goi mang.

Tach rieng khoi stock_data.py de test duoc doc lap: dua vao DataFrame co san cot
open/high/low/close/volume, tra ve so lieu. Moi ham deu chiu duoc du lieu ngan
(tra None thay vi nem loi) vi ma moi niem yet co the chua du lich su.
"""

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

# Cac muc Fibonacci retracement chuan
FIB_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
# HOSE dong cua luc 15:00; cong them dem de du lieu nha cung cap kip cap nhat
MARKET_CLOSE = time(15, 15)


def drop_unfinished_session(df: pd.DataFrame) -> pd.DataFrame:
    """Bo phien cuoi neu do la phien hom nay va thi truong chua dong cua.

    Quan trong voi screener: giua phien, khoi luong moi tich luy mot phan (vd 347K so voi
    trung binh 6.7M), lam volume_ratio tut xuong ~0.05 va giet moi tin hieu breakout.
    Tin hieu swing phai tinh tren cac phien DA hoan tat.
    """
    if df is None or df.empty:
        return df

    now = datetime.now(VN_TZ)
    if now.time() >= MARKET_CLOSE:
        return df

    last_date = str(df.sort_values("time")["time"].iloc[-1])[:10]
    if last_date == now.strftime("%Y-%m-%d"):
        return df.sort_values("time").iloc[:-1]
    return df


def _last(series: pd.Series) -> float | None:
    if series is None or series.empty:
        return None
    value = series.iloc[-1]
    return None if pd.isna(value) else round(float(value), 4)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI theo Wilder: dung smoothing luy thua (alpha = 1/period), khong phai MA don gian."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    signal_line = line.ewm(span=signal, adjust=False).mean()
    return line, signal_line, line - signal_line


def bollinger(close: pd.Series, period: int = 20, std: float = 2.0):
    middle = close.rolling(period).mean()
    deviation = close.rolling(period).std()
    return middle + std * deviation, middle, middle - std * deviation


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range - do bien dong, dung de dat cat lo theo bien dong thuc te
    cua tung ma thay vi mot ty le % co dinh."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift()
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def find_swing(df: pd.DataFrame, lookback: int = 60) -> dict[str, Any] | None:
    """Tim nhip tang gan nhat (day -> dinh) de lam goc tinh Fibonacci.

    Cach lam: trong `lookback` phien gan nhat, lay dinh cao nhat, roi tim day thap nhat
    NAM TRUOC dinh do. Nho vay ta duoc mot nhip tang that su, khong phai ghep bua day va
    dinh o hai thoi diem khong lien quan.
    """
    if len(df) < 20:
        return None

    window = df.tail(lookback).reset_index(drop=True)
    high_pos = int(window["high"].idxmax())
    if high_pos == 0:
        return None  # dinh nam ngay dau cua so, khong co nhip tang de do

    before_high = window.iloc[: high_pos + 1]
    low_pos = int(before_high["low"].idxmin())
    swing_high = float(window.loc[high_pos, "high"])
    swing_low = float(window.loc[low_pos, "low"])
    if swing_high <= swing_low:
        return None

    return {
        "swing_low": round(swing_low, 2),
        "swing_high": round(swing_high, 2),
        "bars_since_high": int(len(window) - 1 - high_pos),
        "range": round(swing_high - swing_low, 2),
    }


def fibonacci_levels(df: pd.DataFrame, lookback: int = 60) -> dict[str, Any] | None:
    """Cac muc Fibonacci retracement cua nhip tang gan nhat + vi tri gia hien tai.

    `retracement_pct` = gia da thoai lui bao nhieu % cua nhip tang. 0% la dang o dinh,
    100% la ve lai day. Vung 38.2-61.8% thuong duoc coi la vung mua gom trong xu huong tang.
    """
    swing = find_swing(df, lookback)
    if not swing:
        return None

    low, high, span = swing["swing_low"], swing["swing_high"], swing["range"]
    price = float(df["close"].iloc[-1])

    levels = {f"fib_{level:.3f}": round(high - span * level, 2) for level in FIB_LEVELS}
    retracement = (high - price) / span * 100

    # Muc Fibonacci gan gia hien tai nhat
    nearest = min(levels.items(), key=lambda kv: abs(kv[1] - price))

    return {
        **swing,
        "levels": levels,
        "price": round(price, 2),
        "retracement_pct": round(retracement, 1),
        "nearest_level": nearest[0],
        "nearest_level_price": nearest[1],
        "distance_to_nearest_pct": round(abs(price - nearest[1]) / price * 100, 2),
        # Muc mo rong, dung lam muc tieu chot loi khi gia vuot dinh cu
        "extension_1.272": round(high + span * 0.272, 2),
        "extension_1.618": round(high + span * 0.618, 2),
    }


def snapshot(df: pd.DataFrame) -> dict[str, Any]:
    """Toan bo chi bao tai phien gan nhat, dang phang de dua thang cho LLM doc."""
    if df is None or df.empty or len(df) < 2:
        return {"error": "Khong du du lieu de tinh chi bao"}

    df = df.sort_values("time").reset_index(drop=True)
    close, volume = df["close"], df["volume"]

    macd_line, macd_signal, macd_hist = macd(close)
    upper, middle, lower = bollinger(close)
    price = float(close.iloc[-1])
    atr_value = _last(atr(df))

    ma = {f"ma{p}": _last(close.rolling(p).mean()) for p in (20, 50, 100, 200) if len(df) >= p}
    avg_volume_20 = _last(volume.rolling(20).mean())

    # MACD cat len trong 3 phien gan nhat: tin hieu vao lenh cua chien luoc giao cat
    cross_up = False
    if len(macd_hist.dropna()) >= 4:
        recent = macd_hist.tail(4).tolist()
        cross_up = recent[-1] > 0 and any(v <= 0 for v in recent[:-1])

    high_52w = _last(df["high"].rolling(min(250, len(df))).max())
    low_52w = _last(df["low"].rolling(min(250, len(df))).min())

    return {
        "price": round(price, 2),
        "rsi14": _last(rsi(close)),
        "macd": _last(macd_line),
        "macd_signal": _last(macd_signal),
        "macd_hist": _last(macd_hist),
        "macd_cross_up": cross_up,
        **ma,
        "bb_upper": _last(upper),
        "bb_middle": _last(middle),
        "bb_lower": _last(lower),
        "atr14": atr_value,
        "atr_pct": round(atr_value / price * 100, 2) if atr_value else None,
        "volume": int(volume.iloc[-1]),
        "avg_volume_20": int(avg_volume_20) if avg_volume_20 else None,
        "volume_ratio": round(volume.iloc[-1] / avg_volume_20, 2) if avg_volume_20 else None,
        "high_20": _last(df["high"].rolling(20).max()),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_52w_high": round((price - high_52w) / high_52w * 100, 1) if high_52w else None,
        "pct_above_52w_low": round((price - low_52w) / low_52w * 100, 1) if low_52w else None,
        "fibonacci": fibonacci_levels(df),
    }
