"""
desktop_launcher.py
===================
Launches Ma Maison Executive BI Suite as a native Windows desktop application.
Uses native standalone App Window mode (no browser address bar or tabs).
"""

import sys
import os
import time
import subprocess
import urllib.request

APP_URL = "http://localhost:8050"

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def launch_desktop():
    # Check if backend server is responsive
    if not wait_for_server(APP_URL, timeout=3):
        # Start server in background
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8050"],
                         cwd=curr_dir, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        wait_for_server(APP_URL, timeout=8)

    # Launch standalone application window (Edge App mode)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]

    for p in edge_paths + chrome_paths:
        if os.path.exists(p):
            subprocess.Popen([p, f"--app={APP_URL}", "--window-size=1480,920"])
            return

    # Fallback to default browser
    import webbrowser
    webbrowser.open(APP_URL)

if __name__ == "__main__":
    launch_desktop()

