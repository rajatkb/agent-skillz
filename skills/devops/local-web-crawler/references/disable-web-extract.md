# Disable web_extract tool

## Why

The `web_extract` tool on this system is broken because the `web.extract_backend` is set to `ddgs` (DuckDuckGo), which is a search-only backend and does not support URL content extraction. The tool raises `DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content` on every call.

## The fix

Patch `toolsets.py` to remove `"web_extract"` from both `_HERMES_CORE_TOOLS` and `TOOLSETS["web"]`:

```python
# disable-web-extract.py
import sys

path = "/home/<user>/.asdf/installs/python/3.11.0/lib/python3.11/site-packages/toolsets.py"

try:
    with open(path) as f:
        content = f.read()

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
    else:
        print("No changes needed — web_extract already removed.")
        sys.exit(0)

except FileNotFoundError:
    print(f"toolsets.py not found at {path}")
    print("Find it with: python3 -c \"from toolsets import TOOLSETS; print(TOOLSETS['web'])\"")
    sys.exit(1)
```

## Re-apply after upgrades

Hermes upgrades (`pip install --upgrade hermes-agent`) overwrite `toolsets.py`. Re-run this after every upgrade.

```bash
python3 ~/.hermes/scripts/disable-web-extract.py
```

## Verification

After patching, verify web_extract is gone:

```python
from toolsets import resolve_toolset
print("web toolset:", resolve_toolset("web"))
print("hermes-cli core:" , [t for t in resolve_toolset("hermes-cli") if "extract" in t])
```

Should show only `web_search` in the web toolset and empty list for hermes-cli core.

## Alternative: use search toolset

Instead of patching, you can use the `search` toolset in config.yaml which only has `web_search`:

```yaml
toolsets:
  - hermes-cli
  - search    # instead of "web" — only web_search, no web_extract
  - browser
  - npu
```

This avoids modifying installed files but also loses `web_extract` from `hermes-cli` (which still includes it via `_HERMES_CORE_TOOLS`).
