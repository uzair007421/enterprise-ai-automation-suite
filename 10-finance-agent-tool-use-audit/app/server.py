"""
REST API & Web Interface for Project 10: Custom Finance AI Agent with Tool Use & Audit Logs
Uses Python standard library - zero external dependencies required.
"""
import http.server
import socketserver
import json
import os
import urllib.parse
from typing import Dict, Any

from .finance_agent import FinanceSecurityAgent

class FinanceServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8010):
        self.host = host
        self.port = port
        self.agent = FinanceSecurityAgent()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.static_dir = os.path.join(self.base_dir, "static")

    def run(self):
        agent = self.agent
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

                if path == "/api/summary":
                    self._send_json(200, agent.get_summary())
                    return

                self._send_json(404, {"error": "Not Found"})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                data = json.loads(body) if body else {}

                if path == "/api/prompt":
                    user_id = data.get("user_id", "usr_manager")
                    prompt = data.get("prompt", "")
                    result = agent.execute_prompt(user_id, prompt)
                    self._send_json(200, result)
                    return

                if path == "/api/write_decision":
                    write_id = data.get("write_id")
                    decision = data.get("decision", "APPROVED")
                    approver_id = data.get("approver_id", "usr_cfo")
                    result = agent.confirm_write_action(write_id, decision, approver_id)
                    self._send_json(200, result)
                    return

                if path == "/api/reset":
                    agent.reset_state()
                    self._send_json(200, {"success": True, "message": "State reset"})
                    return

                self._send_json(404, {"error": "Endpoint Not Found"})

        print(f"\n=======================================================")
        print(f"💼 [Project 10] Custom Finance Agent with Tool Gates & Audit")
        print(f"🔒 RBAC & Mandatory Write Confirmation Gate Active")
        print(f"🌐 Server active at: http://{self.host}:{self.port}")
        print(f"👉 Open this URL in your browser to view the Live Demo!")
        print(f"=======================================================\n")

        with socketserver.TCPServer((self.host, self.port), RequestHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
