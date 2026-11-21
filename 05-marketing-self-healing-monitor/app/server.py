"""
REST API & Web Interface for Project 05: Self-Healing Workflow Monitor
Uses Python standard library - zero external dependencies required.
"""
import http.server
import socketserver
import json
import os
import urllib.parse
from typing import Dict, Any

from .sentinel import SentinelMonitor

class SentinelServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8005):
        self.host = host
        self.port = port
        self.monitor = SentinelMonitor()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.static_dir = os.path.join(self.base_dir, "static")

    def run(self):
        monitor = self.monitor
        static_dir = self.static_dir

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def _send_json(self, status: int, data: Dict[str, Any]):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path

                if path == "/" or path == "/index.html":
                    html_path = os.path.join(static_dir, "index.html")
                    with open(html_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(content)
                    return

                if path == "/api/fleet":
                    self._send_json(200, monitor.get_fleet_status())
                    return

                if path == "/api/daily_report":
                    self._send_json(200, monitor.generate_daily_health_report())
                    return

                self._send_json(404, {"error": "Not Found"})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                data = json.loads(body) if body else {}

                if path == "/api/inject_failure":
                    wf_id = data.get("workflow_id", "WF-01")
                    err_type = data.get("error_type", "RATE_LIMIT_429")
                    res = monitor.inject_failure(wf_id, err_type)
                    self._send_json(200, res)
                    return

                if path == "/api/reset":
                    monitor.reset_state()
                    self._send_json(200, {"success": True, "message": "State reset"})
                    return

                self._send_json(404, {"error": "Endpoint Not Found"})

        print(f"\n=======================================================")
        print(f"🛡️ [Project 05] Self-Healing Workflow Monitor & Sentinel")
        print(f"⚡ Fleet Observability for 40 Marketing Automations Active")
        print(f"🌐 Server active at: http://{self.host}:{self.port}")
        print(f"👉 Open this URL in your browser to view the Live Demo!")
        print(f"=======================================================\n")

        with socketserver.TCPServer((self.host, self.port), RequestHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
