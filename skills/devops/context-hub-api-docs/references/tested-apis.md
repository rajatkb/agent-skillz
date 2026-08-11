# Tested API Queries (Jul 2026)

Results from testing the chub registry on this system.

## Working (docs found)

| Query | Best match | Type | Source | Notes |
|-------|-----------|------|--------|-------|
| `openai` | `openai/chat` | doc (go, js, py) | community | OpenAI Responses API, v2.38.0 SDK |
| `openai` | `openai/package` | doc (py) | maintainer | OpenAI Python SDK |
| `github api` | `pygithub/package` | doc (py) | maintainer | PyGithub 2.6.0 — correct Auth.Token pattern |
| `github api` | `github/octokit` | doc (js) | maintainer | Official GitHub JS SDK |
| `docker` | `docker/package` | doc (py) | maintainer | Docker SDK for Python |
| `stripe` | `stripe/api` | doc (js) | maintainer | Broad Stripe API surface |
| `aws s3` | Though `aws/s3` | doc (js) | maintainer | AWS SDK JS v3 |
| `discord` | Not tested directly but likely present | — | — | — |

## NOT Working (no results)

| Query | Result |
|-------|--------|
| `tokio-tungstenite` | No results |
| `tray-icon` | No results |
| `tray` (Rust crate) | No results |
| `win32` | No results |
| `windows api` | Only Airflow Windows providers (unrelated) |
| `powershell` | Only Airflow PSRP/WinRM providers (unrelated) |
| `rust` | Only `maturin` and `pyo3-pack` (Python→Rust bridge tools) |

## Key Takeaway

chub covers web APIs and SaaS thoroughly but has no Rust crate, Win32, or PowerShell content. For those, use web_search + docs.rs directly.
