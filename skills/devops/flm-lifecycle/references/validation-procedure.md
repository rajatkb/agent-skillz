# FLM + Gemma-Vision Pipeline Validation

A 6-step end-to-end validation of the on-demand NPU server lifecycle and vision inference.

## Prerequisites

- `bash ~/.hermes/scripts/flm-up.sh` and `flm-down.sh` exist (symlinked from amd-npu skill)
- PIL/Pillow installed (`pip install Pillow`)
- Gemma-vision plugin enabled in `config.yaml`

## Procedure

### Step 1 — Script existence
```bash
ls -la ~/.hermes/scripts/flm-up.sh ~/.hermes/scripts/flm-down.sh
```
**Pass:** Both exist (symlinks to amd-npu skill).

### Step 2 — Generate test image
```bash
python3 ~/.hermes/skills/devops/flm-lifecycle/scripts/generate_test_image.py
```
Generates `/tmp/flm_test_image.png` (400x200) with:
- Left: red rectangle containing centered white "Hello"
- Right: green "TEST IMAGE" text at top, blue circle below

Alternative (manual): use PIL from execute_code.

### Step 3 — Start FLM
```bash
bash ~/.hermes/scripts/flm-up.sh
```
**Pass:** Returns within 30s with "... READY". Idempotent (fast-exits if already running).

### Step 4 — Analyze image
Call `analyze_image` tool with:
- `image_path`: `/tmp/flm_test_image.png`
- `question`: "Describe this image in detail: what text do you see, what shapes and colors are present, and where are they located?"
- `detail`: 280

**Pass:** Response correctly reads white "Hello", identifies red rect on left, blue circle on right, green "TEST IMAGE" text.

### Step 5 — Verify response metadata
Check the response object for:
- `elapsed_seconds` (typically 3-6s on NPU)
- `model: gemma4-it:e4b`

**Pass:** Both fields present. Proves context isolation (only image+question sent, no conversation leak).

### Step 6 — Stop FLM (optional — only when verifying shutdown)

FLM stays running after use by default. Only stop if testing shutdown or freeing NPU RAM:

```bash
bash ~/.hermes/scripts/flm-down.sh
```

Then verify:
```bash
powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Format-Table Id, StartTime"
powershell.exe -NoProfile -Command "netstat -ano | findstr ':50001' | findstr LISTENING"
```

**Pass:** No flm.exe processes, no active listener on port 50001 (TIME_WAIT OK).

## Known Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| FLM already on different port | flm-up.sh shows "FLM process exists but not on port 50001" | Stop FLM, check config.yaml port |
| Analyze image hangs/times out | analyze_image takes >30s | FLM may have crashed — restart, check taskmgr for flm.exe |
| Image too large/detail too high | analyze_image slow or OOM | Use detail=280 default, keep images <= 400x200 for quick tests |

## Expected Output

```
$ bash flm-up.sh
Starting FLM server with model gemma4-it:e4b on port 50001...
Waiting for server.... READY

$ analyze_image -> elapsed_seconds: 4.2, model: gemma4-it:e4b

# FLM stays running for future analysis. Stop only when freeing NPU RAM:
$ bash flm-down.sh
Found 1 FLM process(es). Stopping...
FLM stopped. NPU model unloaded.
```
