# ComplianceOS web (Next.js 14, standalone output).
FROM oven/bun:1.3 AS build
WORKDIR /web
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
# Where the Next server forwards /api/* (baked in at build time by next.config.mjs).
ARG API_URL=http://api:8000
# Public repository URL for "suggest a correction" links (inlined into the client bundle).
ARG NEXT_PUBLIC_REPO_URL=""
ENV API_URL=$API_URL NEXT_PUBLIC_REPO_URL=$NEXT_PUBLIC_REPO_URL NEXT_TELEMETRY_DISABLED=1
RUN bun run build

FROM node:20-alpine AS run
WORKDIR /web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S web && adduser -S web -G web
COPY --from=build --chown=web:web /web/.next/standalone ./
COPY --from=build --chown=web:web /web/.next/static ./.next/static
USER web
EXPOSE 3000
CMD ["node", "server.js"]
