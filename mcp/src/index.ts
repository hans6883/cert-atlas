#!/usr/bin/env node
/**
 * cert-atlas-mcp — a Model Context Protocol server over Cert Atlas, the open
 * index of certification exam blueprints (atlas.quizforge.ai).
 *
 * Cert Atlas publishes structured, machine-readable blueprints for 1,562 exams
 * across 217 certifying bodies — exam domains and topic weights, passing scores,
 * question counts, durations, prerequisites, renewal rules, and official source
 * links. This server lets an AI agent search those exams, pull a full blueprint,
 * and compare certifications side by side, with a QuizForge practice link on
 * every result.
 *
 * Read-only, public data, no API key. Reads the local data/ directory when run
 * inside the repo, else fetches the published dataset from GitHub.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import {
  getIndex,
  getBlueprint,
  resolveExam,
  scoreMatch,
  toText,
  dataSource,
  type Blueprint,
  type IndexEntry,
} from "./catalog.js";

const ATLAS = "https://atlas.quizforge.ai";
const server = new McpServer({ name: "cert-atlas", version: "1.0.0" });

// --- formatting helpers ------------------------------------------------------
function indexLine(e: IndexEntry): string {
  const code = e.exam_code ? `[${e.exam_code}] ` : "";
  const parts = [`${e.domains} domains`];
  if (e.total_questions != null) parts.push(`${e.total_questions} Q`);
  if (e.duration_minutes != null) parts.push(`${e.duration_minutes} min`);
  const practice = e.practice_url ? `  ·  practice: ${e.practice_url}` : "";
  return `- ${code}${e.exam_name} — ${e.certifying_body}  (${e.exam_id})\n    ${parts.join(" · ")}${practice}`;
}

function dash(v: unknown, suffix = ""): string {
  return v == null || v === "" ? "—" : `${v}${suffix}`;
}

function blueprintText(e: IndexEntry, bp: Blueprint): string {
  const L: string[] = [];
  L.push(`# ${bp.exam_name}${bp.exam_code ? ` (${bp.exam_code})` : ""}`);
  L.push(`Certifying body: ${bp.certifying_body ?? e.certifying_body}`);
  if (bp.certification_name) L.push(`Certification: ${bp.certification_name}`);

  const mech: string[] = [];
  if (bp.total_questions != null) mech.push(`${bp.total_questions} questions`);
  if (bp.duration_minutes != null) mech.push(`${bp.duration_minutes} min`);
  if (bp.passing_score != null)
    mech.push(`pass ${bp.passing_score}${bp.passing_score_scale ? ` (${bp.passing_score_scale})` : ""}`);
  if (bp.exam_format) mech.push(String(bp.exam_format));
  if (mech.length) L.push(`Format: ${mech.join(" · ")}`);
  if (bp.question_types?.length) L.push(`Question types: ${bp.question_types.join(", ")}`);
  if (bp.exam_price_usd != null)
    L.push(`Price: $${bp.exam_price_usd}${bp.exam_price_notes ? ` (${bp.exam_price_notes})` : ""}`);
  if (bp.available_languages?.length) L.push(`Languages: ${bp.available_languages.join(", ")}`);

  const prereq = toText(bp.prerequisites);
  L.push(`Prerequisites: ${prereq ? prereq : "None stated"}`);
  const recExp = toText(bp.recommended_experience);
  if (recExp) L.push(`Recommended experience: ${recExp}`);

  const ren: string[] = [];
  if (bp.certification_validity_years != null) ren.push(`valid ${bp.certification_validity_years} yr`);
  if (bp.renewal_required != null) ren.push(bp.renewal_required ? "renewal required" : "no renewal");
  if (ren.length) L.push(`Validity: ${ren.join(" · ")}${bp.renewal_options ? ` — ${toText(bp.renewal_options)}` : ""}`);
  const retake = toText(bp.retake_policy);
  if (retake) L.push(`Retake policy: ${retake}`);

  if (bp.domains?.length) {
    L.push("");
    L.push(`## Domains (${bp.domains.length})`);
    for (const d of bp.domains) {
      const w = d.weight_percent != null ? ` — ${d.weight_percent}%` : "";
      L.push(`- ${d.name}${w}`);
      for (const o of d.objectives ?? []) {
        const text = typeof o === "string" ? o : o.description ?? o.name ?? "";
        if (text) L.push(`    · ${text}`);
      }
    }
  } else {
    L.push("");
    L.push("## Domains: not broken down in the published blueprint");
  }

  L.push("");
  if (bp.source_url) L.push(`Official source: ${bp.source_url}`);
  if (bp.official_objectives_url) L.push(`Objectives: ${bp.official_objectives_url}`);
  if (bp.exam_registration_url) L.push(`Register: ${bp.exam_registration_url}`);
  const practice = bp.practice_url ?? e.practice_url;
  if (practice) L.push(`Practice (QuizForge): ${practice}`);
  return L.join("\n");
}

const text = (t: string) => ({ content: [{ type: "text" as const, text: t }] });

// --- tools -------------------------------------------------------------------
server.tool(
  "search_exams",
  "Search Cert Atlas — the open index of 1,562 certification exam blueprints across " +
    "217 certifying bodies — by keyword (vendor, exam code, cert name, or topic; e.g. " +
    "'aws solutions architect', 'CISSP', 'nclex', 'pmp'). Optionally narrow by certifying " +
    "body or vendor slug. Returns matching exams with their id, domain count, question " +
    "count, duration, and a QuizForge practice link.",
  {
    query: z.string().describe("Keywords: certification name, exam code, vendor, or topic"),
    body: z
      .string()
      .optional()
      .describe("Optional certifying-body filter, e.g. 'AWS', 'CompTIA', 'ISC2', '(ISC)²'"),
    vendor: z
      .string()
      .optional()
      .describe("Optional vendor-slug filter, e.g. 'aws', 'microsoft', 'comptia'"),
    limit: z.number().int().min(1).max(50).optional().describe("Max results (default 12)"),
  },
  async ({ query, body, vendor, limit }) => {
    const { exams, meta } = await getIndex();
    const max = limit ?? 12;
    let pool = exams;
    if (body) {
      const b = body.toLowerCase();
      pool = pool.filter((e) => e.certifying_body.toLowerCase().includes(b));
    }
    if (vendor) {
      const v = vendor.toLowerCase();
      pool = pool.filter((e) => e.vendor_slug.toLowerCase() === v || e.vendor_slug.toLowerCase().includes(v));
    }

    const q = query.trim();
    let ranked: IndexEntry[];
    if (q) {
      ranked = pool
        .map((e) => ({ e, s: scoreMatch(e, q) }))
        .filter((x) => x.s > 0)
        .sort((a, b2) => b2.s - a.s)
        .slice(0, max)
        .map((x) => x.e);
    } else {
      // No keyword but filtered (e.g. "list everything from AWS").
      ranked = pool.slice(0, max);
    }

    if (ranked.length === 0) {
      const filterNote = [body && `body="${body}"`, vendor && `vendor="${vendor}"`]
        .filter(Boolean)
        .join(", ");
      return text(
        `No Cert Atlas exam matched "${query}"${filterNote ? ` (${filterNote})` : ""}. ` +
          `Try a broader keyword or an exam code. Browse the full index: ${ATLAS}`,
      );
    }
    const more = q && pool.filter((e) => scoreMatch(e, q) > 0).length > ranked.length;
    return text(
      `Found ${ranked.length} Cert Atlas exam(s) for "${query}"` +
        ` (of ${meta.total_exams} total):\n\n` +
        ranked.map(indexLine).join("\n") +
        (more ? `\n\n…more matches available — raise \`limit\` to see them.` : "") +
        `\n\nGet a full blueprint with get_exam_blueprint(<id or code>). Browse: ${ATLAS}`,
    );
  },
);

server.tool(
  "get_exam_blueprint",
  "Get the full Cert Atlas blueprint for one certification exam: domains with topic " +
    "weights, passing score, question count, duration, price, languages, prerequisites, " +
    "retake/renewal policy, and the official source URL — plus a QuizForge practice link. " +
    "Accepts an exam id (e.g. 'aws-cloud-practitioner-clf-c02'), an exam code ('CLF-C02'), " +
    "or a certification name.",
  {
    exam: z.string().describe("Exam id, exam code, or certification name"),
  },
  async ({ exam }) => {
    const entry = await resolveExam(exam);
    if (!entry) {
      return text(
        `"${exam}" didn't resolve to a Cert Atlas exam. Try search_exams("${exam}") to find ` +
          `the right id or code, or browse ${ATLAS}.`,
      );
    }
    try {
      const bp = await getBlueprint(entry);
      return text(blueprintText(entry, bp));
    } catch (err) {
      return text(
        `Resolved "${exam}" to ${entry.exam_name} (${entry.exam_id}) but couldn't load its ` +
          `blueprint file: ${(err as Error).message}`,
      );
    }
  },
);

server.tool(
  "compare_exams",
  "Compare 2–8 certification exams side by side: question count, duration, passing score, " +
    "price, validity period, and domain count. Accepts exam ids, codes, or names. Useful for " +
    "'is Security+ or CySA+ harder?', 'compare the AWS associate exams', etc.",
  {
    exams: z
      .array(z.string())
      .min(2)
      .max(8)
      .describe("2–8 exam ids, codes, or names to compare"),
  },
  async ({ exams }) => {
    const resolved = await Promise.all(
      exams.map(async (q) => ({ q, entry: await resolveExam(q) })),
    );
    const unresolved = resolved.filter((r) => !r.entry).map((r) => r.q);
    const found = resolved.filter((r) => r.entry) as { q: string; entry: IndexEntry }[];
    if (found.length < 2) {
      return text(
        `Need at least 2 resolvable exams to compare. Unresolved: ${unresolved.join(", ") || "(none)"}. ` +
          `Use search_exams to find ids.`,
      );
    }

    const rows = await Promise.all(
      found.map(async ({ entry }) => {
        let bp: Blueprint | null = null;
        try {
          bp = await getBlueprint(entry);
        } catch {
          /* fall back to index-only fields */
        }
        const label = entry.exam_code || entry.exam_id;
        return {
          label,
          body: entry.certifying_body,
          questions: bp?.total_questions ?? entry.total_questions,
          duration: bp?.duration_minutes ?? entry.duration_minutes,
          pass: bp?.passing_score ?? null,
          scale: bp?.passing_score_scale ?? null,
          price: bp?.exam_price_usd ?? null,
          valid: bp?.certification_validity_years ?? null,
          domains: bp?.domains?.length ?? entry.domains,
          practice: bp?.practice_url ?? entry.practice_url,
        };
      }),
    );

    const header = `| Exam | Body | Questions | Duration | Passing | Price | Valid | Domains |`;
    const sep = `|------|------|-----------|----------|---------|-------|-------|---------|`;
    const body = rows
      .map(
        (r) =>
          `| ${r.label} | ${r.body} | ${dash(r.questions)} | ${dash(r.duration, " min")} | ` +
          `${r.pass != null ? `${r.pass}${r.scale ? ` (${r.scale})` : ""}` : "—"} | ${dash(
            r.price != null ? `$${r.price}` : null,
          )} | ${dash(r.valid != null ? `${r.valid} yr` : null)} | ${dash(r.domains)} |`,
      )
      .join("\n");

    const links = rows
      .filter((r) => r.practice)
      .map((r) => `- ${r.label}: ${r.practice}`)
      .join("\n");

    return text(
      [
        `Comparing ${rows.length} exams:`,
        "",
        header,
        sep,
        body,
        unresolved.length ? `\nCouldn't resolve: ${unresolved.join(", ")}` : "",
        links ? `\nPractice (QuizForge):\n${links}` : "",
      ]
        .filter((s) => s !== "")
        .join("\n"),
    );
  },
);

