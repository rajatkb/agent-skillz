#!/usr/bin/env python3
"""
RuTor Game Search — search rutor.is for games, pick one, open magnet in qBittorrent.

Usage:
  python3 rutor-search.py "cyberpunk 2077"
  python3 rutor-search.py "elden ring" --filter insaneramzes

If no query given, prompts interactively.
"""

import sys
import re
import html as html_mod
import subprocess
import os
import textwrap
from urllib.parse import quote

RUTOR_URL = "https://rutor.info/search/{page}/{cat}/{method}{search_in}0/{sort}/{query}"

def fetch_results(query: str, category: int = 0, filter_text: str = None) -> list:
    """Search rutor.is and return list of result dicts."""
    # URL-encode query, replace & with AND as rutor expects
    encoded = query.replace("&", "AND")
    safe_query = quote(encoded, safe="")
    url = RUTOR_URL.format(page=0, cat=category, method=0, search_in=0, sort=0, query=safe_query)

    result = subprocess.run(
        [
            "curl",
            "-sL",
            "--max-time", "15",
            url,
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ],
        capture_output=True,
        timeout=20,
    )
    html = result.stdout.decode("utf-8", errors="replace")

    results = []
    # Each result row is <tr class="gai"> or <tr class="tum">
    pattern = re.compile(r'<tr class="(?:gai|tum)">(.*?)</tr>', re.DOTALL)

    for row in pattern.findall(html):
        # Date
        date_m = re.search(r"<td[^>]*>\s*(.*?)\s*</td>", row)
        date_str = html_mod.unescape(date_m.group(1).strip()) if date_m else ""

        # Magnet
        magnet_m = re.search(r'href="(magnet:\?[^"]+)"', row)
        magnet = magnet_m.group(1) if magnet_m else ""

        # Title (the game name link)
        title_m = re.search(r'href="/torrent/\d+/[^"]*">(.*?)</a>', row)
        title = html_mod.unescape(title_m.group(1).strip()) if title_m else ""

        # Size
        size_m = re.search(
            r"<td[^>]*>\s*([\d.]+)\s*(?:&nbsp;)?\s*(GB|MB|KB)\s*</td>", row
        )
        size = ""
        if size_m:
            size = f"{size_m.group(1)} {size_m.group(2)}"

        # Seeders
        seeds_m = re.search(r"arrowup.*?>\s*(\d+)", row)
        seeds = int(seeds_m.group(1)) if seeds_m else 0

        if not magnet:
            continue

        item = {
            "title": title,
            "date": date_str,
            "size": size,
            "seeds": seeds,
            "magnet": magnet,
        }

        # Optional filter by repacker name
        if filter_text:
            if filter_text.lower() not in title.lower():
                continue

        results.append(item)

    # Sort by seeders descending (most popular first)
    results.sort(key=lambda r: r["seeds"], reverse=True)
    return results


def open_magnet(magnet: str):
    """Open a magnet link in Windows default handler (qBittorrent)."""
    # Use cmd.exe /c start from WSL — Windows handles the magnet:// protocol association
    proc = subprocess.run(
        ["cmd.exe", "/c", "start", "", magnet],
        capture_output=True,
        timeout=10,
    )
    if proc.returncode != 0:
        # Fallback: try explorer.exe
        subprocess.run(["explorer.exe", magnet], timeout=10)


def print_results(results: list):
    """Display results with index numbers."""
    try:
        width = os.get_terminal_size().columns
    except (ValueError, OSError):
        width = 80

    if not results:
        print("No results found.")
        return

    print(f"\n{'='*width}")
    print(f"  Found {len(results)} results")
    print(f"{'='*width}\n")

    for i, r in enumerate(results, 1):
        # Wrap title if needed
        title = r["title"]
        title_wrapped = textwrap.fill(
            title, width=width - 12, subsequent_indent="  "
        )

        print(f"  [{i:2d}] {title_wrapped}")
        print(f"       Size: {r['size']:>10}  |  Seeds: {r['seeds']:>3}  |  {r['date']}")
        print()


def main():
    # Get query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Search for game: ").strip()

    if not query:
        print("No query given.")
        return

    # Check for --filter flag
    filter_text = None
    if "--filter" in sys.argv:
        idx = sys.argv.index("--filter")
        if idx + 1 < len(sys.argv):
            filter_text = sys.argv[idx + 1]

    print(f"Searching rutor.is for: {query}")
    if filter_text:
        print(f"Filtering by: {filter_text}")

    try:
        results = fetch_results(query, filter_text=filter_text)
    except Exception as e:
        print(f"Error searching rutor.is: {e}")
        return

    print_results(results)

    if not results:
        return

    # Let user pick
    while True:
        choice = input(f"Pick a result (1-{len(results)}) or q to quit: ").strip()
        if choice.lower() in ("q", ""):
            print("Bye.")
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                break
        except ValueError:
            pass
        print(f"Enter a number between 1 and {len(results)} or q.")

    chosen = results[idx]
    print(f"\nOpening in qBittorrent: {chosen['title']}")
    print(f"Magnet: {chosen['magnet'][:80]}...")

    try:
        open_magnet(chosen["magnet"])
        print("Done! Check qBittorrent.")
    except Exception as e:
        print(f"Failed to open magnet: {e}")


if __name__ == "__main__":
    main()
