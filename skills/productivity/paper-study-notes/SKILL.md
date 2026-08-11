---
name: paper-study-notes
description: Study an arXiv paper and write summary/study notes into the user's Obsidian vault — fetch PDF + metadata, extract text locally, produce a top-level vault entry. Use when the user drops an arxiv.org link and says "study / summarise / take notes on this paper".
---

# Paper Study Notes → Obsidian Vault

Workflow for turning an arXiv paper link into a top-level note in the user's vault at `$VAULT_WIN_PATH` (`/mnt/c/Users/<user>/vault/`). Existing vault entries: `conference/`, `jepa_notes/`, `model_tricks/`, `video_diffusion_alignment/` — the vault is for ML/research study notes.

## Steps

1. **Download the PDF** (work dir `/tmp/paper/`):
   ```bash
   mkdir -p /tmp/paper && curl -sL -A "Mozilla/5.0" -o /tmp/paper/paper.pdf "https://arxiv.org/pdf/<ID>"
   ```
   Sanity check size (an arXiv paper PDF is usually 300KB–2MB; an HTML error page will be tiny).

2. **Fetch metadata from the abs page** — web_extract is BROKEN on this system, use curl + python regex instead:
   ```bash
   curl -sL -A "Mozilla/5.0" "https://arxiv.org/abs/<ID>" -o /tmp/paper/abs.html
   python3 - <<'EOF'
   import re, html
   raw = open('/tmp/paper/abs.html', encoding='utf-8', errors='replace').read()
   def meta(name):
       m = re.search(rf'<meta name="{name}" content="(.*?)"', raw)
       return html.unescape(m.group(1)) if m else 'N/A'
   print('TITLE:', meta('citation_title'))
   print('AUTHORS:', re.findall(r'<meta name="citation_author" content="(.*?)"', raw))
   print('DATE:', meta('citation_date'))
   ab = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', raw, re.S)
   if ab:
       print('ABSTRACT:', html.unescape(re.sub(r'<[^>]+>', ' ', ab.group(1))).strip())
   EOF
   ```

3. **Extract text with pypdf** — pdftotext/poppler is NOT installed on this WSL; use a throwaway /tmp venv (no persistent venvs exist on this machine — the old `~/pyenv/agent` was deleted Aug 2026):
   ```bash
   python3 -m venv /tmp/pdfenv && env -u PYTHONPATH /tmp/pdfenv/bin/pip install -q pypdf
   env -u PYTHONPATH /tmp/pdfenv/bin/python -c "
   import pypdf
   r = pypdf.PdfReader('/tmp/paper/paper.pdf')
   text = '\n'.join((p.extract_text() or '') for p in r.pages)
   open('/tmp/paper/paper.txt','w',encoding='utf-8').write(text)
   print('pages:', len(r.pages), 'chars:', len(text))
   "
   rm -rf /tmp/pdfenv   # zero residue — user wants throwaway venvs deleted when done
   ```

4. **Read and understand** — read the extracted text in chunks (read_file with offset/limit). Genuinely work through the math/concepts before writing notes; the user wants real understanding, not a surface summary.

5. **Write the vault note** — top-level entry (no folder unless the user says otherwise). Note naming: `[Short Title] — paper study notes` style. Content: metadata block (title/authors/date/abstract), a real summary, key concepts/equations, and study notes connecting to the user's other work (JEPA, video diffusion, model tricks) where relevant. See "Note style" below for the user's format preferences.

6. **Sync to the Windows vault** — the REPO copy is the source of truth: `~/Work/<username>.github.io/data/vault/`. Write the note there (or `cp` it after authoring), then run the one-shot push:
   ```bash
   export VAULT_WIN_PATH=/mnt/c/Users/<user>/vault/
   bash ~/Work/<username>.github.io/scripts/sync-vault.sh   # no args = one-shot Repo → Windows push
   ```
   (`npm run watch` in the repo = the continuous watcher; the script has no pull mode exposed.) The repo vault also feeds the Next.js blog — after syncing, `npm run build` compiles the note into `/notes/<name>`. When the user says "compile and push": run the build, then `git add data/vault/<note> && git commit && git push origin main`. Note: the build regenerates `app/tag-data.json` (tracked, shows as modified) — commit it only if asked; the note itself is the deliverable.

