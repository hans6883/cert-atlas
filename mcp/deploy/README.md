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

## Hardening (recommended)

- **Run as an isolated user.** The unit uses systemd `DynamicUser=true` — a dedicated,
  no-shell, no-home, zero-capability user — so an app/dependency compromise can't reach
  the host. Put the checkout somewhere world-readable (`/opt/cert-atlas`), not a private home.
- **Rate limit at the edge.** [`nginx-mcp.conf`](./nginx-mcp.conf) adds a per-IP `limit_req`
  (20 r/s, burst 40 → 429). Add a Cloudflare rate-limiting rule too if proxied.
- **Lock the origin to Cloudflare** (no cert needed). If Cloudflare-proxied, stop attackers
  reaching the origin IP directly and bypassing CF's WAF/DDoS. Allow only Cloudflare's edge
  IPs, evaluated on the real TCP peer (`$realip_remote_addr`, works with `set_real_ip_from`):
  ```nginx
  # http scope — fill from https://www.cloudflare.com/ips-v4 + ips-v6
  geo $realip_remote_addr $cf_ok { default 0; 173.245.48.0/20 1; 2400:cb00::/32 1; ...; }
  # in each mcp server { } block, before location:
  if ($cf_ok = 0) { return 403; }
  ```
  Direct hits to the origin IP then return 403; Cloudflare-proxied requests pass. (Stronger
  alternative: Cloudflare **Authenticated Origin Pulls** + `ssl_verify_client on` — but enable
  the CF toggle first or you lock CF out.)

## After it's live

Add a remote entry to [`../server.json`](../server.json) so the official registry lists
the no-install endpoint alongside the npm package:

```json
"remotes": [
  { "type": "streamable-http", "url": "https://mcp.quizforge.ai/mcp" }
]
```

then re-run `mcp-publisher publish` (bump the version first).
