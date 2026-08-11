"""
Chrome CDP Bridge (V2) — connects to Playwright MCP Bridge extension via protocol V2.
Supports chrome.tabs.create, chrome.debugger.attach/detach/sendCommand directly.

Architecture:
  Playwright (WSL)  ──CDP──►  bridge  ──chrome.* API──►  extension  ──debugger──►  Chrome
"""

from __future__ import annotations
import asyncio, json, logging, uuid, subprocess
from typing import Any

try:
    import websockets
    from websockets.asyncio.server import serve as ws_serve, ServerConnection
    from websockets.http11 import Response
    from websockets.datastructures import Headers
except ImportError:
    print("Missing dependency: websockets\n  pip install websockets")
    raise SystemExit(1)

log = logging.getLogger("cdp-bridge")

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Missing dependency: playwright\n  pip install playwright")
    raise SystemExit(1)

EXTENSION_ID = "mmlmfjhmonkocbjadbfplnigmagldckm"
PROTOCOL_VERSION = 2

# ---------------------------------------------------------------------------
# Extension relay (V2 protocol)
# ---------------------------------------------------------------------------

class ExtensionRelay:
    """Manages the V2 WebSocket connection from the Chrome extension."""

    def __init__(self) -> None:
        self._ws: ServerConnection | None = None
        self._connected = asyncio.Event()
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._attached_tabs: dict[int, dict] = {}  # tabId -> {targetId, sessionId, title, url}
        self._cdp_clients: list[CDPClient] = []

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._connected.is_set()

    async def accept(self, ws: ServerConnection) -> None:
        log.info("Extension connected")
        self._ws = ws
        self._connected.set()
        try:
            async for raw in ws:
                msg = json.loads(raw)
                if "id" in msg and msg["id"] in self._pending:
                    fut = self._pending.pop(msg["id"])
                    if "error" in msg:
                        fut.set_exception(RuntimeError(msg["error"]))
                    else:
                        fut.set_result(msg.get("result"))
                elif msg.get("method") == "extension.initialized":
                    log.info("Extension initialized (V2)")
                elif msg.get("method") == "chrome.debugger.onEvent":
                    self._handle_debugger_event(msg["params"])
                elif msg.get("method") == "chrome.tabs.onCreated":
                    self._handle_tab_created(msg["params"])
                else:
                    log.info("Unknown message: %s", msg)
        except websockets.ConnectionClosed:
            log.info("Extension disconnected")
        finally:
            self._ws = None
            self._connected.clear()
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(RuntimeError("Extension disconnected"))
            self._pending.clear()

    async def send_command(self, method: str, params: Any = None) -> Any:
        if not self._ws:
            raise RuntimeError("Extension not connected")
        cmd_id = self._next_id
        self._next_id += 1
        msg = {"id": cmd_id, "method": method, "params": params or []}
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[cmd_id] = fut
        await self._ws.send(json.dumps(msg))
        return await asyncio.wait_for(fut, timeout=30)

    async def chrome_tabs_create(self, url: str) -> dict:
        """Create a new tab and return its info."""
        result = await self.send_command("chrome.tabs.create", [{"url": url}])
        return result

    async def chrome_debugger_attach(self, tab_id: int) -> dict:
        """Attach debugger to a tab. Returns target info."""
        result = await self.send_command("chrome.debugger.attach", [{"tabId": tab_id}, "1.3"])
        # After attach, get target info
        target = await self.send_command("chrome.debugger.sendCommand", [
            {"tabId": tab_id}, "Target.getTargetInfo", {}
        ])
        info = target.get("targetInfo", {})
        self._attached_tabs[tab_id] = {
            "targetId": info.get("targetId", f"tab-{tab_id}"),
            "tabId": tab_id,
            "title": info.get("title", ""),
            "url": info.get("url", ""),
        }
        return info

    async def chrome_debugger_detach(self, tab_id: int | None = None) -> None:
        """Detach debugger from a tab."""
        if not self._attached_tabs:
            return
        if tab_id is None:
            tab_id = list(self._attached_tabs.keys())[0]
        try:
            await self.send_command("chrome.debugger.detach", [{"tabId": tab_id}])
        except Exception:
            pass
        self._attached_tabs.pop(tab_id, None)

    async def chrome_debugger_send_command(self, tab_id: int, method: str, params: dict = None) -> Any:
        """Send a CDP command via the debugger."""
        return await self.send_command("chrome.debugger.sendCommand", [
            {"tabId": tab_id}, method, params or {}
        ])

    def _handle_debugger_event(self, params: list) -> None:
        """Forward chrome.debugger.onEvent to CDP clients."""
        if len(params) < 2:
            return
        source = params[0]  # {tabId, sessionId?}
        method = params[1]
        cdp_params = params[2] if len(params) > 2 else {}
        tab_id = source.get("tabId")
        if tab_id not in self._attached_tabs:
            return
        tab = self._attached_tabs[tab_id]
        event = {
            "method": method,
            "params": cdp_params,
            "sessionId": tab.get("sessionId", f"session-{tab_id}"),
        }
        raw = json.dumps(event)
        for client in list(self._cdp_clients):
            try:
                asyncio.ensure_future(client.ws.send(raw))
            except Exception:
                pass

    def _handle_tab_created(self, params: list) -> None:
        """Handle chrome.tabs.onCreated — notify CDP clients."""
        if not params:
            return
        tab = params[0]
        tab_id = tab.get("id")
        if not tab_id:
            return
        log.info("Tab created: id=%s url=%s", tab_id, tab.get("url", ""))


