#!/usr/bin/env node
/**
 * cert-atlas-mcp (Streamable HTTP) — the remote build. Same four tools as the
 * stdio server, served over the MCP Streamable HTTP transport so clients can use
 * Cert Atlas with no install (e.g. hosted on a VPS behind a reverse proxy).
 *
 * Stateless: every JSON-RPC request gets a fresh server + transport, so there's
 * no session state to manage — ideal for a read-only tool server and trivially
 * horizontally scalable. Exposes:
 *   POST /mcp        MCP endpoint (JSON-RPC over Streamable HTTP)
 *   GET  /health     liveness probe -> {"ok":true}
 *
 * Env:
 *   PORT   (default 3000)
 *   HOST   (default 0.0.0.0)
 */
import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from "node:http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { createServer, ATLAS } from "./server.js";
import { dataSource } from "./catalog.js";

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "0.0.0.0";
const MCP_PATH = "/mcp";

function cors(res: ServerResponse): void {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, mcp-session-id, mcp-protocol-version");
  res.setHeader("Access-Control-Expose-Headers", "mcp-session-id");
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  const body = JSON.stringify(payload);
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(body);
}

async function readBody(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  return raw ? JSON.parse(raw) : undefined;
}

const rpcError = (message: string) => ({
  jsonrpc: "2.0" as const,
  error: { code: -32000, message },
  id: null,
});

async function handleMcpPost(req: IncomingMessage, res: ServerResponse): Promise<void> {
  let body: unknown;
  try {
    body = await readBody(req);
  } catch {
    sendJson(res, 400, rpcError("Invalid JSON in request body."));
    return;
  }

  // Stateless: a fresh server + transport per request, torn down when it closes.
  const server = createServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on("close", () => {
    transport.close();
    server.close();
  });

  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, body);
  } catch (err) {
    console.error("MCP request error:", err);
    if (!res.headersSent) sendJson(res, 500, rpcError("Internal server error."));
  }
}

const httpServer = createHttpServer(async (req, res) => {
  cors(res);

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = (req.url ?? "").split("?")[0];

  if (req.method === "GET" && (url === "/health" || url === "/")) {
    sendJson(res, 200, { ok: true, server: "cert-atlas-mcp", endpoint: MCP_PATH, data: dataSource() });
    return;
  }

  if (url !== MCP_PATH) {
    sendJson(res, 404, rpcError(`Not found. MCP endpoint is ${MCP_PATH}.`));
    return;
  }

  if (req.method === "POST") {
    await handleMcpPost(req, res);
    return;
  }

  // Stateless mode has no standalone SSE stream for server->client notifications.
  sendJson(res, 405, rpcError("Method not allowed. Use POST for MCP requests."));
});

httpServer.listen(PORT, HOST, () => {
  console.error(
    `cert-atlas-mcp (HTTP) on http://${HOST}:${PORT}${MCP_PATH} · health: /health · ` +
      `Data ${dataSource()}. Index: ${ATLAS}`,
  );
});
