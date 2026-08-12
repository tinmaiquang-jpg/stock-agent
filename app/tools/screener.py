"""Quet va xep hang co phieu theo cac setup swing trade (giu vai ngay den vai tuan).

Day la cong cu LOC TIN HIEU KY THUAT, khong phai khuyen nghi dau tu: no tra ve nhung ma
dang thoa man dieu kien cua tung setup, kem muc gia vao/cat lo/chot lai tinh theo bien dong
thuc te (ATR). Quyet dinh cuoi cung van la cua nguoi dung.

Moi setup deu kem `reasons` liet ke dieu kien nao da thoa man, de nguoi doc kiem chung duoc
thay vi tin vao mot con diem khong giai thich.
"""

import logging
from typing import Any

import pandas as pd

from app.tools import history_cache, indicators, stock_data

logger = logging.getLogger(__name__)

# So phien lich su can de tinh MA200 va Fibonacci on dinh
HISTORY_DAYS = 400

STRATEGIES = ("fib_pullback", "breakout", "macd_cross", "oversold_bounce")


def _risk_levels(snap: dict[str, Any], entry: float, setup: str) -> dict[str, Any]:
    """Cat lo theo ATR, chot lai theo khang cu that.

    Cat lo dung ATR vi moi ma co bien dong rieng: '% co dinh' se qua chat voi ma bien dong
    manh va qua rong voi ma it bien dong.

    Muc tieu KHONG dung boi so ATR co dinh - lam vay thi R:R luon ra cung mot so va mat het
    y nghia. Thay vao do lay khang cu that: dinh cu voi setup thoai lui, muc mo rong
    Fibonacci voi setup pha vo. Nho vay R:R phan anh dung tung co hoi.
    """
    atr_value = snap.get("atr14")
    if not atr_value:
        return {}

    fib = snap.get("fibonacci") or {}
    stop = entry - 2 * atr_value

    if setup in ("fib_pullback", "oversold_bounce") and fib.get("swing_high"):
        target = float(fib["swing_high"])  # ky vong quay lai kiem tra dinh cu
        target_note = "dinh cu cua nhip tang"
    elif setup == "breakout" and fib.get("extension_1.272"):
        target = float(fib["extension_1.272"])
        target_note = "muc mo rong Fibonacci 1.272"
    else:
        target = entry + 3 * atr_value
        target_note = "3x ATR (khong tim duoc khang cu ro rang)"

    # Khang cu da bi vuot qua thi khong con la muc tieu - lui ve boi so ATR
    if target <= entry * 1.01:
        target = entry + 3 * atr_value
        target_note = "3x ATR (khang cu gan nhat da bi vuot)"

    risk = entry - stop
    return {
        "entry": round(entry, 2),
        "stop_loss": round(stop, 2),
        "stop_loss_pct": round((stop - entry) / entry * 100, 1),
        "target": round(target, 2),
        "target_pct": round((target - entry) / entry * 100, 1),
        "target_basis": target_note,
        "risk_reward": round((target - entry) / risk, 2) if risk > 0 else None,
    }


def _check_fib_pullback(snap: dict[str, Any]) -> tuple[int, list[str]] | None:
    """Xu huong tang + gia thoai lui ve vung Fibonacci 38.2-61.8% = vung gom hang kinh dien."""
    fib = snap.get("fibonacci")
    price, ma20, ma50 = snap.get("price"), snap.get("ma20"), snap.get("ma50")
    rsi_value = snap.get("rsi14")
    if not fib or None in (price, ma50, rsi_value):
        return None

    retracement = fib["retracement_pct"]
    reasons, score = [], 0

    # Cham diem theo do sau thoai lui. Vung 38.2-61.8% moi la vung gom hang kinh dien;
    # nong hon thi chua chac da chinh xong, sau hon thi xu huong tang dang bi de doa.
    if 38.2 <= retracement <= 61.8:
        reasons.append(f"thoai lui {retracement}% - trong vung vang Fibonacci 38.2-61.8%")
        score += 35
    elif 30 <= retracement < 38.2:
        reasons.append(f"thoai lui {retracement}% - con nong, chua toi vung vang 38.2%")
        score += 20
    elif 61.8 < retracement <= 70:
        reasons.append(f"thoai lui {retracement}% - kha sau, gan nguong 70% de gay xu huong")
        score += 22
    else:
        return None

    if price > ma50:
        reasons.append("gia van tren MA50 - xu huong tang chua gay")
        score += 25
    else:
        return None

    if ma20 and ma20 > ma50:
        reasons.append("MA20 tren MA50")
        score += 15

    if 40 <= rsi_value <= 60:
        reasons.append(f"RSI {rsi_value:.0f} - vung trung tinh, con du dia tang")
        score += 15
    elif rsi_value < 40:
        reasons.append(f"RSI {rsi_value:.0f} - hoi yeu")
        score += 5

    if fib["distance_to_nearest_pct"] < 2:
        reasons.append(f"sat muc {fib['nearest_level']} = {fib['nearest_level_price']}")
        score += 10

    return score, reasons


