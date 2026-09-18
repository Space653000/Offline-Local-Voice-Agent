# -*- coding: utf-8 -*-
"""
主控台專用的輕量本機伺服器：
- 一般路徑 = 靜態檔案（跟原本 python -m http.server 行為一樣）
- GET /api/orders = 掃描交接資料夾，回傳最近的 ORDER.md 清單（給主控台的「已送出訂單」區塊用）
- POST /api/command = 文字輸入指令（companion.html的文字輸入框用，跟語音路徑共用command_processor.py）
- POST /api/stop = 中斷這個session目前卡住的任務（PlanRunner確認中/FrontDesk問答中），對照語音路徑的「停止」指令
- POST /api/confirm = 桌面控制L2/L3確認後的文字回覆
- POST /api/frontdesk_reply = Front Desk文字問答下一輪回覆

只綁定 127.0.0.1，不對外開放。
用 ThreadingMixIn 是因為 /api/command 會擋住(跑ASR/LLM/Executor)，如果不用多執行緒，
處理文字指令期間 companion.html 的 /api/state 500ms輪詢會卡住，畫面看起來像當掉。
"""
import http.server
import json
import re
import socketserver
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

HANDOFF_DIR = Path("C:/0_JN1_AERIS_HANDOFF/orders")
DELIVERY_DIR = Path("C:/0_JN1_AERIS_HANDOFF/delivery")  # 未來 AERIS 完工後可能的回傳位置，先預留判斷
LIVE_STATE_FILE = Path(__file__).parent / "live_state.json"  # listen_loop.py 執行中會持續寫入這個檔案


def parse_order_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    fields = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
    goal_m = re.search(r"# User Goal\n(.+)", text)
    fields["user_goal"] = goal_m.group(1).strip() if goal_m else ""
    fields["filename"] = path.name
    return fields


def list_orders() -> list:
    if not HANDOFF_DIR.exists():
        return []
    orders = []
    for p in sorted(HANDOFF_DIR.glob("*_ORDER.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            fields = parse_order_frontmatter(p)
            case_id = fields.get("case_id", "")
            delivered = (DELIVERY_DIR / case_id).exists() if case_id else False
            fields["delivered"] = delivered
            orders.append(fields)
        except Exception as e:
            orders.append({"filename": p.name, "error": str(e)})
    return orders[:20]


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/orders":
            body = json.dumps(list_orders(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/state":
            if LIVE_STATE_FILE.exists():
                body = LIVE_STATE_FILE.read_bytes()
            else:
                body = json.dumps({"status": "not_running"}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        from command_processor import process_text, confirm_desktop_command, continue_frontdesk_text, stop_session

        try:
            if self.path == "/api/command":
                data = self._read_json_body()
                result = process_text(data["text"], data.get("session_id", "default"))
                self._send_json(result)
                return
            if self.path == "/api/stop":
                data = self._read_json_body()
                result = stop_session(data.get("session_id", "default"))
                self._send_json(result)
                return
            if self.path == "/api/confirm":
                data = self._read_json_body()
                result = confirm_desktop_command(
                    data["tool"], data["args"], data["approved"], data.get("typed_keyword"),
                    data.get("session_id", "default"),
                )
                self._send_json(result)
                return
            if self.path == "/api/frontdesk_reply":
                data = self._read_json_body()
                result = continue_frontdesk_text(data.get("session_id", "default"), data["reply"])
                self._send_json(result)
                return
            self._send_json({"status": "error", "reason": "not found"}, status=404)
        except Exception as e:
            self._send_json({"status": "error", "reason": str(e)}, status=500)

    def log_message(self, fmt, *args):
        pass  # 安靜一點，不洗版終端機


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"serving on http://127.0.0.1:{port}/ (with /api/orders, /api/command)")
        httpd.serve_forever()
