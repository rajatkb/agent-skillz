# WSL Mirrored Networking — Localhost Reaches Windows

## Config File

`C:\Users\<user>\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
memory=4GB
processors=2
swap=0
guiApplications=false

[experimental]
autoMemoryReclaim=gradual
```

## Effect

With `networkingMode=mirrored`, WSL2 shares the Windows host's loopback interface. `localhost` and `127.0.0.1` from WSL reach Windows services directly. No netsh portproxy, no `--host 0.0.0.0`, no gateway IP discovery needed.

## Restart to Apply Changes

```powershell
# From Windows
wsl --shutdown
wsl
```

Or from WSL:
```bash
powershell.exe -Command "wsl --shutdown"
# Then open a new WSL terminal
```

## Verification

1. Start a service on Windows (e.g., FLM on port 50001)
2. From WSL:
```bash
curl -s --max-time 5 http://localhost:50001/v1/models
```

## FLM_HOST Configuration

With mirrored networking, the `gemma-npu` plugin's `FLM_HOST` should be `localhost` (set via `FLM_HOST` env var or default in `tools.py`). The `flm-up.sh` health-check curl should also use `localhost`.

## Diagnosis When It Breaks

If `localhost` stops reaching Windows from WSL:

```bash
# Check if mirrored mode is still configured
cat /mnt/c/Users/<user>/.wslconfig | grep networkingMode

# Check WSL version (must be WSL2 with mirrored support)
wsl.exe --version

# Test basic connectivity (ping Windows host IP)
ping -c 1 192.168.29.113

# Check if FLM is actually running on Windows
powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Format-Table Id, StartTime"

# Check if port is listening from Windows perspective
powershell.exe -NoProfile -Command "netstat -ano | findstr ':50001' | findstr LISTENING"
```

If mirrored mode is configured but not working, do a full `wsl --shutdown` + restart WSL.