server.tool(
  "list_certifying_bodies",
  "List the certifying bodies indexed by Cert Atlas (AWS, CompTIA, ISC2, PMI, AACN, …) " +
    "with how many exams each has. Useful to scope a search or see what's covered.",
  {
    limit: z.number().int().min(1).max(300).optional().describe("Max bodies to list (default: all)"),
  },
  async ({ limit }) => {
    const { byBody, meta } = await getIndex();
    const rows = [...byBody.entries()]
      .map(([b, list]) => ({ b, n: list.length }))
      .sort((a, b2) => b2.n - a.n || a.b.localeCompare(b2.b));
    const shown = limit ? rows.slice(0, limit) : rows;
    return text(
      `Cert Atlas covers ${meta.total_exams} exams across ${rows.length} certifying bodies` +
        ` (generated ${meta.generated}):\n\n` +
        shown.map((r) => `- ${r.b}: ${r.n} exam${r.n === 1 ? "" : "s"}`).join("\n") +
        (limit && rows.length > limit ? `\n\n…and ${rows.length - limit} more.` : "") +
        `\n\nSearch within one via search_exams(query, body="<name>"). Browse: ${ATLAS}`,
    );
  },
);

// --- bootstrap ---------------------------------------------------------------
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // stderr only — stdout is the MCP transport.
  console.error(`cert-atlas-mcp running (stdio). Data ${dataSource()}. Index: ${ATLAS}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
