"""Dinh nghia tool cho Claude + dispatch sang code Python thuc thi.

Them tool moi (vd broker API sau nay): them 1 entry vao TOOL_SCHEMAS va 1 nhanh
trong execute_tool - khong can sua orchestrator."""

import json
from typing import Any

from app.db import repository
from app.tools import stock_data

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_price",
        "description": (
            "Lay gia dong phien gan nhat cua 1 ma chung khoan Viet Nam kem bien dong "
            "so voi phien truoc. Dung khi nguoi dung hoi gia hien tai cua 1 ma."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ma chung khoan, vd VNM, FPT, VCB"}
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_price_board",
        "description": (
            "Lay bang gia cho nhieu ma cung luc. Dung khi nguoi dung hoi gia cua nhieu ma "
            "hoac hoi tinh hinh watchlist - re va nhanh hon goi get_price nhieu lan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sach ma chung khoan",
                }
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "get_history",
        "description": (
            "Lay du lieu gia lich su (OHLCV) cua 1 ma. Dung khi can phan tich xu huong, "
            "tinh chi bao ky thuat, hoac so sanh dien bien gia theo thoi gian."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "days": {
                    "type": "integer",
                    "description": "So ngay lich su can lay, mac dinh 90",
                },
                "interval": {
                    "type": "string",
                    "enum": ["1D", "1W", "1M"],
                    "description": "Do phan giai nen, mac dinh 1D",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_company_overview",
        "description": (
            "Lay thong tin tong quan doanh nghiep: von hoa, so luong co phieu luu hanh, "
            "danh gia, nganh. Dung khi nguoi dung hoi ve ban than doanh nghiep."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "get_financial_ratios",
        "description": (
            "Lay chi so tai chinh (EPS, BVPS, P/E, P/B, ROE, ROA...) cho vai ky gan nhat. "
            "Dung khi nguoi dung hoi ve suc khoe tai chinh hoac dinh gia co phieu."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "period": {"type": "string", "enum": ["year", "quarter"]},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "list_watchlist",
        "description": "Liet ke cac ma trong danh sach theo doi cua nguoi dung.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_watchlist",
        "description": "Them 1 ma vao danh sach theo doi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "note": {"type": "string", "description": "Ghi chu tuy chon"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "remove_watchlist",
        "description": "Xoa 1 ma khoi danh sach theo doi.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "list_alerts",
        "description": "Liet ke cac canh bao gia da dat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "active_only": {"type": "boolean", "description": "Chi lay canh bao dang bat"}
            },
        },
    },
    {
        "name": "create_alert",
        "description": (
            "Tao canh bao gia. He thong se kiem tra dinh ky va gui tin nhan Telegram khi "
            "dieu kien thoa man. condition: price_above (gia vuot nguong), price_below "
            "(gia xuong duoi nguong), pct_change (bien dong % trong phien vuot nguong). "
            "threshold cho price_above/price_below tinh theo nghin VND (vd 71.5)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "condition": {
                    "type": "string",
                    "enum": ["price_above", "price_below", "pct_change"],
                },
                "threshold": {"type": "number"},
            },
            "required": ["symbol", "condition", "threshold"],
        },
    },
]


def execute_tool(name: str, params: dict[str, Any]) -> str:
    """Chay tool va tra ve chuoi JSON de gui lai cho Claude."""
    try:
        result = _dispatch(name, params)
    except stock_data.StockDataError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"Loi khi chay tool {name}: {exc}"}, ensure_ascii=False)

    return json.dumps(result, ensure_ascii=False, default=str)


def _dispatch(name: str, p: dict[str, Any]) -> Any:
    if name == "get_price":
        return stock_data.get_current_price(p["symbol"])
    if name == "get_price_board":
        return stock_data.get_price_board(p["symbols"])
    if name == "get_history":
        return stock_data.get_history(
            p["symbol"], days=p.get("days", 90), interval=p.get("interval", "1D")
        )
    if name == "get_company_overview":
        return stock_data.get_company_overview(p["symbol"])
    if name == "get_financial_ratios":
        return stock_data.get_financial_ratios(p["symbol"], period=p.get("period", "year"))
    if name == "list_watchlist":
        return repository.list_watchlist()
    if name == "add_watchlist":
        repository.add_watchlist(p["symbol"], p.get("note"))
        return {"ok": True, "message": f"Da them {p['symbol'].upper()} vao watchlist"}
    if name == "remove_watchlist":
        repository.remove_watchlist(p["symbol"])
        return {"ok": True, "message": f"Da xoa {p['symbol'].upper()} khoi watchlist"}
    if name == "list_alerts":
        return repository.list_alerts(active_only=p.get("active_only", False))
    if name == "create_alert":
        alert = repository.create_alert(p["symbol"], p["condition"], p["threshold"])
        return {"ok": True, "alert": alert}

    return {"error": f"Tool khong ton tai: {name}"}
