# Vault Note Folder Hierarchy

Implementation for `app/notes/[[...slug]]/page.tsx` — an optional catch-all route that renders directory listings for Obsidian vault subfolders and note pages for leaf files.

## Architecture

The route is a single file replacing what was previously `app/notes/page.tsx` (flat listing) + `app/notes/[...slug]/page.tsx` (note renderer).

### Route Logic

```
/notes                          → FolderListing(folderPath='')
/notes/jepa_notes               → FolderListing(folderPath='jepa_notes')
/notes/jepa_notes/01-ssl-history → render MDX note (leaf)
```

### Key Functions

**`isDirectory(path: string): boolean`**
Returns `true` if any vault note's slug starts with `path + '/'`. This is how folder-vs-file is auto-detected — no manual folder registration.

**`getChildren(folderPath: string): { dirs: {name: string, date: string, count: number}[], files: VaultNote[] }`**
Scans `allVaultNotes` for items under the given prefix. Splits by the next `/` in the remainder to separate subdirectories from direct children. For each directory, tracks the latest `date` (from the newest child note) and `count` (total non-draft notes inside). Dirs are sorted alphabetically, files by date descending.

### Folder Card Presentation

On the `/notes` listing page, subdirectories render using the same card style as file entries:
- **Date:** Shows the date of the newest note inside the folder (from `dir.date`)
- **Title:** `Folder Name /` — the `/` indicator distinguishes folders from files
- **Summary:** Shows `N note(s)` count (e.g. `2 notes`, `1 note`)

This provides visual parity with file cards while clearly differentiating folders.

**`allFolderPaths(): string[]`**
Derives intermediate folder paths from all note slugs. E.g., a note with slug `jepa_notes/deep/01-foo` produces folders `['jepa_notes', 'jepa_notes/deep']`. Used in `generateStaticParams` to pre-render folder listing pages.

**`displayName(segment: string): string`**
Converts a slug segment like `01-ssl-history` to a human-readable `01 Ssl History` (removes leading `N-` prefix, replaces hyphens with spaces, title-cases).

### generateStaticParams

```ts
export const generateStaticParams = async () => {
  // Root /notes/ path — use { slug: undefined }, not {}
  // Next.js 16 static export rejects {} for [[...slug]] root params
  const rootParam = { slug: undefined }
  const noteParams = allVaultNotes.map((p) => ({
    slug: p.slug.split('/').map((name) => decodeURI(name)),
  }))
  const folderParams = allFolderPaths().map((f) => ({
    slug: f.split('/').map((name) => decodeURI(name)),
  }))
  return [rootParam, ...noteParams, ...folderParams]
}
```

Both note pages AND folder listing pages are statically generated at build time. The root `/notes` path requires `{ slug: undefined }` in `generateStaticParams` — without it, static export won't generate `/notes/index.html`, and `/notes/` returns 404 on GH Pages.

### Verifying Build

After a successful build, confirm the generated routes:

```bash
ls out/notes/index.html              # root /notes/ exists
ls out/notes/jepa_notes/             # note dirs + listing exist
```

To verify Contentlayer picked up all documents:

```bash
npx contentlayer2 build
node -e "
const { allVaultNotes } = require('./.contentlayer/generated/index.mjs');
allVaultNotes.forEach(n => console.log(n.slug, '| draft:', n.draft));
"
```

Missing documents mean a required frontmatter field (usually `date`) is absent — Contentlayer skips those silently.

### Critical: Draft Notes Can Make Folders Invisible

**Bug:** If all files inside a folder are `draft: true`, the folder itself disappears from its parent's listing.

**Root cause:** `getChildren()` was filtering out draft notes with `if (note.draft === true) continue` at the top of the loop, before checking for directory structure. Since the only file in `jepa_notes/` was a draft, the `jepa_notes` directory was never added to the `dirs` set.

**Fix:** Always process ALL notes for directory detection. Only skip drafts when adding to the `files` list:

```ts
for (const note of allVaultNotes) {
  if (!note.slug.startsWith(prefix)) continue

  const remainder = note.slug.slice(prefix.length)
  const nextSlash = remainder.indexOf('/')

  if (nextSlash === -1) {
    if (note.draft !== true) {  // <-- draft filter here, NOT at top of loop
      files.push(note)
    }
  } else {
    dirs.add(remainder.slice(0, nextSlash))  // <-- no draft check, always detect dirs
  }
}
```

This also affects `isDirectory()` — it must check ALL notes, not just non-draft ones. The current implementation does this correctly since it has no draft filter.

### Frontmatter Requirements for Notes

See `contentlayer.config.ts` VaultNote definition. Critical fields:
- `title` (required) — displayed on note page and listing
- `date` (required, YYYY-MM-DD) — used for date sorting in listing. Obsidian creates `created` — must rename.
- `draft` (boolean, not string) — `note.draft !== true` filters these out. Obsidian uses `status: draft` — wrong.
- `tags`, `summary`, `lastmod` (optional)

### Generated Routes (Build Output)

```
├ ● /notes/[[...slug]]
│ ├ /notes/hello-vault
│ ├ /notes/jepa_notes
│ └ /notes/jepa_notes/01-ssl-history
```