7. **Verify** — re-read the note file after writing; the sync script self-verifies ("All detected files synced OK") but double-check the Windows copy exists. BOM check on NTFS: `head -c 3 <file> | od -An -tx1` — `ef bb bf` means BOM; strip with `sed -i '1s/^\xEF\xBB\xBF//'` (harmless for Obsidian markdown but can trip other tooling).

## Note style (user preferences — from the "Understanding Transformers" session)

**Voice — write in the USER's own style, not formal prose** (explicit demand: "Write into a stylistic method like I do. You know already how I talk and write."). Study notes must read like the user's own `jepa_notes/01-ssl-history.md`, not like an abstract or a paper summary:
- **Punchy and terse** — one idea per line, fragments and arrows (→) over full sentences, bold lead-ins (`**Why it matters:**`, `**Key insight:**`, `**Math (Name):**`).
- **Signature equation pattern** — `**Math (Name):**` on its own line → display equation (LaTeX, Obsidian MathJax) → an italic plain-language takeaway line (`*Takeaway:*`, `*Why √d_QK:*`, `*Latent learning:*`).
- **⚠ callouts** for traps/misconceptions the user hit — e.g. "heads do NOT split the input", "GQA shares K/V, never Q", "Not Gemini, not Kimi".
- **Comparison tables** with bold header rows (cache math, model specs, variant comparisons).
- **Blockquote memory hooks** the user can re-read and instantly re-understand ("Never-forget version: all heads see the SAME input vector …").
- **Numeric toy examples** for anything the user struggled with — a hand-computed tiny example beats three prose explanations (this is what finally resolved the GQA confusion).
- Before writing, skim `jepa_notes/01-ssl-history.md` and `model_tricks/sparsity_tricks.md` in the vault as style exemplars.

- **Lean, not bloated**: cover the full pipeline but keep every section tight; no filler, no re-stating the abstract.
- **Methodical + self-consistent**: follow the paper's own structure; define every symbol before use; a reader should need no external source to follow the note.
- **Equations are first-class**: include ALL core equations in LaTeX (Obsidian MathJax), box the key results ($\boxed{...}$ or **bold**), and explain the notation inline (e.g. why the $\sqrt{d}$ scaling exists).
- **Annotated reference table**: for survey/intro papers, deliver "understanding the reference papers" as a table (ref → why it matters here) rather than a bare bibliography. This is the deliverable the user asks for when they say references matter.
- **Verify facts attributed to the paper** before writing: check the abs page (curl + regex meta tags) and, for claims about *cited* papers, fetch the cited paper's own text. Citation keys that look like model names are a trap: "[Kim+25]" was misread as "Kimi" and "Gemma 3" as "Gemini" — grep the cited paper's arXiv HTML for the named models before enshrining an adoption claim in the note. Verified IDs + adoption facts for the attention literature (Vaswani §3.2.2, Peri-LN, GQA, MQA, Gemma 3, DeepSeek-V2, TransMLA): `references/attention-literature-verified.md`.
- **Follow-up expansion loop**: when the user asks to expand a concept from the note ("expand the math of GQA", "not comfortable with MLA", "how is RMSNorm handled?"), answer in chat with the equations AND expand the note's corresponding section in the same turn, then re-run the one-shot sync. Tiny worked examples land well ($d_{in}=4$, $N_{heads}=4$, $G=2$). The note is a living document — every explanation deepens it, and the user reads it as the self-consistent reference.

## Pitfalls

- **web_extract is broken** (DDGS backend) — never use it for the abs page; curl + regex meta tags is fast and reliable.
- **NEVER write the note only into the Windows vault** (`/mnt/c/Users/<user>/vault/`) and then run the sync — the script's `rsync --delete` pushes Repo → Windows, so a Windows-only file is treated as "not in source" and DELETED. Always author into the repo copy (`data/vault/`) first, then push.
- If the user interrupts mid-task with "wait, what are you doing?" — STOP and explain the plan/status before continuing. They want transparency on toolchain changes (installs, venvs) as well as task progress.
- Never pip-install extraction libs into the Hermes runtime (asdf py3.11) — use a throwaway /tmp venv with `env -u PYTHONPATH`.
- If the PDF's extract_text returns empty/garbled (scanned or image-based PDF), the paper needs OCR — tell the user rather than fabricating content.
