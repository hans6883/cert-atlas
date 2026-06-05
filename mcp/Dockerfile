# cert-atlas-mcp — remote Streamable HTTP build (Phase 2).
# Builds the TypeScript server and runs the HTTP transport. The dataset is
# fetched from GitHub at runtime, so the image carries no data.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json tsconfig.json ./
RUN npm ci
COPY src ./src
RUN npm run build && npm prune --omit=dev

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOST=0.0.0.0
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
EXPOSE 3000
# Health: GET /health -> {"ok":true}.  MCP endpoint: POST /mcp
CMD ["node", "dist/http.js"]
