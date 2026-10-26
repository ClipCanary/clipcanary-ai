"""Upload a local file to ClipCanary and get the `input` for a job. Python 3.9+, standard library only.

    from clipcanary_upload import upload_file
    job["input"] = upload_file("talk.mov", os.environ["CLIPCANARY_API_KEY"])

Handles both answers `POST /v1/uploads` can give: one PUT for a file up to 5 GiB less
5 MiB, or parts (sent four at a time, each retried) and the call that joins them.
Run it as a script to try it: `python clipcanary_upload.py talk.mov`.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API_BASE = os.environ.get("CLIPCANARY_API_BASE", "https://api.clipcanary.com").rstrip("/")
#: Python's own default User-Agent is refused by the API's edge (a plain-text 403).
USER_AGENT = "clipcanary-upload/1.0 (python)"
PARTS_AT_ONCE = 4
ATTEMPTS = 4


class UploadError(RuntimeError):
    """The API or the storage refused, with the reason it gave."""


class _Slice:
    """`length` bytes of a file from `offset`, read as the request is sent."""

    def __init__(self, path: str, offset: int, length: int) -> None:
        self._file = open(path, "rb")  # noqa: SIM115 - closed by `close`
        self._file.seek(offset)
        self._left = length

    def read(self, size: int = -1) -> bytes:
        if self._left <= 0:
            return b""
        size = self._left if size < 0 else min(size, self._left)
        chunk = self._file.read(size)
        self._left -= len(chunk)
        return chunk

    def close(self) -> None:
        self._file.close()


def _send(method: str, url: str, headers: dict, body=None, timeout: float = 3600) -> bytes:
    """One request, retried on a dropped connection or a 5xx. A 4xx raises with its reason."""
    for attempt in range(1, ATTEMPTS + 1):
        data = body() if callable(body) else body
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("User-Agent", USER_AGENT)
        for name, value in headers.items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as answer:
                return answer.read()
        except urllib.error.HTTPError as exc:
            text = exc.read().decode(errors="replace")
            if exc.code < 500 or attempt == ATTEMPTS:
                try:
                    text = json.loads(text).get("detail", text)
                except (ValueError, AttributeError):
                    pass
                raise UploadError(
                    f"{method} {url.split('?')[0]} answered {exc.code}: {text}"
                ) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == ATTEMPTS:
                raise UploadError(f"{method} {url.split('?')[0]} failed: {exc}") from None
        finally:
            if hasattr(data, "close"):
                data.close()
        time.sleep(min(30, 2**attempt))
    raise AssertionError("unreachable")


def _api(method: str, path: str, api_key: str, payload: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {api_key}"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    return json.loads(_send(method, f"{API_BASE}{path}", headers, body, timeout=60))


def upload_file(path: str, api_key: str, content_type: str | None = None) -> dict:
    """Upload `path` and return the job input for it: `{"upload_id": "up_…"}`."""
    size = os.path.getsize(path)
    kind = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
    ticket = _api(
        "POST",
        "/v1/uploads",
        api_key,
        {"filename": os.path.basename(path), "content_type": kind, "size_bytes": size},
    )
    if ticket.get("put_url"):
        _send(
            "PUT",
            ticket["put_url"],
            ticket["headers"],
            lambda: _Slice(path, 0, size),
        )
        return ticket["source"]

    def send_part(part: dict) -> None:
        _send(
            "PUT",
            part["put_url"],
            part["headers"],
            lambda: _Slice(path, part["offset"], part["size_bytes"]),
        )

    with ThreadPoolExecutor(PARTS_AT_ONCE) as pool:
        list(pool.map(send_part, ticket["parts"]))
    _api(
        "POST",
        ticket.get("complete_path") or f"/v1/uploads/{ticket['upload_id']}/complete",
        api_key,
    )
    return ticket["source"]


if __name__ == "__main__":  # pragma: no cover - a convenience for trying it by hand
    if len(sys.argv) != 2 or "CLIPCANARY_API_KEY" not in os.environ:
        sys.exit("usage: CLIPCANARY_API_KEY=sk_… python clipcanary_upload.py <file>")
    print(json.dumps(upload_file(sys.argv[1], os.environ["CLIPCANARY_API_KEY"])))