def _check_breakout(snap: dict[str, Any]) -> tuple[int, list[str]] | None:
    """Vuot dinh 20 phien kem khoi luong - khong co khoi luong thi de la breakout gia."""
    price, high20 = snap.get("price"), snap.get("high_20")
    volume_ratio, rsi_value = snap.get("volume_ratio"), snap.get("rsi14")
    if None in (price, high20, volume_ratio, rsi_value):
        return None

    if price < high20 * 0.99:
        return None

    reasons, score = [f"gia {price} sat/vuot dinh 20 phien ({high20})"], 35

    if volume_ratio >= 1.5:
        reasons.append(f"khoi luong gap {volume_ratio}x trung binh 20 phien")
        score += 30
    elif volume_ratio >= 1.0:
        reasons.append(f"khoi luong {volume_ratio}x trung binh")
        score += 10
    else:
        return None  # breakout khong khoi luong -> bo qua

    if rsi_value > 75:
        reasons.append(f"RSI {rsi_value:.0f} - da qua mua, rui ro dieu chinh")
        score -= 15
    else:
        score += 15

    ma50 = snap.get("ma50")
    if ma50 and price > ma50:
        reasons.append("tren MA50")
        score += 10

    return score, reasons


def _check_macd_cross(snap: dict[str, Any]) -> tuple[int, list[str]] | None:
    """MACD cat len duong tin hieu trong 3 phien gan nhat, trong boi canh xu huong tang."""
    if not snap.get("macd_cross_up"):
        return None

    price, ma50, rsi_value = snap.get("price"), snap.get("ma50"), snap.get("rsi14")
    if None in (price, rsi_value):
        return None

    reasons = ["MACD vua cat len duong tin hieu (trong 3 phien)"]
    score = 40

    if ma50 and price > ma50:
        reasons.append("gia tren MA50 - cat len thuan xu huong")
        score += 25
    else:
        reasons.append("gia duoi MA50 - tin hieu yeu hon, co the chi la hoi phuc ky thuat")
        score -= 10

    if 45 <= rsi_value <= 70:
        reasons.append(f"RSI {rsi_value:.0f} thuan loi")
        score += 20

    volume_ratio = snap.get("volume_ratio")
    if volume_ratio and volume_ratio > 1.2:
        reasons.append(f"khoi luong tang {volume_ratio}x")
        score += 15

    return score, reasons


def _check_oversold_bounce(snap: dict[str, Any]) -> tuple[int, list[str]] | None:
    """Qua ban sau nhip giam - danh hoi phuc ngan, rui ro cao hon 3 setup con lai."""
    rsi_value, price, bb_lower = snap.get("rsi14"), snap.get("price"), snap.get("bb_lower")
    if None in (rsi_value, price, bb_lower):
        return None

    if rsi_value > 35:
        return None

    reasons = [f"RSI {rsi_value:.0f} - vung qua ban"]
    score = 30

    if price <= bb_lower * 1.02:
        reasons.append(f"gia cham dai Bollinger duoi ({bb_lower})")
        score += 25

    ma200 = snap.get("ma200")
    if ma200 and price > ma200:
        reasons.append("van tren MA200 - xu huong dai han con nguyen")
        score += 25
    else:
        reasons.append("duoi MA200 - bat day nguoc xu huong dai han, rui ro cao")
        score -= 10

    return score, reasons


