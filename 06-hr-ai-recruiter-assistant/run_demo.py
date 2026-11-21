#!/usr/bin/env python3
"""
Entry point to run Project 06: Bias-Free AI Recruiter Assistant
Uses standard Python library.
"""
import sys
import os
import webbrowser

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.server import RecruiterServer

if __name__ == "__main__":
    port = 8006
    server = RecruiterServer(host="127.0.0.1", port=port)
    try:
        webbrowser.open(f"http://127.0.0.1:{port}")
    except Exception:
        pass

    server.run()
