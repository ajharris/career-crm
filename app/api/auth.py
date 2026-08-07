"""Small HS256 JWT implementation for API bearer authentication."""

import base64
import hashlib
import hmac
import json
import time

from flask import current_app


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def issue(user_id, ttl=3600):
    header = _b64(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload = _b64(
        json.dumps(
            {
                "sub": str(user_id),
                "iat": int(time.time()),
                "exp": int(time.time()) + ttl,
            },
            separators=(",", ":"),
        ).encode()
    )
    body = f"{header}.{payload}"
    signature = _b64(
        hmac.new(
            current_app.config["SECRET_KEY"].encode(), body.encode(), hashlib.sha256
        ).digest()
    )
    return f"{body}.{signature}"


def verify(token):
    try:
        header, payload, signature = token.split(".")
        body = f"{header}.{payload}"
        expected = _b64(
            hmac.new(
                current_app.config["SECRET_KEY"].encode(), body.encode(), hashlib.sha256
            ).digest()
        )
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return int(data["sub"]) if data["exp"] >= time.time() else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
