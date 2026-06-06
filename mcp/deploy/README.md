# Deploying the remote (Streamable HTTP) build

Host the `cert-atlas-mcp` HTTP transport so clients can add it by URL — no install.
The endpoint is stateless and reads its data from a repo checkout (or bundled/remote).

## Option A — systemd + Caddy (recommended)

```bash
# On the VPS (e.g. mcp.quizforge.ai):
sudo git clone https://github.com/hans6883/cert-atlas /opt/cert-atlas
cd /opt/cert-atlas/mcp
npm ci && npm run build            # builds dist/ and bundles the data snapshot

sudo cp deploy/cert-atlas-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cert-atlas-mcp
curl -s localhost:3000/health      # -> {"ok":true,...}

# TLS + public hostname:
sudo tee -a /etc/caddy/Caddyfile < deploy/Caddyfile   # or paste the block
sudo systemctl reload caddy
```

Keep data fresh: `cd /opt/cert-atlas && git pull && sudo systemctl restart cert-atlas-mcp`
(the service reads `CERT_ATLAS_LOCAL=/opt/cert-atlas`).

## Option B — Docker

```bash
docker build -t cert-atlas-mcp ./mcp
docker run -d --restart unless-stopped -p 127.0.0.1:3000:3000 --name cert-atlas-mcp cert-atlas-mcp
# then reverse-proxy mcp.quizforge.ai -> 127.0.0.1:3000 (see Caddyfile)
```

## Use it from a client

HTTP-capable MCP clients (Claude.ai/Desktop "Add custom connector", etc.) point at:

```
https://mcp.quizforge.ai/mcp
```

## After it's live

Add a remote entry to [`../server.json`](../server.json) so the official registry lists
the no-install endpoint alongside the npm package:

```json
"remotes": [
  { "type": "streamable-http", "url": "https://mcp.quizforge.ai/mcp" }
]
```

then re-run `mcp-publisher publish` (bump the version first).
