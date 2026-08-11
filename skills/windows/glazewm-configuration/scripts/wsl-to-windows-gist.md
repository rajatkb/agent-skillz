# WSL → Windows: Editing GlazeWM Config

GlazeWM's config lives at `C:\Users\<USER>\.glzr\glazewm\config.yaml` — on the Windows filesystem.

## From WSL

Path becomes: `/mnt/c/Users/<USER>/.glzr/glazewm/config.yaml`

## BOM Pitfall

WSL writing to NTFS can inject a UTF-8 BOM at the start of the file. GlazeWM's YAML parser may reject this with a cryptic error. Fix:

```bash
sed -i '1s/^\xEF\xBB\xBF//' /mnt/c/Users/RAJAT/.glzr/glazewm/config.yaml
```

## Reload

After editing from WSL, reload config in GlazeWM: `alt+shift+r` (or whichever binding does `wm-reload-config`).

## WinAppCLI alternative

From Hermes/WSL, edit the file directly with `write_file` or `patch` using the `/mnt/c/...` path, then trigger the reload via `terminal` calling a `winappcli` keystroke or the user pressing the binding manually.
