"""Sinh ADMIN_PASSWORD_HASH va APP_SECRET_KEY de dan vao .env.

Chay: python scripts/make_secrets.py 'mat-khau-cua-ban'
"""

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.web.auth import hash_password  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Cach dung: python scripts/make_secrets.py 'mat-khau-cua-ban'")
        raise SystemExit(1)

    print(f"ADMIN_PASSWORD_HASH={hash_password(sys.argv[1])}")
    print(f"APP_SECRET_KEY={secrets.token_urlsafe(48)}")


if __name__ == "__main__":
    main()
