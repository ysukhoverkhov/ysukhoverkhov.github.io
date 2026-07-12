## Development

When starting the dev server, use background mode:

```
astro dev --background
```

Manage the background server with `astro dev stop`, `astro dev status`, and `astro dev logs`.

## Documentation

Full documentation: https://docs.astro.build

Consult these guides before working on related tasks:

- [Adding pages, dynamic routes, or middleware](https://docs.astro.build/en/guides/routing/)
- [Working with Astro components](https://docs.astro.build/en/basics/astro-components/)
- [Using React, Vue, Svelte, or other framework components](https://docs.astro.build/en/guides/framework-components/)
- [Adding or managing content](https://docs.astro.build/en/guides/content-collections/)
- [Adding styles or using Tailwind](https://docs.astro.build/en/guides/styling/)
- [Supporting multiple languages](https://docs.astro.build/en/guides/internationalization/)

## Requirements

Node **22+** (Astro's scaffolder requires it; the runtime works on 20.3+).

## Deployment

- **Auto-deploy:** pushing to `main` triggers `.github/workflows/deploy.yml`
  (official `withastro/action`), which builds and publishes to GitHub Pages.
  Live at https://ysukhoverkhov.github.io/ (user site, served at the domain root
  — so `astro.config.mjs` sets `site` with no `base`).
- **Pages must stay in `workflow` build mode.** If it ever flips back to the
  legacy "deploy from branch" (Jekyll) mode, GitHub renders `README.md` as the
  homepage instead of the Astro build. Fix with:
  `gh api -X PUT repos/ysukhoverkhov/ysukhoverkhov.github.io/pages -f build_type=workflow`
- Never commit the built `dist/` — the Action builds it fresh in CI.
