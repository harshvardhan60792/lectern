"""Start Lectern.

    python -m app             the desktop window
    python -m app --browser   the same UI in your web browser (for testing)
"""
import json
import sys
import webbrowser

from app.config import ROOT

DIST = ROOT / "webui" / "dist"


class Bridge:
    """What the window's JavaScript can call: one method, forwarded to Api.call."""

    def __init__(self):
        from app.api import Api
        self._api = Api()

    def call(self, method, payload=None):
        # Round-trip through JSON so dates and other values become plain text.
        return json.loads(json.dumps(self._api.call(method, payload), default=str))


def main() -> None:
    if not (DIST / "index.html").exists():
        print("The UI hasn't been built yet. Run:  cd webui  then  npm install  and  npm run build")
        sys.exit(1)

    if "--browser" in sys.argv:
        from app.server import serve
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
