# Next.js notes for this app

- Pinned to **Next.js 14.2.x** with **React 18.3**. Do not bump majors without a
  scoped migration commit — the build plan and reg-graph integration assume the
  App Router conventions of Next 14.
- Tailwind v3 (CSS `@tailwind` directives), not v4. `tailwind.config.ts` is the
  source of truth.
- ESLint legacy config (`.eslintrc.json`), not the flat config.
- This app is the operator dashboard + authority view. It is **never** deployed
  to Vercel — production runs on Hetzner via Coolify per the sovereignty rules.
