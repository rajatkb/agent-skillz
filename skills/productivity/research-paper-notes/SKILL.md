---
name: research-paper-notes
description: Study, summarize, and take notes on research papers (arXiv links or PDFs) and file them into the Obsidian vault at /mnt/c/Users/<user>/vault/. Use when the user shares a paper and wants it understood, summarized, or noted. Covers PDF text extraction that never touches the Hermes runtime Python.
---

# Research Paper Notes → Obsidian Vault

## When to use
User drops an arXiv link or PDF and says "study / summarize / understand / take notes". Deliverable: a real markdown note in the vault (top-level unless the user says otherwise) containing a genuine summary + study notes, not a stub.

## Vault facts
- Vault: `$VAULT_WIN_PATH` = `/mnt/c/Users/<user>/vault/` (NTFS mount, Windows side)
- Existing top-level structure: `conference/`, `jepa_notes/`, `model_tricks/`, `video_diffusion_alignment/` + loose top-level `.md` notes
- Vault sync is push-only (Repo → Windows), user runs `npm run watch`
- Ask about placement only when ambiguous. "Top-level" = vault root, no folder.

## Workflow
1. **Metadata** (no browser needed): `curl -sL -A "Mozilla/5.0" https://arxiv.org/abs/<ID>` and regex the citation meta tags (`citation_title`, `citation_author`, `citation_date`) + the abstract `<blockquote>`. Note the workshop/context (e.g. "IPAM RNLA workshop") — it frames the note.
2. **Download**: `curl -sL -A "Mozilla/5.0" -o /tmp/paper/paper.pdf https://arxiv.org/pdf/<ID>`
3. **Extract text** — ALWAYS via throwaway venv (see pitfall #1):
   ```bash
   python3 -m venv /tmp/pdfenv && /tmp/pdfenv/bin/pip install -q pypdf
   /tmp/pdfenv/bin/python - <<'EOF'
   import pypdf
   r = pypdf.PdfReader('/tmp/paper/paper.pdf')
   open('/tmp/paper/paper.txt','w',encoding='utf-8').write('\n'.join((p.extract_text() or '') for p in r.pages))
   print('pages:', len(r.pages), 'chars:', len(open('/tmp/paper/paper.txt').read()))
   EOF
   ```
4. **Read + understand**: read `paper.txt` in chunks (read_file, ~500 lines), pull out key equations, architecture in prose, and the *why* behind each technique. Track with todo.
5. **Write the note** (top-level `.md`): title + metadata (authors, arXiv ID + URL, date), then Summary, Key Concepts, Equations, section walkthrough, "Connections" to the user's other work (JEPA/VAE/diffusion — the vault topics), open questions. **Write in the USER's own voice, not formal prose** (punchy one-liners, bold lead-ins, `**Math (Name):**` + display equation + italic plain-language takeaway, ⚠ trap callouts, comparison tables, blockquote "never-forget" memory hooks, toy numeric examples for anything the user struggled with) — full style guide in the paper-study-notes skill; the user explicitly demanded "write into a stylistic method like I do". Author into the REPO copy `~/Work/<username>.github.io/data/vault/` (source of truth), not directly into the Windows vault.
6. **Sync**: `export VAULT_WIN_PATH=/mnt/c/Users/<user>/vault/ && bash ~/Work/<username>.github.io/scripts/sync-vault.sh` (no args = one-shot Repo → Windows push; `npm run watch` = watcher). Full flow in the paper-study-notes skill.
7. **Verify**: re-read the written file; confirm it sits at vault root and the sync reported "All detected files synced OK".

## Pitfalls
- **NEVER `pip install` into the asdf Python 3.11.0** (`~/.asdf/installs/python/3.11.0`) — that IS the Hermes runtime interpreter; polluting it risks breaking Hermes. The user explicitly rejects global/asdf pollution. Terminal sessions have no `VIRTUAL_ENV` by default — check before installing anything, and default to `python3 -m venv /tmp/<name>env`.
- **Verify the interpreter BEFORE installing** (this is what the user will ask about): `echo $VIRTUAL_ENV` (empty = no venv active), `which python3` (asdf path = the Hermes runtime), `pip show <pkg> | grep Location` to see where an install *would* land, and `hermes --version` — it prints `Project: <site-packages path>` which authoritatively shows which interpreter Hermes runs from. Note: `type -a hermes` may reveal multiple installs (e.g. a deprecated brew `hermes-agent` formula that resolves to the same asdf site-packages); the pip/asdf one is canonical — brew's formula was deprecated upstream and uninstalled Aug 2026.
- **Announce installs upfront**: say what you're installing and where it will land BEFORE running it. The user interrupted mid-task to check the pip install — surface the plan and any new package installs first, don't bury them.
- `pdftotext` / poppler-utils is NOT installed on this WSL box and `apt-get install` fails without sudo — go straight to pypdf-in-venv, don't burn a cycle on apt.
- `file` binary is missing — verify the downloaded PDF by byte size / python check, not `file`.
- arXiv abs/pdf are plain endpoints — curl beats the browser stack. (web_extract/DDGS is broken on this system — see memory.)
- **Sync direction trap**: vault sync is Repo → Windows with `rsync --delete`. If you author the note only in `/mnt/c/Users/<user>/vault/` and then sync, the note is deleted as "not in source". Repo copy (`data/vault/`) is canonical; write there first, then one-shot `bash scripts/sync-vault.sh`.
- NTFS BOM quirk applies to YAML/JSON only; plain `.md` notes are safe.
- User wants sources cited for technical claims — reference arXiv IDs and note page/section numbers in the study notes.
