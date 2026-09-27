# Pratyaksa Frontend — SvelteKit (adapter-node)
FROM node:22-alpine AS build

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

# API base is baked at build time; override with --build-arg for other hosts.
ARG PUBLIC_API_BASE=/api/v1
ENV PUBLIC_API_BASE=$PUBLIC_API_BASE
RUN pnpm build

FROM node:22-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json

EXPOSE 3000

CMD ["node", "build/index.js"]
