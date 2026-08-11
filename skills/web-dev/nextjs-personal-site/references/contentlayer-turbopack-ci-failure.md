# Contentlayer + Turbopack: CI Build Failure

## Error

After switching from webpack (`--webpack` flag) to Turbopack, the GitHub Actions build fails on a clean checkout:

```
Build error occurred
Error: Turbopack build failed with 9 errors:
./app/about/page.tsx:1:1
Module not found: Can't resolve 'contentlayer/generated'
```

The same build passes locally because `.contentlayer/generated/` exists from a previous run.

## Root Cause

`withContentlayer` in `next.config.js` injects a webpack plugin to auto-generate Contentlayer output during `next build`. Under Turbopack, webpack plugin hooks never fire — Contentlayer is never auto-generated, and `contentlayer/generated` module resolution fails.

## Fix

Add an explicit `contentlayer2 build` step before `next build` in `package.json`:

```json
"build": "contentlayer2 build && next build && node ./scripts/postbuild.mjs"
```

## Verification

```bash
# Simulate CI: clean everything, reinstall, build
rm -rf node_modules .contentlayer .next out
npm ci
EXPORT=1 UNOPTIMIZED=1 npm run build
```

## Timeline

- Last working CI build (Run #63): used `--webpack` flag — Contentlayer auto-generated via webpack hooks (2m 34s)
- First failing CI build (Run #64): removed `--webpack`, switched to Turbopack — Contentlayer didn't auto-generate (40s, exited 1)
- Fix (Run #67): added explicit `contentlayer2 build` step — build succeeded (2m 1s)
