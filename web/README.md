# ComplianceOS web

The planner's web app: mission wizard, roadmap timeline, licence details with quoted law, application
tracker, deadlines and brief. Next.js 14 (App Router), TypeScript strict, Tailwind, Radix primitives.

```bash
bun install
bun run dev            # http://localhost:3000, expects the API on http://127.0.0.1:8001
API_URL=http://host:port bun run dev   # point at another API
```

The browser only talks to this origin: `/api/*` is forwarded to the planner API by
`next.config.mjs`, so there is no CORS configuration. The API URL is read when the app is built
(and when the dev server starts).

| Script | Does |
|---|---|
| `bun run typecheck` | `tsc --noEmit` |
| `bun run lint` | ESLint (next/core-web-vitals) |
| `bun test` | Unit tests for the pure helpers in `src/lib` |
| `bun run build` | Production build (`output: standalone`, used by the Docker image) |
| `bun run gen:api` | Regenerate `src/lib/api-types.ts` from the FastAPI OpenAPI schema |

Design rules live in [`../DESIGN.md`](../DESIGN.md). Fonts are self-hosted (Fontsource), so the app
makes no requests to third-party font services.
