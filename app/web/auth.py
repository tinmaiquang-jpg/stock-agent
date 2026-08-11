"""Auth don gian cho web admin 1 nguoi dung: password hash trong .env + session cookie."""

import hashlib
import hmac
import secrets

from fastapi import Request

from app.config import get_settings

SESSION_KEY = "admin_authenticated"


def hash_password(password: str) -> str:
    """Tao hash de dat vao ADMIN_PASSWORD_HASH. Format: <salt_hex>$<hash_hex>."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def check_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    user_ok = hmac.compare_digest(username, settings.admin_username)
    pass_ok = verify_password(password, settings.admin_password_hash)
    return user_ok and pass_ok


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get(SESSION_KEY))