# ---------------------------------------------------------------------------
# CDP client connection
# ---------------------------------------------------------------------------

class CDPClient:
    """Handles a Playwright CDP client connection, translating to V2 chrome.* calls."""

    def __init__(self, ws: ServerConnection, relay: ExtensionRelay) -> None:
        self.ws = ws
        self.relay = relay
        self._tab_id: int | None = None
        self._target_id: str | None = None
        self._session_id: str | None = None
        self._context_id = "bridge-context"

    async def handle(self) -> None:
        relay = self.relay
        relay._cdp_clients.append(self)
        log.info("CDP client connected")
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                cmd_id = msg.get("id")
                method = msg.get("method", "")
                params = msg.get("params", {})
                session_id = msg.get("sessionId")

                try:
                    result = await self._handle_method(method, params, session_id)
                    resp = {"id": cmd_id, "result": result or {}}
                except Exception as e:
                    resp = {"id": cmd_id, "error": {"code": -32000, "message": str(e)}}

                if session_id:
                    resp["sessionId"] = session_id
                await self.ws.send(json.dumps(resp))
        except websockets.ConnectionClosed:
            log.info("CDP client disconnected")
        finally:
            if self in relay._cdp_clients:
                relay._cdp_clients.remove(self)
            if self._tab_id:
                await relay.chrome_debugger_detach(self._tab_id)

    async def _handle_method(self, method: str, params: dict, session_id: str | None) -> Any:
        relay = self.relay
        cdp_port = None  # Will be set from the server

        if not session_id:
            # Browser-level commands
            if method == "Browser.getVersion":
                return {
                    "protocolVersion": "1.3",
                    "product": "Chrome (V2 Bridge)",
                    "userAgent": "CDP-Bridge/2.0",
                }
            if method == "Browser.setDownloadBehavior":
                return {}
            if method == "Target.setAutoAttach":
                return await self._attach_tab()
            if method == "Target.getTargetInfo":
                # Return info for the CDP browser-level target
                return {"targetInfo": {"type": "browser", "targetId": "bridge-browser"}}
            if method == "Target.getTargets":
                targets = []
                for tid, t in relay._attached_tabs.items():
                    targets.append({
                        "targetId": t["targetId"],
                        "type": "page",
                        "title": t.get("title", ""),
                        "url": t.get("url", ""),
                        "attached": True,
                        "browserContextId": self._context_id,
                    })
                return {"targetInfos": targets}

        # Target-level commands (with sessionId)
        if method == "Target.createTarget":
            url = params.get("url", "about:blank")
            tab = await relay.chrome_tabs_create(url)
            tab_id = tab.get("id")
            if not tab_id:
                raise RuntimeError("Tab creation returned no id")
            await relay.chrome_debugger_attach(tab_id)
            self._tab_id = tab_id
            self._target_id = relay._attached_tabs[tab_id]["targetId"]
            self._session_id = f"session-{tab_id}"
            return {
                "targetId": self._target_id,
                "browserContextId": self._context_id,
                "sessionId": self._session_id,
            }

        # Forward all other CDP commands via chrome.debugger.sendCommand
        if not self._tab_id:
            raise RuntimeError("No tab attached")
        result = await relay.chrome_debugger_send_command(self._tab_id, method, params)
        return result

    async def _attach_tab(self) -> dict:
        relay = self.relay
        # Detach any old session
        if self._tab_id:
            await relay.chrome_debugger_detach(self._tab_id)

        # Create a new tab and attach debugger
        tab = await relay.chrome_tabs_create("about:blank")
        tab_id = tab.get("id")
        if not tab_id:
            raise RuntimeError("Failed to create tab")
        info = await relay.chrome_debugger_attach(tab_id)
        self._tab_id = tab_id
        self._target_id = relay._attached_tabs[tab_id]["targetId"]
        self._session_id = f"session-{tab_id}"

        # Synthesize Target.attachedToTarget event
        event = {
            "method": "Target.attachedToTarget",
            "params": {
                "sessionId": self._session_id,
                "targetInfo": {
                    "type": "page",
                    "targetId": self._target_id,
                    "title": info.get("title", ""),
                    "url": info.get("url", ""),
                    "attached": True,
                    "browserContextId": self._context_id,
                },
                "waitingForDebugger": False,
            },
        }
        await self.ws.send(json.dumps(event))
        return {}


