FROM node:24-alpine AS base

# Enable corepack for pnpm support
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app

# ---- Install dependencies (cached unless package.json/pnpm-lock.yaml change) ----
FROM base AS deps

COPY app/package.json app/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ---- Build the Nuxt app ----
FROM deps AS build

COPY app/ .

# ui/app/app/api/generated is gitignored, so it must be generated from the
# checked-in OpenAPI schema before `nuxt build`.
RUN pnpm run generate:api
RUN pnpm run build

# ---- Production runtime ----
FROM base AS production

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=8077

COPY --from=build /app/.output ./.output

EXPOSE 8077

CMD ["node", ".output/server/index.mjs"]
