"""
REST API & Web Interface for Project 04: Invoice-to-Accounting Autonomous Pipeline
Uses Python standard library - zero external dependencies required.
"""
import http.server
import socketserver
import json
import os
import urllib.parse
from typing import Dict, Any

from .invoice_processor import InvoicePipeline

class InvoiceServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8004):
        self.host = host
        self.port = port
        self.pipeline = InvoicePipeline()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.static_dir = os.path.join(self.base_dir, "static")
        self.data_dir = os.path.join(self.base_dir, "data")

    def get_sample_invoices(self):
        samples_path = os.path.join(self.data_dir, "sample_invoices.json")
        with open(samples_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(self):
        pipeline = self.pipeline
        static_dir = self.static_dir
        samples = self.get_sample_invoices()

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

                if path == "/api/init":
                    self._send_json(200, {
                        "samples": samples,
                        "summary": pipeline.get_summary()
                    })
                    return

                if path == "/api/summary":
                    self._send_json(200, pipeline.get_summary())
                    return

                self._send_json(404, {"error": "Not Found"})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                data = json.loads(body) if body else {}

                if path == "/api/process":
                    result = pipeline.process_invoice(data)
                    self._send_json(200, {"success": True, "record": result})
                    return

                if path == "/api/review":
                    invoice_id = data.get("invoice_id")
                    decision = data.get("decision")
                    corrected_total = data.get("corrected_total")
                    note = data.get("note", "")

                    result = pipeline.review_action(invoice_id, decision, corrected_total, note)
                    self._send_json(200, {"success": True, "record": result})
                    return

                if path == "/api/reset":
                    pipeline.reset_db()
                    self._send_json(200, {"success": True, "message": "Ledger reset"})
                    return

                self._send_json(404, {"error": "Endpoint Not Found"})

        print(f"\n=======================================================")
        print(f"📊 [Project 04] Invoice-to-Accounting Autonomous Pipeline")
        print(f"💼 OCR Validation & QuickBooks/Xero Sync Active")
        print(f"🌐 Server active at: http://{self.host}:{self.port}")
        print(f"👉 Open this URL in your browser to view the Live Demo!")
        print(f"=======================================================\n")

        with socketserver.TCPServer((self.host, self.port), RequestHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
