"""A small local web server for the UI, used for testing in a normal browser.

    python -m app --browser      opens http://127.0.0.1:8765

The desktop window doesn't need it: there the UI talks to `Api` directly
through pywebview. Both routes call the same `Api.call`.
"""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.api import Api

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")


def serve(dist: Path, port: int = 8765) -> ThreadingHTTPServer:
    api = Api()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if not self.path.startswith("/api/"):
                return self._send(404, b"", "text/plain")
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            result = api.call(self.path[len("/api/"):], payload)
            self._send(200, json.dumps(result, default=str).encode(), "application/json")

        def do_GET(self):
            rel = self.path.split("?")[0].lstrip("/") or "index.html"
            target = (dist / rel).resolve()
            if not str(target).startswith(str(dist.resolve())) or not target.is_file():
                target = dist / "index.html"
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send(200, target.read_bytes(), kind)

    # Bound to this computer only: nothing on the network can reach it.
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
