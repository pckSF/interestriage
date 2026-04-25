from __future__ import annotations

import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class EvilHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/redirect-private":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1/private")
            self.end_headers()
            return

        if self.path == "/oversized":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"A" * (3 * 1024 * 1024))
            return

        if self.path == "/slow-loris":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            for _ in range(12):
                self.wfile.write(b".")
                self.wfile.flush()
                time.sleep(1)
            return

        if self.path == "/content-mismatch":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"<html><script>alert('xss')</script></html>")
            return

        if self.path == "/markdown-injection":
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown")
            self.end_headers()
            self.wfile.write(b"# Header\n\n<script>alert('bad')</script>\n")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"evil-server-ready")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8081), EvilHandler)
    server.serve_forever()
