---
name: python-venv-hygiene
description: Python environment topology on this machine — which interpreter/venv to use for what, the PYTHONPATH leak from the Hermes runtime into every venv, and safe pip install patterns. Load BEFORE any pip install, or when diagnosing "why does this venv see packages it doesn't own".
---

# Python Venv Hygiene (this machine)

## Environment map

| Interpreter | Role | Rule |
|---|---|---|
| `/home/rajat-g14/.asdf/installs/python/3.11.0` | **Hermes runtime** — TUI + gateway run from its site-packages | **NEVER pip install here**; polluting it can break Hermes itself |
| `/usr/bin/python3` | System global | Avoid; user explicitly doesn't want it polluted |

**No persistent venvs on this machine** (ml + agent both deleted Aug 2026 at user's request). Any package need is met with a **throwaway venv in /tmp** (see safe install pattern below).

## THE critical quirk: PYTHONPATH leak

The Hermes TUI process exports `PYTHONPATH=/home/rajat-g14/.asdf/installs/python/3.11.0/lib/python3.11/site-packages` into every child shell (it lives in the Hermes process env, **not** in ~/.zshrc — verify with `cat /proc/$$/environ | tr '\0' '\n' | grep PYTHON`).

Consequences:
- Every venv can `import` the entire Hermes runtime's packages, even with `include-system-site-packages = false` in pyvenv.cfg.
- `pip show <pkg>` / `pip list` inside a venv will list runtime packages at the asdf path (e.g. crawl4ai "appears" in the ml venv but is actually installed in the runtime). PYTHONPATH precedes site-packages in sys.path, so the runtime copy wins on import.
- Bare `python3` / `pip` on PATH resolves to the asdf interpreter → `pip install` with those pollutes the Hermes runtime.

## Safe install pattern

```bash
# Throwaway venv in /tmp — zero footprint on any permanent environment
python3 -m venv /tmp/pyenv && env -u PYTHONPATH /tmp/pyenv/bin/pip install <pkg>

# Verify import resolution uses the venv copy
env -u PYTHONPATH /tmp/pyenv/bin/python -c \
  "import sys, <pkg>; print(sys.executable); print(<pkg>.__file__)"
```

Expected: `sys.executable` = /tmp venv python, `<pkg>.__file__` under `.../tmp/pyenv/lib/python3.11/site-packages/`.

## Diagnostics

- `cat /proc/$$/environ | tr '\0' '\n' | grep PYTHON` — confirm the leak source (Hermes parent process env).
- `pyvenv.cfg` → `include-system-site-packages` — tells whether a venv is *meant* to be isolated (all throwaway venvs = false, yet still see runtime pkgs because of the leak).
- `pip show <pkg> | grep -E "Location|Version"` — reveals which interpreter "owns" the package.
- `python3 -c "import sys; print(sys.path)"` — PYTHONPATH entries appear before site-packages.

## Pitfalls

- Don't uninstall runtime packages you didn't install: crawl4ai, playwright, bs4, httpx, requests are Hermes-runtime deps used by `~/.hermes/scripts/*.py` (see local-web-crawler skill). Restoring *your own* stray installs (e.g. pypdf) is safe.
- After using a throwaway /tmp venv, delete it when done (`rm -rf /tmp/pyenv`) — user prefers zero residue.
- pdftotext (poppler-utils) is NOT installed on this WSL and apt install needs sudo that may fail silently — use pypdf from a throwaway /tmp venv instead (see paper-study-vault skill).
- The user cares specifically about not polluting global/system Python and the Hermes runtime — always route installs through the agent venv.
