"""Kiem tra doc lap module lay du lieu chung khoan (khong can Supabase/Telegram).

Chay: python scripts/test_stock_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools import stock_data  # noqa: E402

TICKERS = ["VNM", "FPT", "VCB"]


def main() -> None:
    for ticker in TICKERS:
        print(f"\n=== {ticker} ===")
        try:
            print("Gia:", stock_data.get_current_price(ticker))
        except stock_data.StockDataError as exc:
            print("  LOI gia:", exc)

        try:
            hist = stock_data.get_history(ticker, days=10)
            print(f"Lich su: {len(hist)} phien, phien gan nhat:", hist[-1] if hist else None)
        except stock_data.StockDataError as exc:
            print("  LOI lich su:", exc)

    print("\n=== Thong tin cong ty FPT ===")
    try:
        overview = stock_data.get_company_overview("FPT")
        print({k: overview[k] for k in list(overview)[:8]})
    except stock_data.StockDataError as exc:
        print("  LOI:", exc)

    print("\n=== Chi so tai chinh FPT (nam) ===")
    try:
        ratios = stock_data.get_financial_ratios("FPT")
        print(f"{len(ratios)} ky, ky gan nhat co {len(ratios[0]) if ratios else 0} chi tieu")
        if ratios:
            print("  vi du:", {k: ratios[0][k] for k in list(ratios[0])[:6]})
    except stock_data.StockDataError as exc:
        print("  LOI:", exc)

    print("\n=== Bang gia nhieu ma ===")
    try:
        board = stock_data.get_price_board(TICKERS)
        print(f"{len(board)} dong, cot mau:", list(board[0])[:8] if board else None)
    except stock_data.StockDataError as exc:
        print("  LOI:", exc)


if __name__ == "__main__":
    main()
