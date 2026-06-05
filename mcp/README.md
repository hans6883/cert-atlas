# cert-atlas-mcp

An [MCP](https://modelcontextprotocol.io) server over **[Cert Atlas](https://atlas.quizforge.ai)** — the open index of certification exam blueprints. It lets any AI assistant (Claude, Cursor, …) search exams, pull a full structured blueprint, and compare certifications, with a free practice link on every result.

Cert Atlas publishes machine-readable blueprints for **1,562 exams across 217 certifying bodies** — exam domains and topic weights, passing scores, question counts, durations, prerequisites, retake/renewal rules, languages, and official source links. This server exposes that dataset to agents over MCP. **Read-only, public data, no API key.**

## Tools

| Tool | What it does |
|------|--------------|
| `search_exams` | Keyword search across all 1,562 blueprints (vendor, exam code, cert name, topic). Optional `certifying_body` / `vendor_slug` filter. Returns matches with id, domain count, question count, duration, and a practice link. |
| `get_exam_blueprint` | Full blueprint for one exam (by id, code, or name): domains + weights, passing score, format, price, languages, prerequisites, retake/renewal policy, and official source URL. |
| `compare_exams` | Compare 2–8 exams side by side: question count, duration, passing score, price, validity, domain count. |
| `list_certifying_bodies` | All 217 certifying bodies with exam counts (optional `contains` filter) — useful to scope a search. |

### Resources & prompts

- **Resources:** `cert-atlas://index` (the master index) and `cert-atlas://exam/{exam_id}` (a single blueprint) — agents can browse or attach the data directly.
- **Prompts:** `study-plan` (arg: `cert`) builds a topic-weighted plan grounded in the real blueprint; `compare-certs` (arg: `certs`) drives a structured comparison.

### Practice-link funnel

Every exam returned by any tool carries its free QuizForge practice link with UTM attribution — `?utm_source=mcp&utm_medium=cert_atlas&utm_campaign=<tool>` (existing query preserved) — so the server doubles as a measurable referral funnel. Links are factual and singular (one per exam); the value to the user is a real free practice exam.

## Install

```bash
npm install
npm run build
```

### Use with Claude Desktop / Claude Code

Add to your MCP config (`claude_desktop_config.json`, or via `claude mcp add`):

```json
{
  "mcpServers": {
    "cert-atlas": {
      "command": "node",
      "args": ["/absolute/path/to/cert-atlas/mcp/dist/index.js"]
    }
  }
}
```

Or, once published to npm (works in Claude Desktop/Code and **Cursor** — `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "cert-atlas": { "command": "npx", "args": ["-y", "cert-atlas-mcp"] }
  }
}
```

### Example prompts

- "What domains are on the AWS Solutions Architect Associate exam, and how is it weighted?"
- "Compare CompTIA Security+ and CySA+ — which is harder and which is cheaper?"
- "What are the prerequisites and passing score for CISSP?"
- "What nursing certifications does Cert Atlas cover?"

## How it works

The server reads the Cert Atlas dataset, preferring local files over the network:

1. A bundled snapshot of `index.json` (+ `vendors.json`) ships in the package → **instant, offline search** with a tiny install.
2. Individual blueprints are **lazy-fetched** from `raw.githubusercontent.com/hans6883/cert-atlas/master` on demand and cached, so the install stays small and data stays fresh.
3. When run inside the cert-atlas repo, it reads the canonical `../data/` directly (always in sync).

The bundled snapshot is regenerated from `../data` on every `npm run build` (see `scripts/copy-data.mjs`).

### Environment variables (all optional)

| Var | Default | Purpose |
|-----|---------|---------|
| `CERT_ATLAS_LOCAL` | — | Path to a cert-atlas **repo checkout**; reads its `data/` dir (used by the VPS/remote deployment). |
| `CERT_ATLAS_DATA_DIR` | repo/bundled `data/` | Force a specific data directory. |
| `CERT_ATLAS_RAW_BASE` | `https://raw.githubusercontent.com/hans6883/cert-atlas/master` | Override the remote dataset base (e.g. a fork or mirror). |

## Remote HTTP build

The same four tools are also served over the MCP **Streamable HTTP** transport, for hosting with no client install:

```bash
npm run build
npm run start:http        # PORT (default 3000), HOST (default 0.0.0.0)
# POST /mcp   — MCP endpoint
# GET  /health — liveness probe -> {"ok":true}
```

It's stateless (a fresh server per request), so it scales horizontally with no session store. A [`Dockerfile`](./Dockerfile) is included:

```bash
docker build -t cert-atlas-mcp .
docker run -p 3000:3000 cert-atlas-mcp
```

Put it behind your reverse proxy (TLS) and point HTTP-capable MCP clients at `https://<host>/mcp`.

## Publishing

**npm** (stdio package):

```bash
npm login
npm publish --access public      # runs the build via prepublishOnly
```

**Official MCP registry** ([registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io)) — uses [`server.json`](./server.json); `package.json` carries the matching `mcpName` for ownership verification:

```bash
# one-time: install the publisher CLI, then authenticate via GitHub
mcp-publisher login github
mcp-publisher publish            # reads ./server.json
```

[`smithery.yaml`](./smithery.yaml) lets [Smithery](https://smithery.ai) list it. Other directories (Glama, PulseMCP, mcp.so) auto-index from npm + GitHub once published.

## License

MIT — see the repo [LICENSE](../LICENSE). Cert Atlas indexes publicly available exam structure only (no proprietary questions); blueprint content belongs to the respective certifying bodies.
