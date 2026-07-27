"""Enterprise security framework: JWT auth, password hashing, rate limiting, sanitization."""

import os
import re
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

try:
    import jwt
    import bcrypt
except ImportError:
    jwt = None
    bcrypt = None


class SecurityService:
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET", "change-this-in-production")
        self.jwt_expires_in = int(os.getenv("JWT_EXPIRES_IN_SECONDS", "86400"))
        self.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
        self.rate_limit_window_ms = int(os.getenv("RATE_LIMIT_WINDOW_MS", "900000"))
        self.rate_limit_max_requests = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))

    def generate_token(self, payload: Dict[str, Any]) -> str:
        if jwt is None:
            raise RuntimeError("PyJWT is not installed")
        payload["iss"] = "procureflow"
        payload["aud"] = "bd_procurement_users"
        payload["iat"] = datetime.utcnow()
        payload["exp"] = datetime.utcnow() + timedelta(seconds=self.jwt_expires_in)
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def verify_token(self, token: str) -> Dict[str, Any]:
        if jwt is None:
            raise RuntimeError("PyJWT is not installed")
        return jwt.decode(
            token, self.jwt_secret, algorithms=["HS256"],
            issuer="procureflow", audience="bd_procurement_users",
        )

    def hash_password(self, password: str) -> str:
        if bcrypt is None:
            raise RuntimeError("bcrypt is not installed")
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(self.bcrypt_rounds)).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        if bcrypt is None:
            raise RuntimeError("bcrypt is not installed")
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        checks = [
            (len(password) >= 8, "Password must be at least 8 characters"),
            (len(password) <= 128, "Password must not exceed 128 characters"),
            (bool(re.search(r"[A-Z]", password)), "Must contain an uppercase letter"),
            (bool(re.search(r"[a-z]", password)), "Must contain a lowercase letter"),
            (bool(re.search(r"\d", password)), "Must contain a number"),
            (bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)), "Must contain a special character"),
        ]
        for passed, msg in checks:
            if not passed:
                return False, msg
        return True, "Password strength is acceptable"

    def generate_secure_password(self, length: int = 16) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        return "".join(secrets.choice(chars) for _ in range(length))

    def sanitize_input(self, value: str) -> str:
        replacements = {
            "<": "&lt;", ">": "&gt;", '"': "&quot;",
            "'": "&#x27;", "\\": "&#x5c;",
        }
        result = "".join(replacements.get(c, c) for c in value)
        return result.strip()

    def get_security_headers(self) -> Dict[str, str]:
        return {
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
                "font-src 'self' data:; connect-src 'self' https://api.procureflow.com; "
                "frame-src 'none'; object-src 'none';"
            ),
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-DNS-Prefetch-Control": "off",
            "X-Download-Options": "noopen",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }


security_service = SecurityService()
