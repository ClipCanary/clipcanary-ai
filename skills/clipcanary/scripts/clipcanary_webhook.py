"""Verify a ClipCanary webhook delivery. Python 3.9+, standard library only.

    from clipcanary_webhook import verify_delivery
    if not verify_delivery(raw_body, request.headers, os.environ["CLIPCANARY_WEBHOOK_SECRET"]):
        return 400

`raw_body` must be the exact bytes received (Flask: `request.get_data()`, FastAPI:
`await request.body()`, Django: `request.body`), never re-serialised JSON. The secret is
the account's `whsec_…` from the dashboard's API keys page.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping

TOLERANCE_S = 300


def _header(headers: Mapping[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def verify_delivery(
    raw_body: bytes,
    headers: Mapping[str, str],
    secret: str,
    tolerance_s: int = TOLERANCE_S,
    now: float | None = None,
) -> bool:
    """True when the delivery is signed with `secret` and less than `tolerance_s` old."""
    timestamp = _header(headers, "X-Fleet-Timestamp")
    signature = _header(headers, "X-Fleet-Signature")
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs((time.time() if now is None else now) - sent_at) > tolerance_s:
        return False
    material = f"{sent_at}.".encode() + raw_body
    expected = "v1=" + hmac.new(secret.encode(), material, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), signature.encode())
