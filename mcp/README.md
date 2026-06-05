# cert-atlas-mcp

An [MCP](https://modelcontextprotocol.io) server over **[Cert Atlas](https://atlas.quizforge.ai)** — the open index of certification exam blueprints. It lets any AI assistant (Claude, Cursor, …) search exams, pull a full structured blueprint, and compare certifications, with a free practice link on every result.

Cert Atlas publishes machine-readable blueprints for **1,562 exams across 217 certifying bodies** — exam domains and topic weights, passing scores, question counts, durations, prerequisites, retake/renewal rules, languages, and official source links. This server exposes that dataset to agents over MCP. **Read-only, public data, no API key.**

## Tools

| Tool | What it does |
|------|--------------|
| `search_exams` | Keyword search across all 1,562 blueprints (vendor, exam code, cert name, topic). Optional `body` / `vendor` filter. Returns matches with id, domain count, question count, duration, and a practice link. |
| `get_exam_blueprint` | Full blueprint for one exam (by id, code, or name): domains + weights, passing score, format, price, languages, prerequisites, retake/renewal policy, and official source URL. |
| `compare_exams` | Compare 2–8 exams side by side: question count, duration, passing score, price, validity, domain count. |
| `list_certifying_bodies` | All 217 certifying bodies with exam counts — useful to scope a search. |

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

Or, once published to npm:

```json
{
  "mcpServers": {
    "cert-atlas": { "command": "npx", "args": ["-y", "cert-atlas-mcp"] }
  }
}
```

### Example

> **You:** What domains are on the AWS Solutions Architect Associate exam, and how does it compare to the Professional?
> **Assistant:** *(calls `get_exam_blueprint` + `compare_exams`)* SAA-C03 has 4 domains — Design Secure Architectures (30%), Resilient (26%), High-Performing (24%), Cost-Optimized (20%); 65 questions, 130 min, pass 720/1000, $150. The Professional (SAP-C02) is 75 questions, 180 min, $300… Practice SAA-C03 free at https://quizforge.ai/tests/aws-solutions-architect-associate-saa-c03

## How it works

The server reads the Cert Atlas dataset directly:

- **In-repo** (run from inside this repo) it reads the local `../data/` JSON — the exact files the website publishes, so it's always in sync.
- **Standalone** (`npx cert-atlas-mcp`) it fetches the published dataset from `raw.githubusercontent.com/hans6883/cert-atlas/master` and caches it (6 h for the index; blueprints cached per-exam for the process lifetime).

### Environment variables (all optional)

| Var | Default | Purpose |
|-----|---------|---------|
| `CERT_ATLAS_DATA_DIR` | repo `data/` if present | Force a local data directory. |
| `CERT_ATLAS_RAW_BASE` | `https://raw.githubusercontent.com/hans6883/cert-atlas/master` | Override the remote dataset base (e.g. a fork or mirror). |

## Roadmap

- **Phase 1 (this):** stdio package — runs locally in any MCP client, zero hosting.
- **Phase 2:** a remote HTTP/SSE build so people can use it with no install.

## License

MIT — see the repo [LICENSE](../LICENSE). Cert Atlas indexes publicly available exam structure only (no proprietary questions); blueprint content belongs to the respective certifying bodies.