_CHECKERS = {
    "fib_pullback": _check_fib_pullback,
    "breakout": _check_breakout,
    "macd_cross": _check_macd_cross,
    "oversold_bounce": _check_oversold_bounce,
}


def analyze_symbol(symbol: str) -> dict[str, Any]:
    """Toan bo chi bao + setup dang khop cho mot ma."""
    return _analyze(symbol.upper(), history_cache.get_history(symbol, days=HISTORY_DAYS))


def _analyze(symbol: str, raw: list[dict[str, Any]]) -> dict[str, Any]:
    if not raw:
        return {"symbol": symbol, "error": "Khong co du lieu lich su"}

    df = indicators.drop_unfinished_session(pd.DataFrame(raw))
    snap = indicators.snapshot(df)
    if "error" in snap:
        return {"symbol": symbol, **snap}

    setups = []
    for name, checker in _CHECKERS.items():
        result = checker(snap)
        if not result:
            continue
        score, reasons = result
        risk = _risk_levels(snap, snap["price"], name)

        # Setup dep ve ky thuat nhung rui ro lon hon loi nhuan ky vong thi khong phai co hoi
        # tot. Khong tinh yeu to nay thi bang xep hang se day len dau nhung ma R:R < 1.
        rr = risk.get("risk_reward")
        if rr is not None:
            if rr >= 2:
                reasons.append(f"R:R {rr} - lai ky vong gap doi rui ro")
                score += 15
            elif rr >= 1.5:
                reasons.append(f"R:R {rr} - chap nhan duoc")
                score += 10
            elif rr < 1:
                reasons.append(f"R:R {rr} - CANH BAO: rui ro lon hon loi nhuan toi muc tieu dau")
                score -= 20

        setups.append(
            {
                "setup": name,
                "score": max(0, min(100, score)),
                "reasons": reasons,
                **risk,
            }
        )

    setups.sort(key=lambda s: s["score"], reverse=True)
    return {"symbol": symbol, "indicators": snap, "setups": setups}


def screen(
    group: str = "VN30",
    strategy: str = "all",
    top_n: int = 10,
    min_score: int = 50,
) -> dict[str, Any]:
    """Quet ca nhom, tra ve cac ma co setup dat diem tu `min_score` tro len.

    strategy: 'all' hoac mot trong fib_pullback / breakout / macd_cross / oversold_bounce.
    """
    if strategy != "all" and strategy not in STRATEGIES:
        return {"error": f"strategy phai la 'all' hoac mot trong {list(STRATEGIES)}"}

    symbols = stock_data.get_group_symbols(group)
    histories = history_cache.get_history_many(symbols, days=HISTORY_DAYS)

    analyses = []
    for symbol in symbols:
        try:
            analysis = _analyze(symbol, histories.get(symbol, []))
        except Exception as exc:
            logger.warning("Bo qua %s khi quet: %s", symbol, exc)
            continue
        if "error" not in analysis:
            analyses.append(analysis)

    matches = []
    for analysis in analyses:
        for setup in analysis["setups"]:
            if strategy != "all" and setup["setup"] != strategy:
                continue
            if setup["score"] < min_score:
                continue
            snap = analysis["indicators"]
            matches.append(
                {
                    "symbol": analysis["symbol"],
                    "price": snap["price"],
                    "rsi14": snap["rsi14"],
                    "volume_ratio": snap.get("volume_ratio"),
                    **setup,
                }
            )

    matches.sort(key=lambda m: m["score"], reverse=True)
    return {
        "group": group.upper(),
        "strategy": strategy,
        "scanned": len(symbols),
        "analyzed": len(analyses),
        "matched": len(matches),
        "results": matches[:top_n],
        "note": (
            "Tin hieu ky thuat tu du lieu gia, KHONG phai khuyen nghi mua ban. "
            "Gia tinh tren phien da dong cua gan nhat."
        ),
    }
