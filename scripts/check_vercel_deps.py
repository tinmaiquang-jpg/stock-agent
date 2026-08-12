"""Kiem tra bundle Vercel co du dependency khong. CHAY TRUOC MOI LAN DEPLOY.

Cach lam: tinh xem uv se cai nhung package nao tu pyproject.toml, roi CHAN tat ca package
ngoai danh sach do va thu import api/index.py. Neu import duoc thi Vercel cung se chay duoc.

Cach nay chinh xac hon viec chi liet ke module duoc nap, vi nhieu thu vien boc import
trong try/except ImportError va van chay binh thuong khi thieu package (vd uvicorn trong
sse_starlette, cryptography trong python-telegram-bot). Chi nhung import KHONG duoc boc
moi lam function chet.

Loi that da gap: python-telegram-bot import apscheduler khong co try/except, ma apscheduler
chi la extra 'job-queue' nen uv khong cai -> function crash luc import, HTTP 500 o MOI route.
Local khong lo ra vi .venv cai tu requirements.txt (day du hon pyproject.toml).

    python scripts/check_vercel_deps.py
"""

import importlib.metadata as md
import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _norm(name: str) -> str:
    """Chuan hoa ten package: bo version, bo extra, ve chu thuong."""
    for sep in ("==", ">=", "~=", "<=", "<", ">", "!=", "("):
        name = name.split(sep)[0]
    return name.lower().replace("_", "-").split("[")[0].strip()


def _extras_of(spec: str) -> set[str]:
    if "[" not in spec:
        return set()
    return {e.strip() for e in spec.split("[", 1)[1].split("]", 1)[0].split(",")}


def _requirement(spec: str) -> tuple[str, str | None]:
    """Tach 'ten>=1.0; extra == \"x\"' thanh (ten, ten-extra-dieu-kien)."""
    marker = None
    if ";" in spec:
        spec, condition = spec.split(";", 1)
        if "extra" in condition:
            for quote in ('"', "'"):
                if quote in condition:
                    marker = condition.split(quote)[1]
                    break
    return _norm(spec), marker


def _closure(declared: list[str]) -> set[str]:
    """Tap package uv se cai: dependency truc tiep + gian tiep + extra duoc yeu cau."""
    resolved: set[str] = set()
    queue = [(_norm(s), _extras_of(s)) for s in declared]
    done: set[tuple[str, frozenset]] = set()

    while queue:
        name, extras = queue.pop()
        key = (name, frozenset(extras))
        if key in done:
            continue
        done.add(key)
        resolved.add(name)
        try:
            requires = md.requires(name) or []
        except md.PackageNotFoundError:
            continue
        for req in requires:
            dep, marker = _requirement(req)
            if marker and marker not in extras:
                continue  # dependency co dieu kien extra ma ta khong yeu cau
            queue.append((dep, _extras_of(req)))
    return resolved


BLOCKER = """
import sys, json

BLOCKED = set(json.loads({blocked!r}))

class Blocker:
    def find_module(self, name, path=None):
        return None
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(f"[gia lap Vercel] khong co package cung cap '{{name}}'")
        return None

sys.meta_path.insert(0, Blocker())
sys.path.insert(0, {root!r})

try:
    import api.index
except Exception as exc:
    print("FAIL [import api.index]", type(exc).__name__, exc)
    raise SystemExit(0)

# Import duoc chua du: build_application() chi chay khi co tin nhan den, va cac thu vien
# co the thieu thu chi can luc chay chu khong phai luc import.
try:
    from app.telegram_bot.bot import build_application
    build_application()
except Exception as exc:
    print("FAIL [build_application]", type(exc).__name__, exc)
    raise SystemExit(0)

print("OK")
"""


def main() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    installed = _closure(pyproject["project"]["dependencies"])

    # Module nao thuoc package KHONG nam trong bundle -> chan de gia lap moi truong Vercel
    blocked = set()
    for module, dists in md.packages_distributions().items():
        if not any(_norm(d) in installed for d in dists):
            blocked.add(module)

    script = BLOCKER.format(blocked=json.dumps(sorted(blocked)), root=str(ROOT))
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT
    )
    output = result.stdout.strip().splitlines()
    verdict = output[-1] if output else "FAIL (khong co ket qua)"

    if verdict.startswith("OK"):
        print(f"OK - import duoc voi dung {len(installed)} package tu pyproject.toml.")
        print(f"Da chan {len(blocked)} package ngoai bundle de gia lap Vercel.")
        return 0

    print("FUNCTION SE CRASH TREN VERCEL\n")
    print(f"  {verdict}\n")
    if result.stderr.strip():
        print("  " + result.stderr.strip().splitlines()[-1])
    print("\nThem package con thieu vao [project.dependencies] trong pyproject.toml.")
    print("Neu no la extra cua package khac, dung dang 'ten-gói[extra]'.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
