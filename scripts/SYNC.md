# Syncing blueprints → cert-atlas → live (the one process)

The `web-scraper-mcp` pipeline scrapes/updates official exam blueprints into a SQLite DB
(`web-scraper-mcp/data/blueprint_registry.db`). This is the documented process to publish
those into the cert-atlas dataset and every live surface.

## 1. Regenerate the dataset from the blueprint DB
```bash
cd cert-atlas
python scripts/export.py     # reads ~/source/repos/web-scraper-mcp/data/blueprint_registry.db
                             # -> data/<vendor>/<exam>.json + data/index.json + data/vendors.json
```
- Override the DB with `BLUEPRINT_DB=/path/to.db`; pin a stamp with `GENERATED_DATE=YYYY-MM-DD`
  (defaults to today).
- `export.py` **wipes + rebuilds** `data/` from the DB (new exams added, changed blueprints
  updated, nothing deleted unless removed from the DB). Sample questions are stripped on purpose.
- `practice_url` comes from `slug_map.json` (verified `exam_id` → QuizForge `/tests/<slug>`).
  Unmapped exams fall back to `quizforge.ai/?q=<name>`. Maintain mappings with
  `scripts/match_slugs.py` and keep **only verified** slugs — a wrong slug sends users to the
  wrong practice exam. New exams start unmapped (search fallback) until verified.

## 2. Commit + push
```bash
git add data slug_map.json
git commit -m "data: resync blueprints from web-scraper"
git push origin master
```
Instantly refreshes: GitHub **raw** (what the MCP lazy-fetches per blueprint),
**atlas.quizforge.ai** (GitHub Pages), and the **Kaggle/Hugging Face** dataset mirrors.

## 3. Refresh the live remote MCP (mcp.quizforge.ai)
The hosted server caches the index in memory, so a data change needs a pull **and** restart:
```bash
ssh blazor@199.250.208.34 \
  "cd /opt/cert-atlas && git pull --ff-only && sudo systemctl restart cert-atlas-mcp"
```
- `blazor` owns `/opt/cert-atlas` (so `git pull` needs no sudo) and has a sudoers exception
  for restarting just this one service.
- Verify: `curl -s https://mcp.quizforge.ai/health` then a `search_exams` call for a new exam.

## 4. (Optional) Refresh the npm package's bundled snapshot
`npx cert-atlas-mcp` ships a bundled `data/index.json` for instant **offline** search; full
blueprints always lazy-fetch fresh from raw GitHub. To refresh the offline snapshot: bump
`mcp/package.json` version, `npm publish`, then publish the new `mcp/server.json` to the
official MCP registry. Not required for the remote/raw paths (those are always current).
