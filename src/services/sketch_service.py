"""
草图画板服务（Engineer Sketch）

打开方式：本地 HTTP 服务（127.0.0.1）+ 系统默认浏览器，而不是 file:// 直开。

为什么不用 file://
    Excalidraw 0.18 官方 dist 只发 ES module，浏览器在 file:// 下会因 CORS
    直接拒绝加载 <script type="module">（Edge 实测不执行），页面必然白屏；
    手绘字体 woff2 在 file:// 下同样会被 CORS 拦截，只能回退系统字体。
    走 127.0.0.1 后可完整保留手绘风格、语言包与 undo 能力，且依然完全离线。

静态文件位置
    开发态：  <项目根>/resources/sketch/
    打包后：  onefile → sys._MEIPASS/resources/sketch/
              onedir  → exe 同目录 resources/sketch/
"""

from __future__ import annotations

import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 起始端口；被占用时向后顺延，端口变化只影响本次会话的自动保存 origin
SKETCH_PORT = 8756
SKETCH_PORT_TRIES = 20

# 健康检查标记：用于区分「端口被本工具占用」和「被别的程序占用」
_SIGNATURE = b"engineer-sketch"

_server: ThreadingHTTPServer | None = None
_server_lock = threading.Lock()


class SketchHTTPServer(ThreadingHTTPServer):
    # 必须关掉 SO_REUSEADDR：Windows 上开着它会导致与本已占用 8756 的
    # 其他程序「绑定成功但请求仍被对方接走」的静默错绑。
    allow_reuse_address = False


def sketch_dir() -> Path:
    """返回 Sketch 静态文件目录。"""
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else PROJECT_ROOT
    return base / "resources" / "sketch"


def _handler_for(root: Path):
    """构造一个把 root 作为站点根目录的静态文件处理器。"""

    class SketchHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, directory=str(root), **kwargs)

        def do_GET(self) -> None:
            # 健康检查：用于识别「端口上跑的是不是本工具的服务」
            if self.path.rstrip("/").endswith("/__sketch_health"):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(_SIGNATURE)))
                self.end_headers()
                self.wfile.write(_SIGNATURE)
                return
            super().do_GET()

        def end_headers(self) -> None:
            # 开发阶段改完前端刷新即可生效
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, fmt: str, *args) -> None:
            # 静音：不往控制台/日志里刷请求行
            return

    return SketchHandler


def _probe(port: int) -> bool:
    """端口上是否已有一个本工具的服务在跑。"""
    import urllib.request

    # 显式绕过系统代理：探测目标是本机回环地址，走代理没有意义，
    # 而且公司网络/抓包工具配置了 http_proxy 时会把回环请求也劫持掉。
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(
            f"http://127.0.0.1:{port}/__sketch_health", timeout=0.4
        ) as resp:
            return resp.read() == _SIGNATURE
    except Exception:
        return False


def _ensure_server(root: Path) -> int:
    """确保本地服务已启动，返回端口号；0 表示启动失败。"""
    global _server

    with _server_lock:
        if _server is not None:
            return int(_server.server_address[1])

        for offset in range(SKETCH_PORT_TRIES):
            port = SKETCH_PORT + offset
            if _probe(port):
                # 另一个 Engineer Desk 实例已起服务，直接复用
                return port
            try:
                httpd = ThreadingHTTPServer(
                    ("127.0.0.1", port), _handler_for(root)
                )
            except OSError:
                continue

            httpd.daemon_threads = True
            threading.Thread(
                target=httpd.serve_forever, name="sketch-httpd", daemon=True
            ).start()
            _server = httpd
            return port

    return 0


def open_sketch() -> bool:
    """
    打开草图画板。

    Returns:
        bool: 是否成功唤起浏览器。
    """
    root = sketch_dir()
    if not (root / "index.html").exists():
        return False

    port = _ensure_server(root)
    if not port:
        return False

    return bool(
        QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{port}/index.html"))
    )


def shutdown() -> None:
    """关闭本地服务（应用退出时调用）。"""
    global _server
    with _server_lock:
        if _server is not None:
            try:
                _server.shutdown()
                _server.server_close()
            except Exception:
                pass
            _server = None
