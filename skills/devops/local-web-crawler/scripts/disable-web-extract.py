#!/usr/bin/env python3
"""Disable the broken web_extract tool by patching toolsets.py.

Usage: python3 /home/rajat-g14/.hermes/scripts/disable-web-extract.py

Run after every `pip install --upgrade hermes-agent` since upgrades
overwrite the patched file.
"""

import sys

path = "/home/rajat-g14/.asdf/installs/python/3.11.0/lib/python3.11/site-packages/toolsets.py"

try:
    with open(path) as f:
        content = f.read()
except FileNotFoundError:
    print(f"toolsets.py not found at {path}", file=sys.stderr)
    print("Try: python3 -c \"from toolsets import TOOLSETS; print(TOOLSETS['web'])\"", file=sys.stderr)
    sys.exit(1)

changes = 0

# Remove from _HERMES_CORE_TOOLS
old = '"web_search", "web_extract",'
if old in content:
    content = content.replace(old, '"web_search",')
    changes += 1

# Remove from TOOLSETS["web"]
old = '"tools": ["web_search", "web_extract"],'
if old in content:
    content = content.replace(old, '"tools": ["web_search"],')
    changes += 1

if changes:
    with open(path, 'w') as f:
        f.write(content)
    print(f"Patched {path} — {changes} change(s) applied.")
    print('web_extract removed from _HERMES_CORE_TOOLS and TOOLSETS["web"]')
else:
    print("No changes needed — web_extract already removed or not found.")
    sys.exit(0)
