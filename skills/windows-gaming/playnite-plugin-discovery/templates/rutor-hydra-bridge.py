#!/usr/bin/env python3
"""
RuTor → qBittorrent Bridge

Standalone tool: searches rutor.is for a game, sends the magnet to qBittorrent.

Usage:
  python rutor-hydra-bridge.py "Cyberpunk 2077"
  python rutor-hydra-bridge.py "Cyberpunk 2077" --repacker InsaneRamZes
  python rutor-hydra-bridge.py "Cyberpunk 2077" --list          # list matches only

Requires qBittorrent running with Web UI enabled (Tools → Options → Web UI).
"""

import urllib.request, urllib.parse, urllib.error
import re, json, sys, os

QB_HOST = os.environ.get("QB_HOST", "localhost")
QB_PORT = int(os.environ.get("QB_PORT", "8080"))
QB_USER = os.environ.get("QB_USER", "admin")
QB_PASS = os.environ.get("QB_PASS", "admin")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def search_rutor(query: str, category: int = 0) -> list[dict]:
    """Search rutor.is, return list of {title, magnet, size, seeders}."""
    encoded = urllib.parse.quote(query)
    url = f"https://rutor.is/search/0/{category}/000/0/{encoded}"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    results = []
    for row in re.findall(r'<tr class="(?:gai|tum)">(.*?)</tr>', html, re.DOTALL):
        magnet_m = re.search(r'href="(magnet:\?[^"]+)"', row)
        title_m = re.search(r'href="/torrent/\d+[^"]*">(.+?)</a>', row)
        size_m = re.search(r"<td[^>]*>\s*([\d.]+\s*(?:GB|MB|KB))", row)
        seed_m = re.search(r'class="green"[^>]*>.*?(\d+)', row)

        if magnet_m and title_m:
            results.append({
                "title": title_m.group(1).strip(),
                "magnet": magnet_m.group(1),
                "size": size_m.group(1) if size_m else "N/A",
                "seeders": int(seed_m.group(1)) if seed_m else 0,
            })
    return results


def send_to_qbittorrent(magnet: str, save_path: str = "") -> bool:
    """Add a magnet link to qBittorrent via Web API."""
    import base64
    # Login
    login_data = urllib.parse.urlencode({"username": QB_USER, "password": QB_PASS}).encode()
    login_req = urllib.request.Request(
        f"http://{QB_HOST}:{QB_PORT}/api/v2/auth/login",
        data=login_data,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(login_req, timeout=10) as resp:
            cookie = resp.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as e:
        print(f"qBittorrent login failed: {e}")
        return False

    # Add torrent
    params = {"urls": magnet}
    if save_path:
        params["savepath"] = save_path
    add_data = urllib.parse.urlencode(params).encode()
    add_req = urllib.request.Request(
        f"http://{QB_HOST}:{QB_PORT}/api/v2/torrents/add",
        data=add_data,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(add_req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"Failed to add torrent: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Search rutor.is and send magnet to qBittorrent")
    parser.add_argument("query", help="Game name to search for")
    parser.add_argument("--repacker", "-r", help="Filter results by repacker name (e.g. InsaneRamZes, FitGirl)")
    parser.add_argument("--category", "-c", type=int, default=0, help="Category (0=all, 8=games)")
    parser.add_argument("--list", "-l", action="store_true", help="List matches without downloading")
    parser.add_argument("--pick", "-p", type=int, default=0, help="Pick result N from the list (1-indexed, 0=auto-pick best seeded)")
    parser.add_argument("--save-path", "-s", help="qBittorrent download directory override")
    args = parser.parse_args()

    results = search_rutor(args.query, args.category)
    if not results:
        print("No results found.")
        sys.exit(1)

    # Filter by repacker if specified
    if args.repacker:
        filtered = [r for r in results if args.repacker.lower() in r["title"].lower()]
        if not filtered:
            print(f"No results matching repacker '{args.repacker}'. Showing all.")
        else:
            results = filtered

    # Sort by seeders descending
    results.sort(key=lambda r: r["seeders"], reverse=True)

    if args.list or args.pick == 0 and len(results) > 1:
        print(f"\nFound {len(results)} result(s):\n")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r['title']}")
            print(f"      Size: {r['size']}  Seeders: {r['seeders']}")
            print()

    if args.list:
        return

    # Pick which result to download
    pick = args.pick
    if pick == 0:
        pick = 1  # Best seeded
        if len(results) > 1:
            try:
                pick = int(input(f"Pick 1-{len(results)} (default 1, best seeded): ") or "1")
            except (ValueError, EOFError):
                pick = 1

    pick = max(1, min(pick, len(results)))
    chosen = results[pick - 1]

    print(f"\nSending to qBittorrent: {chosen['title']}")
    print(f"  Size: {chosen['size']}  Seeders: {chosen['seeders']}")
    success = send_to_qbittorrent(chosen["magnet"], args.save_path or "")
    if success:
        print("✓ Magnet sent to qBittorrent")
    else:
        print("✗ Failed to send to qBittorrent. Check credentials and Web UI status.")
        sys.exit(1)


if __name__ == "__main__":
    main()
