# Dockerfile for the Cert Atlas MCP server (./mcp), used by Glama's automated
# safety & quality checks (and reusable for remote/self-hosting).
#
#   Build context MUST be the repository root (so the canonical ./data tree is
#   available and gets bundled into the image — the server then runs fully
#   offline, with no network needed for search OR blueprints):
#
#       docker build -t cert-atlas-mcp .
#       docker run --rm -i cert-atlas-mcp     # speaks MCP over stdio
#
# Published to npm as `cert-atlas-mcp`; registry id io.github.hans6883/cert-atlas.

# ---------- build ----------
FROM node:22-bookworm-slim AS build
WORKDIR /app/mcp

# Install deps from the lockfile first (reproducible + better layer caching).
COPY mcp/package.json mcp/package-lock.json ./
RUN npm ci

# Source + the canonical dataset. copy-data.mjs reads <repo>/data, i.e.
# /app/mcp/scripts/../../data -> /app/data, and bundles index.json + vendors.json
# into /app/mcp/data. tsc then compiles src -> dist.
COPY mcp/ ./
COPY data/ /app/data/
RUN npm run build

# Strip dev dependencies (typescript, @types) for a lean runtime image.
RUN npm prune --omit=dev

# ---------- runtime ----------
FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app/mcp

# Runtime artifacts only.
COPY --from=build /app/mcp/package.json ./package.json
COPY --from=build /app/mcp/node_modules ./node_modules
COPY --from=build /app/mcp/dist ./dist
COPY --from=build /app/mcp/data ./data
# Full blueprint tree at the repo-style path the loader also checks
# (<dist>/../../data == /app/data) -> every exam resolves offline, no fetch.
COPY --from=build /app/data /app/data

# Cert Atlas is public, read-only data — run unprivileged.
USER node

# The MCP server communicates over stdio; Glama connects to this.
ENTRYPOINT ["node", "dist/index.js"]
