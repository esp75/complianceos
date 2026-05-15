# Local dev Dockerfile for the Next.js web app.

FROM oven/bun:1-slim

WORKDIR /app
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile || bun install

COPY . .

EXPOSE 3000
CMD ["bun", "run", "dev"]
