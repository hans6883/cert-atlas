#!/usr/bin/env node
/**
 * cert-atlas-mcp (stdio) — a Model Context Protocol server over Cert Atlas, the
 * open index of certification exam blueprints (atlas.quizforge.ai).
 *
 * Cert Atlas publishes structured, machine-readable blueprints for 1,580 exams
 * across 222 certifying bodies — exam domains and topic weights, passing scores,
 * question counts, durations, prerequisites, renewal rules, and official source
 * links. This server lets an AI agent search those exams, pull a full blueprint,
 * and compare certifications, with a QuizForge practice link on every result.
 *
 * Read-only, public data, no API key. Reads the local data/ directory when run
 * inside the repo, else fetches the published dataset from GitHub.
 *
 * This is the stdio entry point. For the remote HTTP build, see http.ts.
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer, ATLAS } from "./server.js";
import { dataSource } from "./catalog.js";

async function main() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // stderr only — stdout is the MCP transport.
  console.error(`cert-atlas-mcp running (stdio). Data ${dataSource()}. Index: ${ATLAS}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