# ---------------------------------------------------------------------------
# Bridge server
# ---------------------------------------------------------------------------

class CDPBridge:
    def __init__(self, cdp_port: int = 9222, extension_port: int = 0) -> None:
        self.cdp_port = cdp_port
        self.extension_port = extension_port
        self.relay = ExtensionRelay()
        self._uuid = uuid.uuid4().hex[:12]
        self._extension_path = f"/extension/{self._uuid}"

    async def start(self, open_browser: bool = True, token: str | None = None) -> None:
        # Extension-facing server
        ext_server = await ws_serve(
            self._handle_extension, "0.0.0.0", self.extension_port,
            process_request=self._ext_process_request,
        )
        ext_addr = ext_server.sockets[0].getsockname()
        self.extension_port = ext_addr[1]
        ext_url = f"ws://127.0.0.1:{self.extension_port}{self._extension_path}"
        log.info("Extension endpoint: %s", ext_url)

        # CDP-facing server
        cdp_server = await ws_serve(
            self._handle_cdp, "0.0.0.0", self.cdp_port,
            process_request=self._cdp_process_request,
        )
        cdp_addr = cdp_server.sockets[0].getsockname()
        log.info("CDP endpoint: ws://127.0.0.1:%d", cdp_addr[1])

        # Open connect page with protocolVersion=2
        if open_browser:
            connect_url = (
                f"chrome-extension://{EXTENSION_ID}/connect.html"
                f"?mcpRelayUrl={ext_url}&protocolVersion={PROTOCOL_VERSION}"
            )
            if token:
                connect_url += f"&token={token}"
            print(f"\n  CDP Bridge (V2) running on ws://127.0.0.1:{cdp_addr[1]}")
            print(f"  Extension relay on port {self.extension_port}")
            print(f"  Opening extension connect page...")
            print(f"  {connect_url}\n")
            ps_cmd = f"Start-Process chrome '{connect_url}'"
            subprocess.run(["powershell.exe", "-Command", ps_cmd], capture_output=True)

        print("  Waiting for extension connection...")
        try:
            await asyncio.wait_for(self.relay._connected.wait(), timeout=60)
        except asyncio.TimeoutError:
            print("  ERROR: Extension did not connect within 60 seconds")
            return

        print("  Extension connected! Bridge is ready.\n")
        print(f"  Playwright: p.chromium.connect_over_cdp('ws://127.0.0.1:{cdp_addr[1]}')")
        print("  Internal Playwright + TCP command server starting...")

        # Connect internal Playwright to own CDP endpoint
        self._pw = await async_playwright().start()
        self._pw_browser = await self._pw.chromium.connect_over_cdp(
            f"ws://127.0.0.1:{cdp_addr[1]}"
        )
        self._pw_ctx = self._pw_browser.contexts[0]
        self._pw_page = self._pw_ctx.pages[0]
        cmd_port = cdp_addr[1] + 1
        print(f"  Internal Playwright connected. Command port: {cmd_port}")
        print("  Send: python3 -c \"import socket;s=socket.socket();s.connect(('127.0.0.1',{}));s.sendall(b'<cmd>\\\\n');print(s.recv(8192).decode());s.close()\"".format(cmd_port))
        print("  Response ends with ---CMD-END---\n")

        asyncio.create_task(self._command_server(cmd_port))
        await asyncio.Future()

    async def _command_server(self, port: int):
        """TCP server: one line in, async eval with page/ctx/browser scope, result out."""
        import traceback
        scope = {
            "page": self._pw_page,
            "ctx": self._pw_ctx,
            "browser": self._pw_browser,
            "asyncio": asyncio,
            "json": json,
        }

        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            line = (await reader.readline()).decode().strip()
            if not line or line.startswith("#"):
                writer.write(b"---CMD-END---\n")
                writer.close()
                return
            try:
                ns = {}
                exec(f"async def _f():\n    return {line}", scope, ns)
                result = await ns["_f"]()
                if result is not None:
                    writer.write(f"{result}\n".encode())
            except Exception as e:
                writer.write(f"ERROR: {e}\n".encode())
                traceback.print_exc()
            writer.write(b"---CMD-END---\n")
            await writer.drain()
            writer.close()

        await asyncio.start_server(handle, "127.0.0.1", port)

    async def _handle_extension(self, ws: ServerConnection) -> None:
        await self.relay.accept(ws)

    async def _handle_cdp(self, ws: ServerConnection) -> None:
        if not self.relay.connected:
            print("  Waiting for extension to connect first...")
            await asyncio.wait_for(self.relay._connected.wait(), timeout=60)
        client = CDPClient(ws, self.relay)
        await client.handle()

    async def _ext_process_request(self, connection, request):
        if request.path != self._extension_path:
            return connection.respond(404, "Not found")
        return None

    def _json_response(self, data: Any) -> Response:
        body = json.dumps(data).encode()
        headers = Headers({"Content-Type": "application/json", "Content-Length": str(len(body))})
        return Response(200, "OK", headers, body)

    async def _cdp_process_request(self, connection, request):
        path = request.path
        if path in ("/json/version", "/json/version/"):
            return self._json_response({
                "Browser": "Chrome (V2 Bridge)",
                "Protocol-Version": "1.3",
                "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.cdp_port}",
            })
        if path in ("/json", "/json/", "/json/list", "/json/list/"):
            entries = []
            for tid, t in self.relay._attached_tabs.items():
                entries.append({
                    "id": t["targetId"],
                    "title": t.get("title", ""),
                    "type": "page",
                    "url": t.get("url", ""),
                    "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.cdp_port}",
                })
            if not entries:
                entries = [{"id": "bridge-tab", "title": "CDP Bridge", "type": "page",
                            "url": "", "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.cdp_port}"}]
            return self._json_response(entries)
        upgrade = request.headers.get("upgrade", "").lower()
        if upgrade == "websocket":
            return None
        body = b"Not found"
        return Response(404, "Not Found", Headers({"Content-Length": str(len(body))}), body)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Chrome CDP Bridge V2")
    parser.add_argument("--port", type=int, default=9222, help="CDP port (default: 9222)")
    parser.add_argument("--extension-port", type=int, default=0, help="Extension relay port (default: random)")
    parser.add_argument("--token", default=None, help="Extension auth token")
    parser.add_argument("--no-open", action="store_true", help="Don't open extension connect page")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(name)s] %(message)s")

    bridge = CDPBridge(cdp_port=args.port, extension_port=args.extension_port)
    try:
        asyncio.run(bridge.start(open_browser=not args.no_open, token=args.token))
    except KeyboardInterrupt:
        print("\nBridge stopped.")

if __name__ == "__main__":
    main()
