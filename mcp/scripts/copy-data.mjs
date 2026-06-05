// Bundle a snapshot of the canonical dataset into the package for instant,
// offline search. Copies cert-atlas/data/{index.json,vendors.json} -> mcp/data/.
// Runs on `npm run build`; skips gracefully when the repo data/ isn't present
// (e.g. building outside the monorepo), in which case the server falls back to
// the local/remote loaders at runtime.
import { mkdir, copyFile, access } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url)); // mcp/scripts
const repoData = resolve(here, "..", "..", "data"); // cert-atlas/data
const outDir = resolve(here, "..", "data"); // mcp/data
const files = ["index.json", "vendors.json"];

try {
  await access(repoData);
} catch {
  console.error(`[copy-data] source ${repoData} not found — skipping bundle (remote/local fallback will be used).`);
  process.exit(0);
}

await mkdir(outDir, { recursive: true });
for (const f of files) {
  try {
    await copyFile(join(repoData, f), join(outDir, f));
    console.error(`[copy-data] bundled ${f}`);
  } catch (e) {
    console.error(`[copy-data] could not copy ${f}: ${e.message}`);
  }
}
