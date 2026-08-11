"""
Chrome CDP Bridge — connect any CDP client (browser-use, Puppeteer, Playwright, etc.)
to an existing Chrome browser via the Playwright MCP Bridge extension.

No --remote-debugging-port needed. The extension uses Chrome's internal
chrome.debugger API to attach to any tab.

Architecture:
  ┌──────────────┐  CDP-over-WS   ┌───────────┐  relay protocol  ┌───────────────┐
  │  browser-use │ ◄────────────► │  bridge   │ ◄──────────────► │  Chrome ext.  │
  │  / any CDP   │   :9222        │  server   │   :random        │  (debugger)   │
  └──────────────┘                └───────────┘                  └───────────────┘

Protocol spoken with the extension (same as Playwright MCP):
  Server → Extension:  { id, method: "attachToTab"|"forwardCDPCommand", params }
  Extension → Server:  { id, result|error }  (responses)
                       { method: "forwardCDPEvent", params: { method, sessionId, params } }

This bridge exposes a standard CDP WebSocket endpoint so any tool that speaks CDP
can connect — just point it at ws://127.0.0.1:9222.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
import webbrowser
from typing import Any

try:
    import websockets
    from websockets.asyncio.server import serve as ws_serve, ServerConnection
    from websockets.http11 import Response
    from websockets.datastructures import Headers
except ImportError:
    print("Missing dependency: websockets")
    print("  pip install websockets")
    raise SystemExit(1)

log = logging.getLogger("cdp-bridge")

# ---------------------------------------------------------------------------
# Extension relay connection (extension connects here)
# ---------------------------------------------------------------------------

class ExtensionRelay:
    """Manages the WebSocket connection from the Chrome extension."""

    def __init__(self) -> None:
        self._ws: ServerConnection | None = None
        self._connected = asyncio.Event()
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._target_info: dict | None = None
        self._session_id: str | None = None
        # CDP clients waiting for events
        self._cdp_clients: list[CDPClient] = []

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._connected.is_set()

    async def accept(self, ws: ServerConnection) -> None:
        """Called when the extension connects."""
        log.info("Extension connected")
        self._ws = ws
        self._connected.set()
        try:
            async for raw in ws:
                msg = json.loads(raw)
                if "id" in msg and msg["id"] in self._pending:
                    # Response to a command we sent
                    fut = self._pending.pop(msg["id"])
                    if "error" in msg:
                        fut.set_exception(RuntimeError(msg["error"]))
                    else:
                        fut.set_result(msg.get("result"))
                elif msg.get("method") == "forwardCDPEvent":
                    self._dispatch_event(msg["params"])
                else:
                    log.warning("Unknown message from extension: %s", msg)
        except websockets.ConnectionClosed:
            log.info("Extension disconnected")
        finally:
            self._ws = None
            self._connected.clear()
            # Fail any pending commands
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(RuntimeError("Extension disconnected"))
            self._pending.clear()

    async def send_command(self, method: str, params: dict | None = None) -> Any:
        """Send a command to the extension and wait for the response."""
        if not self._ws:
            raise RuntimeError("Extension not connected")
        cmd_id = self._next_id
        self._next_id += 1
        msg = {"id": cmd_id, "method": method, "params": params or {}}
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[cmd_id] = fut
        await self._ws.send(json.dumps(msg))
        return await asyncio.wait_for(fut, timeout=30)

    async def attach_to_tab(self) -> dict:
        """Attach the debugger to the selected tab."""
        result = await self.send_command("attachToTab")
        self._target_info = result.get("targetInfo", {})
        self._session_id = f"pw-tab-1"
        return result

    async def detach_from_tab(self) -> None:
        """Detach the debugger from the current tab."""
        try:
            await self.send_command("detach")
        except Exception:
            pass
        self._target_info = None

    async def forward_cdp(self, method: str, params: dict | None = None,
                          session_id: str | None = None) -> Any:
        """Forward a CDP command through the extension."""
        return await self.send_command("forwardCDPCommand", {
            "method": method,
            "params": params or {},
            "sessionId": session_id if session_id != self._session_id else None,
        })

    def _dispatch_event(self, params: dict) -> None:
        """Forward a CDP event from the extension to all CDP clients."""
        cdp_method = params.get("method", "")
        cdp_params = params.get("params", {})
        session_id = params.get("sessionId")
        # Map to the session ID we gave the CDP client
        effective_session = session_id or self._session_id
        event = {
            "method": cdp_method,
            "params": cdp_params,
        }
        if effective_session:
            event["sessionId"] = effective_session
        raw = json.dumps(event)
        for client in list(self._cdp_clients):
            try:
                asyncio.ensure_future(client.ws.send(raw))
            except Exception:
                pass


# ---------------------------------------------------------------------------
# CDP client connection (browser-use / puppeteer / etc. connect here)
# ---------------------------------------------------------------------------

class CDPClient:
    """Handles a CDP WebSocket client connection."""

    def __init__(self, ws: ServerConnection, relay: ExtensionRelay) -> None:
        self.ws = ws
        self.relay = relay

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
            # Detach so next CDP client can re-attach
            try:
                asyncio.ensure_future(relay.detach_from_tab())
            except Exception:
                pass

    async def _handle_method(self, method: str, params: dict,
                             session_id: str | None) -> Any:
        relay = self.relay

        # Intercept certain top-level CDP methods (no sessionId = browser-level)
        if not session_id:
            if method == "Browser.getVersion":
                return {
                    "protocolVersion": "1.3",
                    "product": "Chrome (via CDP Bridge)",
                    "userAgent": "CDP-Bridge/1.0",
                }
            if method == "Browser.setDownloadBehavior":
                return {}
            if method == "Target.setAutoAttach":
                # Attach to the tab via extension and synthesize the event
                result = await relay.attach_to_tab()
                target_info = result.get("targetInfo", {})
                # Send Target.attachedToTarget event to client
                event = {
                    "method": "Target.attachedToTarget",
                    "params": {
                        "sessionId": relay._session_id,
                        "targetInfo": {
                            "type": "page",
                            "targetId": target_info.get("targetId", "bridge-tab"),
                            "title": target_info.get("title", ""),
                            "url": target_info.get("url", ""),
                            "attached": True,
                            "browserContextId": "bridge-context",
                        },
                        "waitingForDebugger": False,
                    },
                }
                await self.ws.send(json.dumps(event))
                return {}
            if method == "Target.getTargetInfo":
                ti = relay._target_info or {}
                return {"targetInfo": ti}
            if method == "Target.getTargets":
                ti = relay._target_info or {}
                return {"targetInfos": [ti] if ti else []}

        # Everything else: forward through the extension
        return await relay.forward_cdp(method, params, session_id)


# ---------------------------------------------------------------------------
# Bridge server
# ---------------------------------------------------------------------------

class CDPBridge:
    """
    Main bridge server.

    Runs two WebSocket endpoints:
      - /extension/<uuid>  — the Chrome extension connects here
      - /cdp/<uuid> or /   — CDP clients connect here (browser-use, etc.)

    Also serves /json/version and /json/list for CDP discovery.
    """

    def __init__(self, cdp_port: int = 9222, extension_port: int = 0) -> None:
        self.cdp_port = cdp_port
        self.extension_port = extension_port
        self.relay = ExtensionRelay()
        self._uuid = uuid.uuid4().hex[:12]
        self._extension_path = f"/extension/{self._uuid}"

    async def start(self, open_browser: bool = True, token: str | None = None) -> None:
        # Start the extension-facing WebSocket server
        ext_server = await ws_serve(
            self._handle_extension,
            "0.0.0.0",
            self.extension_port,
            process_request=self._ext_process_request,
        )
        ext_addr = ext_server.sockets[0].getsockname()
        self.extension_port = ext_addr[1]
        ext_url = f"ws://127.0.0.1:{self.extension_port}{self._extension_path}"
        log.info("Extension endpoint: %s", ext_url)

        # Start the CDP-facing WebSocket server
        cdp_server = await ws_serve(
            self._handle_cdp,
            "0.0.0.0",
            self.cdp_port,
            process_request=self._cdp_process_request,
        )
        cdp_addr = cdp_server.sockets[0].getsockname()
        log.info("CDP endpoint: ws://127.0.0.1:%d", cdp_addr[1])

        # Open the extension's connect page
        if open_browser:
            connect_url = (
                f"chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/connect.html"
                f"?mcpRelayUrl={ext_url}"
            )
            if token:
                connect_url += f"&token={token}"
            print(f"\n  CDP Bridge running on ws://127.0.0.1:{cdp_addr[1]}")
            print(f"\n  Extension relay on port {self.extension_port}")
            print(f"\n  Opening Chrome extension tab selector...")
            print(f"  (If it doesn't open, navigate to this URL in Chrome:)")
            print(f"  {connect_url}\n")
            webbrowser.open(connect_url)

        # Wait for extension to connect
        print("  Waiting for extension connection...")
        try:
            await asyncio.wait_for(self.relay._connected.wait(), timeout=60)
        except asyncio.TimeoutError:
            print("  ERROR: Extension did not connect within 60 seconds")
            return

        print("  Extension connected! Bridge is ready.")
        print(f"\n  Connect browser-use or any CDP client to:")
        print(f"    ws://127.0.0.1:{cdp_addr[1]}")
        print(f"\n  Example:")
        print(f'    browser-use --cdp-url ws://127.0.0.1:{cdp_addr[1]} state')
        print(f"\n  Press Ctrl+C to stop.\n")

        # Keep running
        await asyncio.Future()

    async def _handle_extension(self, ws: ServerConnection) -> None:
        """Handle WebSocket connection from the Chrome extension."""
        await self.relay.accept(ws)

    async def _handle_cdp(self, ws: ServerConnection) -> None:
        """Handle WebSocket connection from a CDP client."""
        if not self.relay.connected:
            print("  Waiting for extension to connect first...")
            await asyncio.wait_for(self.relay._connected.wait(), timeout=60)
        client = CDPClient(ws, self.relay)
        await client.handle()

    async def _ext_process_request(self, connection, request):
        """Only allow connections to the extension path."""
        if request.path != self._extension_path:
            return connection.respond(404, "Not found")
        return None

    def _json_response(self, data: Any) -> Response:
        """Create an HTTP 200 JSON response."""
        body = json.dumps(data).encode()
        headers = Headers({"Content-Type": "application/json", "Content-Length": str(len(body))})
        return Response(200, "OK", headers, body)

    async def _cdp_process_request(self, connection, request):
        """Handle CDP HTTP discovery endpoints and WebSocket upgrades."""
        path = request.path

        if path in ("/json/version", "/json/version/"):
            return self._json_response({
                "Browser": "Chrome (via CDP Bridge)",
                "Protocol-Version": "1.3",
                "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.cdp_port}",
            })

        if path in ("/json", "/json/", "/json/list", "/json/list/"):
            ti = self.relay._target_info or {}
            target_id = ti.get("targetId", "bridge-tab")
            entry = {
                "id": target_id,
                "title": ti.get("title", "CDP Bridge Tab"),
                "type": "page",
                "url": ti.get("url", ""),
                "webSocketDebuggerUrl": f"ws://127.0.0.1:{self.cdp_port}",
            }
            return self._json_response([entry])

        # WebSocket upgrade — let it through
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Chrome CDP Bridge — connect CDP clients to Chrome via the Playwright MCP Bridge extension",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start on default port 9222
  %(prog)s --port 9333              # Use a different port
  %(prog)s --token MY_SECRET        # Auto-approve extension connection

Then connect browser-use:
  browser-use --cdp-url ws://127.0.0.1:9222 state
        """,
    )
    parser.add_argument("--port", type=int, default=9222,
                        help="CDP port for clients to connect to (default: 9222)")
    parser.add_argument("--extension-port", type=int, default=0,
                        help="Port for the extension relay (default: random)")
    parser.add_argument("--token", default=None,
                        help="Extension auth token for auto-approve (from extension settings)")
    parser.add_argument("--no-open", action="store_true",
                        help="Don't auto-open the extension tab selector")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(name)s] %(message)s")

    bridge = CDPBridge(cdp_port=args.port, extension_port=args.extension_port)

    try:
        asyncio.run(bridge.start(
            open_browser=not args.no_open,
            token=args.token,
        ))
    except KeyboardInterrupt:
        print("\nBridge stopped.")


if __name__ == "__main__":
    main()
