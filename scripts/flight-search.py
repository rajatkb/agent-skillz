#!/usr/bin/env python3
"""One-shot flight search via Playwright MCP Bridge extension."""
import asyncio, json, subprocess, sys, time, urllib.request
import websockets

BRIDGE_PORT = 9333
TOKEN = "f1V-hII_CQ6np8KyrhxlVXW9re1nl_mCeDcG8VeXOSM"
EXTENSION_ID = "mmlmfjhmonkocbjadbfplnigmagldckm"

async def run():
    # 1. Start bridge.py as subprocess
    bridge = await asyncio.create_subprocess_exec(
        sys.executable, "-u", f"{os.environ['HOME']}/.hermes/scripts/cdp-bridge.py",
        "--port", str(BRIDGE_PORT), "--token", TOKEN, "--no-open",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    
    # 2. Wait for 'Waiting for extension connection' in output
    ext_url = None
    async for line in bridge.stdout:
        line = line.decode().strip()
        print(f"[bridge] {line}")
        if "Extension endpoint:" in line:
            ext_url = line.split("Extension endpoint: ")[1]
        if "Waiting for extension connection..." in line:
            break
    
    if not ext_url:
        print("ERROR: bridge didn't start properly")
        bridge.kill()
        return
    
    # 3. Open extension connect page in Chrome via PowerShell
    connect_url = (
        f"chrome-extension://{EXTENSION_ID}/connect.html"
        f"?mcpRelayUrl={ext_url}&token={TOKEN}"
    )
    subprocess.run(["powershell.exe", "-Command",
        f"Start-Process chrome -ArgumentList '{connect_url}'"],
        capture_output=True)
    
    # 4. Wait for extension to connect
    await asyncio.sleep(3)
    print("Extension should be connected now")
    
    # 5. Connect Playwright and do the flight search
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"ws://127.0.0.1:{BRIDGE_PORT}")
        page = browser.contexts[0].pages[0]
        
        # Navigate to Amazon flights
        page.goto("https://www.amazon.in/flights")
        page.wait_for_load_state()
        print(f"\n=== Page: {page.evaluate('document.title')} ===")
        
        # Read page content
        text = page.evaluate('document.body.innerText')
        print(text[:2000])
    
    bridge.kill()

if __name__ == "__main__":
    import os
    asyncio.run(run())
