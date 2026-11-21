#!/usr/bin/env python3
"""
Entry point to run Project 01: Multi-Agent Real Estate Sales Automation
Zero-dependency runner: uses Python standard library only!
"""
import sys
import os
import webbrowser

# Add current folder to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.server import ProjectServer

if __name__ == "__main__":
    port = 8001
    server = ProjectServer(host="127.0.0.1", port=port)
    
    # Optionally open browser
    try:
        webbrowser.open(f"http://127.0.0.1:{port}")
    except Exception:
        pass

    server.run()
