"""
Lightweight Web Viewer & Inspection Server for Ghost-Desktop.
Provides an HTML5 live canvas visualizer and interactive inspection console.
"""

import http.server
import json
import threading
from typing import Optional
from .display import VirtualDisplay
from .models import ComputerAction, ActionType


HTML_VIEWER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Ghost-Desktop Ephemeral Live Inspector</title>
  <style>
    body {
      background-color: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .header {
      width: 1280px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid #30363d;
    }
    .badge {
      background: #238636;
      color: #fff;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
    }
    #screen-container {
      position: relative;
      border: 2px solid #30363d;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.8);
      cursor: crosshair;
    }
    #screen-img {
      display: block;
      width: 1280px;
      height: 800px;
    }
    .controls {
      width: 1280px;
      margin-top: 15px;
      display: flex;
      gap: 15px;
      background: #161b22;
      padding: 15px;
      border-radius: 8px;
      border: 1px solid #30363d;
    }
    button {
      background: #21262d;
      color: #58a6ff;
      border: 1px solid #30363d;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
    }
    button:hover { background: #30363d; }
    #status { font-family: monospace; font-size: 13px; color: #8b949e; align-self: center; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h2 style="margin: 0; color: #58a6ff;">❖ Ghost-Desktop Live Sandbox</h2>
      <span style="font-size: 13px; color: #8b949e;">Ephemeral Virtual Framebuffer for AI Computer-Use Agents</span>
    </div>
    <div style="display:flex; gap:10px; align-items:center;">
      <span class="badge">SANDBOX ARMED</span>
      <span style="font-size:12px; color:#8b949e;" id="refresh-rate">30 FPS Stream</span>
    </div>
  </div>

  <div id="screen-container">
    <img id="screen-img" src="/screenshot.png" alt="Ghost-Desktop Virtual Screen">
  </div>

  <div class="controls">
    <button onclick="refreshScreen()">Force Refresh</button>
    <button onclick="sendAction('reset')">Reset Snapshot (Clean)</button>
    <div id="status">Listening for Computer-Use API Calls...</div>
  </div>

  <script>
    function refreshScreen() {
      const img = document.getElementById('screen-img');
      img.src = '/screenshot.png?t=' + Date.now();
    }
    setInterval(refreshScreen, 1000);

    const container = document.getElementById('screen-container');
    container.addEventListener('click', (e) => {
      const rect = container.getBoundingClientRect();
      const x = Math.round((e.clientX - rect.left) * (1280 / rect.width));
      const y = Math.round((e.clientY - rect.top) * (800 / rect.height));
      fetch('/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'left_click', coordinate: [x, y]})
      }).then(r => r.json()).then(data => {
        document.getElementById('status').innerText = 'User Click: (' + x + ', ' + y + ') -> ' + data.output;
        refreshScreen();
      });
    });

    function sendAction(type) {
      if (type === 'reset') {
        fetch('/reset', {method: 'POST'}).then(() => {
          document.getElementById('status').innerText = 'Environment reset to clean baseline in <200ms';
          refreshScreen();
        });
      }
    }
  </script>
</body>
</html>
"""


class GhostViewerHandler(http.server.BaseHTTPRequestHandler):
    display: Optional[VirtualDisplay] = None

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/index"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_VIEWER_TEMPLATE.encode("utf-8"))
        elif self.path.startswith("/screenshot.png"):
            if self.display:
                img = self.display.render_canvas()
                import io
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png_bytes)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(png_bytes)
            else:
                self.send_error(500, "Display not initialized")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if self.path == "/action" and self.display:
            try:
                data = json.loads(post_data.decode("utf-8"))
                coord = data.get("coordinate")
                res = self.display.click(coord[0] if coord else None, coord[1] if coord else None)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": res.success,
                    "output": res.output,
                    "cursor": res.cursor_position
                }).encode("utf-8"))
            except Exception as e:
                self.send_error(400, str(e))
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logs
        return


def start_viewer_server(display: VirtualDisplay, port: int = 8787) -> threading.Thread:
    """Start web inspection server in background thread."""
    handler = GhostViewerHandler
    handler.display = display
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t
