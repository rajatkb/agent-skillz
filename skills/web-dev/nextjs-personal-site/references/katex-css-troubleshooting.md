# KaTeX CSS Troubleshooting

## Symptom

Math expressions render "double time" — once as rendered KaTeX (styling may be broken) and once as raw LaTeX source text next to it.

## Root Cause(s)

**Two distinct root causes produce the same symptom.**

### Cause 1: Missing KaTeX CSS (the common case)

`rehypeKatex` generates two HTML outputs for each math expression:

1. **Visual rendering** (`<span class="katex-html" aria-hidden="true">`) — the styled math
2. **MathML annotation** (`<span class="katex-mathml">`) — contains `<annotation encoding="application/x-tex">` with the raw LaTeX source, plus `<math>` markup for accessibility

The `.katex-mathml` element is normally hidden by KaTeX CSS:
```css
.katex .katex-mathml {
  position: absolute;
  clip-path: inset(50%);
  width: 1px;
  height: 1px;
  overflow: hidden;
}
```

If the KaTeX CSS isn't loaded on the page, `.katex-mathml` becomes visible, showing the raw LaTeX annotation alongside the visual HTML.

### Cause 2: rehype-preset-minify stripping aria-hidden

`rehype-preset-minify` minifies HTML output from all rehype plugins, including KaTeX. It strips `aria-hidden="true"` from `<span class="katex-html">` — the CSS is loaded correctly, but without `aria-hidden` the browser treats both the visual span and the MathML annotation as visible.

**Signs it's this cause:**
- `katex.css` IS present in the page (check via dev tools)
- The rendered math looks fully styled (not unstyled like Cause 1)
- Raw LaTeX source still visible next to styled math

**Fix:** Remove `rehype-preset-minify` from `contentlayer.config.ts` (both the import and the plugin entry in `rehypePlugins`). It breaks several plugins (KaTeX, Mermaid) and its byte savings on an SSG site are negligible.

## Investigation

### 1. Check if KaTeX CSS is in the page

```bash
# In the built output:
grep -c 'katex' out/_next/static/css/*.css
```

If only 1-2 matches (not hundreds/thousands), the CSS isn't loaded.

### 2. Check which CSS files the page loads

```bash
grep -oP 'href="/[^"]*\.css"' out/notes/path/to/page/index.html
```

If none of the linked CSS files contain the full KaTeX stylesheet (check for `katex-mathml` rule), that's the bug.

### 3. Check if the CSS exists but isn't linked

```bash
# Search ALL generated CSS files for the katex-mathml rule
grep -l 'katex-mathml' out/_next/static/css/*.css
```

If the CSS file exists but isn't in the page's `<link>` tags, the import is in a different page's component — Next.js code-splits CSS per-page chunk.

## Fixes

### Option A: Import in each page that needs math

```tsx
// app/notes/[[...slug]]/page.tsx
import 'katex/dist/katex.css'
```

This is the blog page's approach. Downside: needs a full rebuild (slow).

### Option B: Static asset in public/

Copy KaTeX CSS and fonts to `public/`, then add a `<link>` in the root layout:

```bash
cp node_modules/katex/dist/katex.css public/css/katex.css
cp node_modules/katex/dist/fonts/* public/css/fonts/
```

```tsx
// app/layout.tsx in the <head>
<link rel="stylesheet" href={`${basePath}/css/katex.css`} />
```

No rebuild needed — `public/` files are served directly. The CSS references fonts via relative paths (`fonts/KaTeX_*.woff2`), so both directories must exist.

### Option C: Import in root layout (if rebuild is acceptable)

```tsx
// app/layout.tsx imports
import 'katex/dist/katex.css'
```

This bundles KaTeX CSS into the global CSS chunk that all pages share.

## Related: Build Performance

When fixing this issue, the full build (`EXPORT=1 UNOPTIMIZED=1 npm run build`) may take 600+ seconds due to `rehypeKatex` processing on large math documents. Option B avoids the full rebuild.
