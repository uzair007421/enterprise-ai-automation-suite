"""
Lightweight REST API & Web Dashboard Server for Project 01
Uses Python standard library (http.server) - Zero external pip dependencies required!
"""
import http.server
import socketserver
import json
import os
import urllib.parse
from typing import Dict, Any

from .orchestrator import RealEstateMultiAgentOrchestrator
from .crm import RealEstateCRM

class ProjectServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8001):
        self.host = host
        self.port = port
        self.orchestrator = RealEstateMultiAgentOrchestrator()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.static_dir = os.path.join(self.base_dir, "static")
        self.data_dir = os.path.join(self.base_dir, "data")

    def get_sample_leads(self):
        samples_path = os.path.join(self.data_dir, "sample_leads.json")
        with open(samples_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(self):
        orchestrator = self.orchestrator
        static_dir = self.static_dir
        samples = self.get_sample_leads()

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress noisy logs
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

                if path == "/api/init":
                    self._send_json(200, {
                        "samples": samples,
                        "dashboard": orchestrator.get_dashboard_summary()
                    })
                    return

                if path == "/api/dashboard":
                    self._send_json(200, orchestrator.get_dashboard_summary())
                    return

                self._send_json(404, {"error": "Not Found"})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                data = json.loads(body) if body else {}

                try:
                    if path == "/api/ingest":
                        state = orchestrator.ingest_lead(data)
                        self._send_json(200, {"success": True, "state": state.to_dict()})
                        return

                    if path == "/api/pipeline/run":
                        lead_id = data.get("lead_id")
                        state = orchestrator.run_agent_pipeline(lead_id)
                        self._send_json(200, {"success": True, "state": state.to_dict()})
                        return

                    if path == "/api/pipeline/review":
                        lead_id = data.get("lead_id")
                        decision = data.get("decision")
                        reviewer = data.get("reviewer", "Broker")
                        comments = data.get("comments", "")
                        modified_letter = data.get("modified_letter")
                        modified_price = data.get("modified_price")

                        state = orchestrator.human_review_action(
                            lead_id=lead_id,
                            decision=decision,
                            reviewer=reviewer,
                            comments=comments,
                            modified_letter=modified_letter,
                            modified_price=modified_price
                        )
                        self._send_json(200, {"success": True, "state": state.to_dict()})
                        return

                    if path == "/api/reset":
                        # Reset memory & CRM
                        orchestrator.active_workflows.clear()
                        orchestrator.approval_queue.clear()
                        db_path = orchestrator.crm.db_path
                        if os.path.exists(db_path):
                            os.remove(db_path)
                        orchestrator.crm._ensure_db()
                        self._send_json(200, {"success": True, "message": "System reset"})
                        return

                    self._send_json(404, {"error": "Endpoint Not Found"})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})

        print(f"\n=======================================================")
        print(f"🚀 [Project 01] Multi-Agent Real Estate Sales Automation")
        print(f"🌐 Server active at: http://{self.host}:{self.port}")
        print(f"👉 Open this URL in your browser to view the Live Demo!")
        print(f"=======================================================\n")

        with socketserver.TCPServer((self.host, self.port), RequestHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
