"""Start Lectern.

    python -m app             the desktop window
    python -m app --browser   the same UI in your web browser, at http://127.0.0.1:8765 (for testing)

In the window, the UI reaches Python through pywebview (`Bridge`). In a browser it
posts to the small local server below. Both end up in the same `Api.call`.
"""
import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.config import ROOT

DIST = ROOT / "webui" / "dist"
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")


class Bridge:
    """What the window's JavaScript can call: one method, forwarded to Api.call."""

    def __init__(self):
        from app.api import Api
        self._api = Api()

    def call(self, method, payload=None):
        # Round-trip through JSON so dates and other values become plain text.
        return json.loads(json.dumps(self._api.call(method, payload), default=str))


def serve(dist: Path, port: int = 8765) -> ThreadingHTTPServer:
    """A small web server for the UI: files from `dist`, and POST /api/<method> to Api.call."""
    from app.api import Api
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


def main() -> None:
    if not (DIST / "index.html").exists():
        print("The UI hasn't been built yet. Run:  cd webui  then  npm install  and  npm run build")
        sys.exit(1)

    if "--browser" in sys.argv:
        server = serve(DIST)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print(f"Lectern is running at {url}  (Ctrl+C to stop)")
        if "--no-open" not in sys.argv:
            webbrowser.open(url)
        server.serve_forever()
        return

    import webview
    webview.create_window("Lectern", url=str(DIST / "index.html"), js_api=Bridge(),
                          width=1400, height=900, min_size=(1100, 700), background_color="#E3E7DC")
    webview.start(http_server=True)


if __name__ == "__main__":
    main()
